"""O03 offline hindsight reference generation and export.

This module is intentionally separate from the visible-state solver (O01/O02). It
operates on a complete ``PrivateEpisode`` — including future arrivals and realized
(private) carbon observations — and produces a ``SolverResult`` with
``kind="hindsight"`` and ``uses_future_arrivals=True``. Hindsight artifacts are
offline-only: they are never returned to a running policy and never enter a
``VisibleState`` or ``Context``.

The public entry point is ``generate_hindsight_reference``. It validates the
private episode, builds a hindsight-only view, runs the reference MILP, and
returns a ``HindsightReferenceArtifact`` envelope with provenance and a stable
fingerprint. ``export_hindsight_reference`` writes the artifact and a sidecar
manifest atomically to a directory outside the repository checkout.

Design choices (Q08 stand-in until the team records them):

* Backend: ``scipy.optimize.milp`` (same backend as O01, separate adapter).
* Objective: minimize total realized emissions (kg CO2) over the full episode.
* Decision variables: one binary per feasible ``(job_id, start_slot)`` candidate
  across the entire 30-slot horizon.
* Constraints:
  1. Each job starts exactly once.
  2. Each job starts within its feasible window.
  3. Capacity per slot: background + running/newly started jobs <= capacity limit.
  4. Non-flexible jobs must start exactly at their arrival slot.
* Tie-breaking: deterministic lexical ordering of candidates (job_id, start_slot).
* Tolerance: ``1e-6`` for integrality/objective reporting.
"""

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from dc_sustainability import schemas as s
from dc_sustainability.reference.solver import _BACKEND_VERSION, _BACKENDS, _TOLERANCE

_HINDSIGHT_VERSION = "o03-v1"
_TIME_LIMIT_S = 30.0


class HindsightError(ValueError):
    """Raised when a hindsight reference cannot be generated or exported."""


@dataclass(frozen=True)
class _HindsightVar:
    """One MILP binary variable: ``x[idx] == 1`` means ``job_id`` starts at ``start_slot``."""

    idx: int
    job_id: str
    start_slot: int
    job: s.Job
    energy_kwh: float
    carbon_g_per_kwh: float

    @property
    def emissions_kg(self) -> float:
        return self.energy_kwh * self.carbon_g_per_kwh / 1000.0


