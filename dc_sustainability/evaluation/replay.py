"""E01 independent episode replay.

Rebuilds the state at every slot boundary from a private episode and the starts that were
actually executed, then checks those executions and the episode outcome. It does not
import or call the simulator, the production checker or shared impact code, so a
simulator or trace defect shows up as a mismatch instead of being copied.

Timing follows the shared rules and the Q01 draft: occupancy is [start, start + duration),
new starts only through ``protocol.last_start_slot`` and all work ends by boundary 30. A
waiting job is missed at the first boundary where no legal start remains, so a job that is
already impossible when it arrives is missed at its arrival boundary.
"""

import math
from dataclasses import dataclass
from typing import Iterable, Literal, Mapping

from dc_sustainability import schemas as s
from dc_sustainability.evaluation.validator import Protocol, _legal_starts

END = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS

ReplayCode = Literal[
    "executed_slot_mismatch",  # recorded start slot differs from its decision slot
    "executed_unknown_job",
    "executed_not_waiting",  # not arrived, running, completed, missed or started twice
    "capacity",
    "capacity_unverifiable",
]


@dataclass(frozen=True)
class ReplayFinding:
    code: ReplayCode
    slot: int
    job_id: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class Boundary:
    """Derived state at boundary t, before that slot's starts."""

    slot: int
    waiting: tuple[str, ...]
    running: tuple[tuple[str, int], ...]  # job ID and start slot, still occupying t
    completed: tuple[tuple[str, int, int], ...]  # job ID, start and end (end <= t)
    missed: tuple[str, ...]


@dataclass(frozen=True)
class SlotOutcome:
    """What happened during slot t."""

    slot: int
    started: tuple[str, ...]
    running: tuple[str, ...]  # every job occupying t, including new starts
    completed: tuple[str, ...]  # jobs finishing at boundary t + 1
    job_load_kw: float


@dataclass(frozen=True)
class Mismatch:
    """A recorded value that differs from the replay; the replay is not changed."""

    field: str
    slot: int | None
    expected: object
    recorded: object


@dataclass(frozen=True)
class Replay:
    episode: s.PrivateEpisode
    protocol: str
    boundaries: tuple[Boundary, ...]  # boundaries 0..30
    slots: tuple[SlotOutcome, ...]  # slots 0..29
    findings: tuple[ReplayFinding, ...]
    completed_job_ids: tuple[str, ...]
    missed_job_ids: tuple[str, ...]
    unfinished_job_ids: tuple[str, ...]  # everything not completed, missed jobs included
    completed_it_energy_kwh: float  # completed jobs only, before PUE (Q03.5)

    @property
    def valid(self) -> bool:
        return not self.findings

    def state_at(
        self, slot: int, carbon_facts: tuple[s.CarbonForecast, ...] = ()
    ) -> s.VisibleState:
        """The visible state the replay derives at a decision boundary.

        Forecasts are supplied by the caller, as the episode holds only private actuals.
        Pass the result to ``validator.facts_from_state`` to judge a plan against
        replayed state instead of a state the runtime supplied.
        """
        if not 0 <= slot < s.PROPOSED_DECISION_SLOTS:
            raise ValueError("only decision boundaries have a visible decision state")
        jobs = {p.job.job_id: p.job for p in self.episode.jobs}
        b = self.boundaries[slot]
        present = {f.valid_slot for f in carbon_facts}
        return s.VisibleState.from_snapshot(
            self.episode.snapshot,
            episode_id=self.episode.episode_id,
            current_slot=slot,
            state_version=slot,
            waiting_jobs=tuple(jobs[j] for j in b.waiting),
            running_jobs=tuple(s.RunningJobView(job=jobs[j], start_slot=st) for j, st in b.running),
            completed_jobs=tuple(
                s.CompletedJobView(job_id=j, start_slot=st, end_slot=end)
                for j, st, end in b.completed
            ),
            missed_job_ids=b.missed,
            carbon_facts=carbon_facts,
            missing_carbon_slots=tuple(
                t
                for t in range(slot, min(slot + s.PROPOSED_DECISION_SLOTS, END))
                if t not in present
            ),
        )