class _HindsightMILP:
    """Build and solve a deterministic full-episode MILP using realized carbon."""

    def __init__(
        self,
        episode: s.PrivateEpisode,
        *,
        time_limit_s: float = _TIME_LIMIT_S,
        tolerance: float = _TOLERANCE,
    ) -> None:
        self.episode = episode
        self.time_limit_s = time_limit_s
        self.tolerance = tolerance
        self.capacity = self._capacity_kw()
        self.horizon = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
        self.carbon: dict[int, float] = self._realized_carbon_map()
        self.vars: list[_HindsightVar] = []
        self._build_vars()

    def _capacity_kw(self) -> Optional[float]:
        caps = [
            c.limit_value
            for c in self.episode.snapshot.constraints
            if c.constraint_type == "capacity"
        ]
        if len(caps) != 1:
            return None
        return caps[0]

    def _realized_carbon_map(self) -> dict[int, float]:
        carbon: dict[int, float] = {}
        for obs in self.episode.realized_carbon:
            if obs.valid_slot is None:
                continue
            if obs.valid_slot in carbon:
                raise HindsightError(
                    f"duplicate realized carbon observation for slot {obs.valid_slot}"
                )
            carbon[obs.valid_slot] = obs.value
        return carbon

    def _build_vars(self) -> None:
        for job in sorted(self.episode.jobs, key=lambda pj: pj.job.job_id):
            j = job.job
            for start in self._window(j):
                if not self._fits(start, j):
                    continue
                carbon = self._fresh_carbon(start, j.duration_slots)
                if carbon is None:
                    continue
                energy = self._energy_kwh(j)
                mean_carbon = sum(carbon) / len(carbon)
                self.vars.append(
                    _HindsightVar(
                        idx=len(self.vars),
                        job_id=j.job_id,
                        start_slot=start,
                        job=j,
                        energy_kwh=energy,
                        carbon_g_per_kwh=mean_carbon,
                    )
                )

    def _window(self, job: s.Job) -> tuple[int, ...]:
        horizon = self.horizon
        last_start = min(23, job.deadline_slot - job.duration_slots, horizon - job.duration_slots)
        if not job.flexible:
            arrival = job.arrival_slot
            if arrival > last_start or arrival + job.duration_slots > horizon:
                return ()
            return (arrival,)
        first = max(0, job.arrival_slot)
        if first > last_start:
            return ()
        return tuple(range(first, last_start + 1))

    def _fits(self, start: int, job: s.Job) -> bool:
        if self.capacity is None:
            return False
        return all(
            job.power_kw <= self.capacity for slot in range(start, start + job.duration_slots)
        )

    def _fresh_carbon(self, start: int, duration: int) -> Optional[tuple[float, ...]]:
        values: list[float] = []
        for slot in range(start, start + duration):
            value = self.carbon.get(slot)
            if value is None:
                return None
            values.append(value)
        return tuple(values)

    def _energy_kwh(self, job: s.Job) -> float:
        site = self.episode.snapshot.site
        return job.power_kw * job.duration_slots * site.slot_hours * site.pue

    def solve(self) -> s.SolverResult:
        if self.capacity is None:
            return self._insufficient_evidence("capacity constraint missing from snapshot")
        if len(self.carbon) != self.horizon:
            missing = sorted(set(range(self.horizon)) - self.carbon.keys())
            return self._insufficient_evidence(f"realized carbon missing for slots {missing}")
        if not self.vars:
            if self.episode.jobs:
                return self._certified_infeasible("no feasible start satisfies capacity/carbon")
            return self._certified_optimal([], 0.0, "empty episode")

        n = len(self.vars)
        c = np.array([var.emissions_kg for var in self.vars], dtype=float)

        job_ids = sorted({var.job_id for var in self.vars})
        job_index = {job_id: i for i, job_id in enumerate(job_ids)}
        a_job = np.zeros((len(job_ids), n))
        for var in self.vars:
            a_job[job_index[var.job_id], var.idx] = 1.0
        job_con = LinearConstraint(a_job, lb=1.0, ub=1.0)

        nonflex_jobs: dict[str, int] = {}
        for var in self.vars:
            if not var.job.flexible and var.start_slot == var.job.arrival_slot:
                nonflex_jobs[var.job_id] = var.idx
        nonflex_rows: list[np.ndarray] = []
        for job_id in job_ids:
            job = next(var.job for var in self.vars if var.job_id == job_id)
            if not job.flexible:
                if job_id not in nonflex_jobs:
                    return self._certified_infeasible(
                        f"non-flexible job {job_id} has no feasible start at arrival"
                    )
                row = np.zeros(n)
                row[nonflex_jobs[job_id]] = 1.0
                nonflex_rows.append(row)
        if nonflex_rows:
            a_nonflex = np.vstack(nonflex_rows)
            nonflex_con = LinearConstraint(a_nonflex, lb=1.0, ub=1.0)
        else:
            nonflex_con = None

        a_cap = np.zeros((self.horizon, n))
        for var in self.vars:
            for slot in range(var.start_slot, var.start_slot + var.job.duration_slots):
                a_cap[slot, var.idx] = var.job.power_kw
        cap_ub = np.array(
            [
                (self.capacity or 0.0) - self.episode.snapshot.site.background_kw
                for _ in range(self.horizon)
            ],
            dtype=float,
        )
        cap_con = LinearConstraint(a_cap, lb=-np.inf, ub=cap_ub)

        constraints = [job_con, cap_con]
        if nonflex_con is not None:
            constraints.append(nonflex_con)

        bounds = Bounds(lb=np.zeros(n), ub=np.ones(n))
        integrality = np.ones(n, dtype=int)

        try:
            res = milp(
                c=c,
                constraints=constraints,
                bounds=bounds,
                integrality=integrality,
                options={"time_limit": self.time_limit_s},
            )
        except Exception as exc:  # pragma: no cover - solver failure
            return self._unresolved(f"scipy milp raised {type(exc).__name__}: {exc}")

        if res.success and res.status == 0:
            selected = [var for var in self.vars if res.x[var.idx] > 0.5]
            objective = float(res.fun)
            return self._certified_optimal(selected, objective, res.message)
        if res.status == 2:
            return self._certified_infeasible(res.message)
        return self._unresolved(res.message)

    def _schedule_from(self, selected: list[_HindsightVar]) -> tuple[s.PlannedStart, ...]:
        starts = sorted(
            (s.PlannedStart(job_id=var.job_id, start_slot=var.start_slot) for var in selected),
            key=lambda ps: (ps.job_id, ps.start_slot),
        )
        return tuple(starts)

    def _input_hash(self) -> str:
        payload = {
            "episode_id": self.episode.episode_id,
            "snapshot_id": self.episode.snapshot.snapshot_id,
            "snapshot_hash": self.episode.snapshot.canonical_hash(),
            "jobs": sorted(
                [
                    [
                        pj.job.job_id,
                        pj.job.arrival_slot,
                        pj.job.duration_slots,
                        pj.job.power_kw,
                        pj.job.deadline_slot,
                        pj.job.flexible,
                    ]
                    for pj in self.episode.jobs
                ]
            ),
            "realized_carbon": sorted([[slot, value] for slot, value in self.carbon.items()]),
            "solver_version": _HINDSIGHT_VERSION,
            "tolerance": self.tolerance,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
                "utf-8"
            )
        ).hexdigest()

    def _certified_optimal(
        self, selected: list[_HindsightVar], objective_kg: float, termination: str
    ) -> s.SolverResult:
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="hindsight",
            uses_future_arrivals=True,
            input_hash=self._input_hash(),
            status="certified_optimal",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            elapsed_s=0.0,
            termination=termination,
            tolerance=self.tolerance,
            objective_kg=objective_kg,
            schedule=self._schedule_from(selected),
            tie_break="lexicographic (job_id, start_slot)",
            certification_basis=(
                "scipy.optimize.milp mixed-integer linear program; "
                "minimize realized emissions over full episode; "
                "capacity + one-start + nonflexible constraints; "
                "uses private realized carbon and future arrivals"
            ),
            matching_work_job_ids=tuple(sorted({var.job_id for var in selected})),
        )

    def _certified_infeasible(self, reason: str) -> s.SolverResult:
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="hindsight",
            uses_future_arrivals=True,
            input_hash=self._input_hash(),
            status="certified_infeasible",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            elapsed_s=0.0,
            termination=reason,
            tolerance=self.tolerance,
            certification_basis="scipy.optimize.milp proved infeasibility over full episode",
        )

    def _unresolved(self, reason: str) -> s.SolverResult:
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="hindsight",
            uses_future_arrivals=True,
            input_hash=self._input_hash(),
            status="unresolved",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            elapsed_s=self.time_limit_s,
            termination=reason,
            tolerance=self.tolerance,
            unresolved_reason=reason,
        )

    def _insufficient_evidence(self, reason: str) -> s.SolverResult:
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="hindsight",
            uses_future_arrivals=True,
            input_hash=self._input_hash(),
            status="insufficient_evidence",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            elapsed_s=0.0,
            termination=reason,
            tolerance=self.tolerance,
            unresolved_reason=reason,
        )


def _new_solver_id() -> str:
    return f"SOLVE-HINDSIGHT-{uuid.uuid4().hex[:16].upper()}"


def _validate_episode(episode: s.PrivateEpisode) -> None:
    """Reject episodes that cannot safely become a hindsight reference."""
    if not isinstance(episode, s.PrivateEpisode):
        raise HindsightError("hindsight requires a PrivateEpisode")
    if (episode.n_decision_slots, episode.n_completion_slots) != (24, 6):
        raise HindsightError("hindsight solver requires 24 decision + 6 completion slots")
    if not episode.jobs:
        raise HindsightError("episode contains no jobs")
    job_ids = [pj.job.job_id for pj in episode.jobs]
    if len(set(job_ids)) != len(job_ids):
        raise HindsightError("duplicate job ids in episode")
    if not episode.realized_carbon:
        raise HindsightError("episode has no realized carbon observations")
    n_slots = episode.n_decision_slots + episode.n_completion_slots
    slots = [obs.valid_slot for obs in episode.realized_carbon if obs.valid_slot is not None]
    if sorted(slots) != list(range(n_slots)):
        raise HindsightError(f"realized carbon must cover every slot 0..{n_slots - 1} exactly once")


def _job_has_feasible_window(job: s.Job, horizon: int) -> bool:
    """Return True if the job can fit inside the horizon before its deadline."""
    last_start = min(job.deadline_slot - job.duration_slots, horizon - job.duration_slots)
    return job.arrival_slot <= last_start and job.arrival_slot + job.duration_slots <= horizon