def _capacity(snapshot: s.ConstraintSnapshot) -> float | None:
    """The single site capacity limit, or None when capacity evidence is missing."""
    caps = [
        c
        for c in snapshot.constraints
        if c.constraint_type == "capacity" and c.applies_to_site == snapshot.site.site_id
    ]
    return caps[0].limit_value if len(caps) == 1 else None


def executed_starts(
    records: Iterable[s.DecisionRecord], episode_id: str
) -> dict[int, tuple[s.ApprovedStart, ...]]:
    """Collect executed starts by decision slot from one run's decision records.

    Records must belong to the episode and to one run, system and trial, with at most one
    record per slot; anything else is a trace defect and is refused rather than merged.
    """
    by_slot: dict[int, tuple[s.ApprovedStart, ...]] = {}
    runs = set()
    for record in records:
        record = s.DecisionRecord.model_validate(
            record.model_dump(mode="python", warnings="none"), strict=True
        )
        if record.episode_id != episode_id:
            raise ValueError(f"{record.decision_id} belongs to another episode")
        runs.add((record.run_id, record.system, record.trial))
        if len(runs) > 1:
            raise ValueError("records mix runs, systems or trials")
        if record.slot in by_slot:
            raise ValueError(f"more than one decision record for slot {record.slot}")
        by_slot[record.slot] = record.executed_starts
    return by_slot