def solve_hindsight(
    episode: s.PrivateEpisode,
    *,
    time_limit_s: float = _TIME_LIMIT_S,
    tolerance: float = _TOLERANCE,
) -> s.SolverResult:
    """Solve one complete private episode offline and return a hindsight SolverResult."""
    _validate_episode(episode)
    model = _HindsightMILP(episode, time_limit_s=time_limit_s, tolerance=tolerance)
    return model.solve()


class HindsightReferenceArtifact(s.Record):
    """Offline envelope around a hindsight SolverResult with provenance and identity."""

    record_type: str = "HindsightReferenceArtifact"
    schema_version: str = s.SCHEMA_VERSION
    artifact_id: s.GenericId
    episode_id: s.EpisodeId
    generated_at_utc: s.UtcTime
    solver_version: str
    solver_config_hash: s.Hex64
    source_snapshot_hash: s.Hex64
    realized_carbon_hash: s.Hex64
    solver_result: s.SolverResult
    complete: bool
    offline_only: bool = True

    def to_manifest(self) -> dict[str, Any]:
        """Return a JSON-serializable provenance sidecar for this artifact."""
        return {
            "artifact_id": self.artifact_id,
            "episode_id": self.episode_id,
            "schema_version": self.schema_version,
            "generated_at_utc": self.generated_at_utc.isoformat().replace("+00:00", "Z"),
            "solver_version": self.solver_version,
            "solver_config_hash": self.solver_config_hash,
            "source_snapshot_hash": self.source_snapshot_hash,
            "realized_carbon_hash": self.realized_carbon_hash,
            "solver_result_id": self.solver_result.solver_result_id,
            "solver_result_status": self.solver_result.status,
            "solver_result_kind": self.solver_result.kind,
            "uses_future_arrivals": self.solver_result.uses_future_arrivals,
            "offline_only": self.offline_only,
            "complete": self.complete,
        }