def replay_episode(
    episode: s.PrivateEpisode,
    executed: Mapping[int, Iterable[s.ApprovedStart]],
    protocol: Protocol,
) -> Replay:
    """Replay executed starts slot by slot and report every execution the rules forbid.

    A start for a job that cannot run (unknown, not waiting, or recorded at another slot)
    is reported and not applied. A start that overloads capacity is applied, because the
    job did run, and each overloaded slot is reported.
    """
    episode = s.PrivateEpisode.model_validate(
        episode.model_dump(mode="python", warnings="none"), strict=True
    )
    if (episode.n_decision_slots, episode.n_completion_slots) != (
        s.PROPOSED_DECISION_SLOTS,
        s.PROPOSED_COMPLETION_SLOTS,
    ):
        raise ValueError("replay requires the proposal's 24 decision and 6 completion slots")
    if any(type(t) is not int or not 0 <= t < END for t in executed):
        raise ValueError("executed starts must be keyed by slots 0..29")
    jobs = {p.job.job_id: p.job for p in episode.jobs}
    if episode.snapshot.site.slot_hours != 1:
        raise ValueError("replay requires hourly slots")
    for constraint in episode.snapshot.constraints:
        for job_id in constraint.applies_to_jobs:
            if job_id not in jobs:
                raise ValueError(
                    f"constraint {constraint.constraint_id} names unknown job {job_id}"
                )
            job = jobs[job_id]
            expected = {
                "arrival": job.arrival_slot,
                "deadline": job.deadline_slot,
                "nonflexible": job.arrival_slot,
            }
            kind = constraint.constraint_type
            if kind in expected and (
                constraint.limit_value != expected[kind] or (kind == "nonflexible" and job.flexible)
            ):
                raise ValueError(f"constraint {constraint.constraint_id} contradicts job {job_id}")
    capacity = _capacity(episode.snapshot)
    background = episode.snapshot.site.background_kw

    running: dict[str, int] = {}
    completed: dict[str, tuple[int, int]] = {}
    missed: set[str] = set()
    boundaries, slots, findings = [], [], []
    for t in range(END + 1):
        for job_id, st in list(running.items()):
            if st + jobs[job_id].duration_slots <= t:
                completed[job_id] = (st, st + jobs[job_id].duration_slots)
                del running[job_id]
        arrived = [j for j, job in sorted(jobs.items()) if job.arrival_slot <= t]
        for job_id in arrived:
            if job_id in running or job_id in completed or job_id in missed:
                continue
            if not _legal_starts(jobs[job_id], t, protocol):
                missed.add(job_id)
        waiting = [
            j for j in arrived if j not in running and j not in completed and j not in missed
        ]
        boundaries.append(
            Boundary(
                slot=t,
                waiting=tuple(waiting),
                running=tuple(sorted(running.items())),
                completed=tuple(sorted((j, st, end) for j, (st, end) in completed.items())),
                missed=tuple(sorted(missed)),
            )
        )
        if t == END:
            break

        started: list[str] = []
        for start in executed.get(t, ()):
            start = s.ApprovedStart.model_validate(
                start.model_dump(mode="python", warnings="none"), strict=True
            )
            job_id = start.job_id
            if start.start_slot != t:
                findings.append(
                    ReplayFinding(
                        "executed_slot_mismatch", t, job_id, f"start_slot {start.start_slot}"
                    )
                )
            elif job_id not in jobs:
                findings.append(ReplayFinding("executed_unknown_job", t, job_id))
            elif job_id not in waiting or job_id in started:
                findings.append(
                    ReplayFinding(
                        "executed_not_waiting",
                        t,
                        job_id,
                        _why(job_id, t, jobs, running, completed, missed, started),
                    )
                )
            else:
                started.append(job_id)
                running[job_id] = t
        if started and capacity is None:
            findings.append(
                ReplayFinding("capacity_unverifiable", t, detail="no capacity constraint")
            )

        occupying = sorted(running)  # everything in ``running`` occupies t
        load = math.fsum(jobs[j].power_kw for j in occupying)
        if capacity is not None and background + load > capacity:
            findings.append(ReplayFinding("capacity", t, detail=f"{background + load:g} kW"))
        slots.append(
            SlotOutcome(
                slot=t,
                started=tuple(sorted(started)),
                running=tuple(occupying),
                completed=tuple(
                    j for j in occupying if running[j] + jobs[j].duration_slots == t + 1
                ),
                job_load_kw=load,
            )
        )

    done = tuple(sorted(completed))
    return Replay(
        episode=episode,
        protocol=protocol.name,
        boundaries=tuple(boundaries),
        slots=tuple(slots),
        findings=tuple(findings),
        completed_job_ids=done,
        missed_job_ids=tuple(sorted(missed)),
        unfinished_job_ids=tuple(sorted(set(jobs) - set(completed))),
        completed_it_energy_kwh=math.fsum(
            jobs[j].power_kw * jobs[j].duration_slots * episode.snapshot.site.slot_hours
            for j in done
        ),
    )


def _why(job_id, t, jobs, running, completed, missed, started) -> str:
    if jobs[job_id].arrival_slot > t:
        return "not arrived"
    if job_id in started:
        return "started twice in one slot"
    if job_id in running:
        return "already running"
    if job_id in completed:
        return "already completed"
    return "missed" if job_id in missed else "not waiting"


def _same_kw(a: float, b: float) -> bool:
    # Reporting comparison only, for float summation order; never a feasibility boundary.
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)


def compare_result(replay: Replay, result: s.EpisodeResult) -> tuple[Mismatch, ...]:
    """Compare structural outcomes and loads, not impact totals or unagreed work units.

    A supplied completed_work scalar cannot receive a clean result without an agreed
    unit/definition mapping. Per-slot/total energy and emissions remain outside this
    structural comparison until independent impact reference selection is established.
    """
    result = s.EpisodeResult.model_validate(
        result.model_dump(mode="python", warnings="none"), strict=True
    )
    if result.episode_id != replay.episode.episode_id:
        raise ValueError("the result belongs to another episode")
    if result.completed_work is not None:
        raise ValueError("completed_work comparison requires an agreed unit/definition mapping")
    out: list[Mismatch] = []

    def check(field, slot, expected, recorded):
        if expected != recorded:
            out.append(Mismatch(field, slot, expected, recorded))

    check("n_decision_slots", None, s.PROPOSED_DECISION_SLOTS, result.n_decision_slots)
    check("n_completion_slots", None, s.PROPOSED_COMPLETION_SLOTS, result.n_completion_slots)
    check("job_count_total", None, len(replay.episode.jobs), result.job_count_total)
    check(
        "completed_job_ids", None, replay.completed_job_ids, tuple(sorted(result.completed_job_ids))
    )
    check(
        "deadline_missed_job_ids",
        None,
        replay.missed_job_ids,
        tuple(sorted(result.deadline_missed_job_ids)),
    )
    check(
        "unfinished_job_ids",
        None,
        replay.unfinished_job_ids,
        tuple(sorted(result.unfinished_job_ids)),
    )
    background = replay.episode.snapshot.site.background_kw
    for mine, theirs in zip(replay.slots, result.slots):
        t = mine.slot
        check(
            "phase", t, "decision" if t < s.PROPOSED_DECISION_SLOTS else "completion", theirs.phase
        )
        check("started_job_ids", t, mine.started, tuple(sorted(theirs.started_job_ids)))
        check("running_job_ids", t, mine.running, tuple(sorted(theirs.running_job_ids)))
        check("completed_job_ids", t, mine.completed, tuple(sorted(theirs.completed_job_ids)))
        if not _same_kw(mine.job_load_kw, theirs.job_load_kw):
            out.append(Mismatch("job_load_kw", t, mine.job_load_kw, theirs.job_load_kw))
        if not _same_kw(background, theirs.background_load_kw):
            out.append(Mismatch("background_load_kw", t, background, theirs.background_load_kw))
    return tuple(out)


def compare_state(replay: Replay, state: s.VisibleState) -> tuple[Mismatch, ...]:
    """Compare job state and authoritative metadata against the replayed boundary.

    Forecast issuance and mutation-version history cannot be derived from executed
    starts alone and are not certified by this structural comparison.
    """
    state = s.VisibleState.model_validate(
        state.model_dump(mode="python", warnings="none"), strict=True
    )
    if state.episode_id != replay.episode.episode_id:
        raise ValueError("the state belongs to another episode")
    t = state.current_slot
    b = replay.boundaries[t]
    snapshot = replay.episode.snapshot
    known = (
        set(b.waiting) | {j for j, _ in b.running} | {j for j, _, _ in b.completed} | set(b.missed)
    )
    constraint_ids = tuple(
        sorted(
            constraint.constraint_id
            for constraint in snapshot.constraints
            if constraint.applies_to_site == snapshot.site.site_id
            or (constraint.applies_to_jobs and set(constraint.applies_to_jobs) <= known)
        )
    )
    recorded = {
        "constraint_snapshot_id": state.constraint_snapshot_id,
        "site": state.site,
        "constraint_ids": tuple(sorted(state.constraint_ids)),
        "waiting": tuple(sorted(j.job_id for j in state.waiting_jobs)),
        "running": tuple(sorted((r.job.job_id, r.start_slot) for r in state.running_jobs)),
        "completed": tuple(
            sorted((c.job_id, c.start_slot, c.end_slot) for c in state.completed_jobs)
        ),
        "missed": tuple(sorted(state.missed_job_ids)),
    }
    expected = {
        "constraint_snapshot_id": snapshot.snapshot_id,
        "site": snapshot.site,
        "constraint_ids": constraint_ids,
        "waiting": b.waiting,
        "running": b.running,
        "completed": b.completed,
        "missed": b.missed,
    }
    out = [Mismatch(k, t, expected[k], recorded[k]) for k in expected if expected[k] != recorded[k]]
    jobs = {p.job.job_id: p.job for p in replay.episode.jobs}
    for job in (*state.waiting_jobs, *(r.job for r in state.running_jobs)):
        if jobs.get(job.job_id) != job:
            out.append(Mismatch("job_record", t, jobs.get(job.job_id), job))
    return tuple(out)