def _realized_carbon_hash(episode: s.PrivateEpisode) -> str:
    payload = [
        {
            "fact_id": obs.fact_id,
            "valid_slot": obs.valid_slot,
            "value": obs.value,
            "source_id": obs.source_id,
        }
        for obs in sorted(episode.realized_carbon, key=lambda o: o.valid_slot)
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _solver_config_hash(
    *,
    time_limit_s: float,
    tolerance: float,
    backend: str,
    backend_version: str,
) -> str:
    payload = {
        "time_limit_s": time_limit_s,
        "tolerance": tolerance,
        "backend": backend,
        "backend_version": backend_version,
        "solver_version": _HINDSIGHT_VERSION,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def generate_hindsight_reference(
    episode: s.PrivateEpisode,
    *,
    time_limit_s: float = _TIME_LIMIT_S,
    tolerance: float = _TOLERANCE,
) -> HindsightReferenceArtifact:
    """Generate a validated hindsight reference artifact for one private episode."""
    _validate_episode(episode)
    result = solve_hindsight(episode, time_limit_s=time_limit_s, tolerance=tolerance)
    if result.kind != "hindsight" or not result.uses_future_arrivals or not result.offline_only:
        raise HindsightError("solver result is not a hindsight result")
    scheduled_ids = {ps.job_id for ps in (result.schedule or ())}
    feasible_ids = {
        pj.job.job_id
        for pj in episode.jobs
        if _job_has_feasible_window(pj.job, episode.n_decision_slots + episode.n_completion_slots)
    }
    complete = result.status == "certified_optimal" and scheduled_ids == feasible_ids
    return HindsightReferenceArtifact(
        artifact_id=f"HINDSIGHT-{uuid.uuid4().hex[:16].upper()}",
        episode_id=episode.episode_id,
        generated_at_utc=datetime.now(timezone.utc),
        solver_version=_HINDSIGHT_VERSION,
        solver_config_hash=_solver_config_hash(
            time_limit_s=time_limit_s,
            tolerance=tolerance,
            backend=result.backend,
            backend_version=result.backend_version,
        ),
        source_snapshot_hash=episode.snapshot.canonical_hash(),
        realized_carbon_hash=_realized_carbon_hash(episode),
        solver_result=result,
        complete=complete,
    )


def export_hindsight_reference(
    artifact: HindsightReferenceArtifact,
    directory: Path,
) -> tuple[Path, Path]:
    """Atomically write artifact JSON and manifest sidecar to ``directory``.

    The directory must already exist and must not be inside a Git checkout. Files
    are written with restrictive permissions and no overwrite.
    """
    directory = directory.resolve(strict=True)
    if not directory.is_dir() or any(
        (p / ".git").exists() for p in (directory, *directory.parents)
    ):
        raise HindsightError("hindsight export must target a directory outside Git checkouts")
    artifact_path = directory / f"{artifact.artifact_id}.json"
    manifest_path = directory / f"{artifact.artifact_id}.manifest.json"
    if artifact_path.exists() or manifest_path.exists():
        raise HindsightError(f"artifact files already exist: {artifact.artifact_id}")

    artifact_json = artifact.to_json()
    manifest_json = json.dumps(artifact.to_manifest(), sort_keys=True, indent=2, allow_nan=False)

    fd, tmp_artifact = tempfile.mkstemp(dir=directory, prefix=".hindsight-artifact-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(artifact_json + "\n")
        os.chmod(tmp_artifact, 0o600)
        fd2, tmp_manifest = tempfile.mkstemp(
            dir=directory, prefix=".hindsight-manifest-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd2, "w", encoding="utf-8") as stream:
                stream.write(manifest_json + "\n")
            os.chmod(tmp_manifest, 0o600)
            os.rename(tmp_artifact, artifact_path)
            os.rename(tmp_manifest, manifest_path)
        except Exception:
            try:
                os.unlink(tmp_manifest)
            except FileNotFoundError:
                pass
            raise
    except Exception:
        try:
            os.unlink(tmp_artifact)
        except FileNotFoundError:
            pass
        raise
    return artifact_path, manifest_path


def load_hindsight_reference(path: Path) -> HindsightReferenceArtifact:
    """Load a previously exported hindsight reference artifact and validate it."""
    path = path.resolve()
    if not path.is_file():
        raise HindsightError(f"not a file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    artifact = HindsightReferenceArtifact.model_validate(data)
    if artifact.offline_only is not True:
        raise HindsightError("loaded artifact is not marked offline_only")
    if artifact.solver_result.kind != "hindsight":
        raise HindsightError("loaded solver result is not a hindsight result")
    if not artifact.solver_result.uses_future_arrivals:
        raise HindsightError("loaded solver result does not use future arrivals")
    return artifact


def reject_hindsight_in_context(context: Union[s.Context, dict[str, Any]]) -> None:
    """Defensive check: raise if a context contains hindsight-only evidence.

    Accepts either a ``Context`` record or its JSONable dict form so the check
    can be applied to deserialized/poisoned payloads that may not validate as a
    regular ``Context``.
    """
    if isinstance(context, s.Context):
        jsonable = context.to_jsonable()
    elif isinstance(context, dict):
        jsonable = context
    else:
        raise HindsightError("context must be a Context record or JSONable dict")
    content = jsonable.get("content", {})
    if content.get("solver_result_kind") == "hindsight":
        raise HindsightError("hindsight solver results are not policy-visible")
    for key in ("hindsight", "realized_carbon", "uses_future_arrivals"):
        if key in content:
            raise HindsightError(f"hindsight-only key {key!r} found in policy context")
