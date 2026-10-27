"""D04 private, provisional allocation metadata; never a policy or frozen-data interface.

No source values, jobs, forecasts, labels or held-out episode contents are read/generated.
All caller seeds and candidate dates are explicit. Q05/Q06 remain open.
"""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from importlib.metadata import version
from pathlib import Path

from dc_sustainability.data import carbon_source, scenarios
from dc_sustainability.schemas import SCHEMA_VERSION

VERSION = "d04-provisional-v1"
SCENARIOS = tuple(scenarios.SCENARIOS)


def digest(value: object) -> str:
    """D04 canonical metadata hash: sorted UTF-8 JSON, no whitespace/NaN."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _seed(value: int) -> None:
    if type(value) is not int:
        raise ValueError("seed must be an integer")


@dataclass(frozen=True)
class Window:
    """30 physical-hour indices CONDITIONAL on proposed start-label mapping.

    Source byte identity, not a caller alias/path, determines intersections.
    Half-open UTC boundaries include the entire next-day completion tail.
    """

    day: date
    source_sha256: str = carbon_source.SHA256

    def __post_init__(self):
        if type(self.day) is not date:
            raise ValueError("day must be a date")
        if len(self.source_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.source_sha256
        ):
            raise ValueError("source identity must be a lowercase SHA-256")
        self.indices  # fail closed at year boundaries; no wrapping

    @property
    def indices(self) -> tuple[int, ...]:
        return carbon_source.episode_indices(self.day, interval_convention="start")

    @property
    def start(self) -> datetime:
        return carbon_source.START + self.indices[0] * carbon_source.HOUR

    @property
    def end(self) -> datetime:
        return self.start + 30 * carbon_source.HOUR

    def overlaps(self, other: Window) -> bool:
        return (
            self.source_sha256 == other.source_sha256
            and self.start < other.end
            and other.start < self.end
        )

    def metadata(self) -> dict:
        return {
            "date": self.day.isoformat(),
            "source_sha256": self.source_sha256,
            "proposed_physical_indices": list(self.indices),
            "proposed_start_utc": self.start.isoformat(),
            "proposed_end_exclusive_utc": self.end.isoformat(),
            "source_interval_semantics": "unverified",
            "mapping": "proposed_interval_start_not_scientifically_adopted",
        }


@dataclass(frozen=True)
class Allocation:
    episode_id: str
    partition: str
    scenario: str
    seed: int
    window: Window
    related_group: str
    withheld: bool = False
    parent_id: str | None = None
    fold: int | None = None

    def __post_init__(self):
        _seed(self.seed)
        if not self.episode_id or not self.related_group:
            raise ValueError("episode ID and related group are required")
        if self.partition not in ("development", "held_out") or self.scenario not in SCENARIOS:
            raise ValueError("unknown partition or scenario")
        if type(self.withheld) is not bool or self.withheld != (self.parent_id is not None):
            raise ValueError("withheld variants require a parent; base allocations cannot have one")
        if self.withheld and self.scenario != "normal":
            raise ValueError("only normal has a withheld variant")
        if self.fold is not None and (type(self.fold) is not int or self.fold not in range(3)):
            raise ValueError("fold must be 0, 1, 2 or None")
        if self.partition == "held_out" and self.fold is not None:
            raise ValueError("held-out allocations have no development fold")

    def metadata(self) -> dict:
        record = {k: v for k, v in asdict(self).items() if k != "window"}
        record["window"] = self.window.metadata()
        record["episode_content_sha256"] = None  # no held-out contents generated to hash
        record["allocation_sha256"] = digest(record)
        return record


def overlap_report(records: tuple[Allocation, ...]) -> tuple[tuple[str, str], ...]:
    """Report all intersections, including permitted same-partition/fold sharing."""
    ordered = sorted(records, key=lambda r: r.episode_id)
    return tuple(
        (a.episode_id, b.episode_id)
        for i, a in enumerate(ordered)
        for b in ordered[i + 1 :]
        if a.window.overlaps(b.window)
    )


def _components(records: tuple[Allocation, ...]) -> list[list[Allocation]]:
    """Transitive closure of related groups AND source-window overlaps."""
    remaining = list(sorted(records, key=lambda r: (r.window.start, r.episode_id)))
    groups = []
    while remaining:
        group = [remaining.pop(0)]
        while True:
            attached = [
                r
                for r in remaining
                if any(
                    r.related_group == g.related_group or r.window.overlaps(g.window) for g in group
                )
            ]
            if not attached:
                break
            group.extend(attached)
            remaining = [r for r in remaining if r not in attached]
        groups.append(group)
    return groups


def validate_isolation(records: tuple[Allocation, ...], *, require_folds: bool = True) -> None:
    """Reject cross-partition or cross-fold components, including related variants."""
    ids = {r.episode_id: r for r in records}
    if len(ids) != len(records):
        raise ValueError("duplicate episode ID")
    for r in records:
        if require_folds and r.partition == "development" and r.fold is None:
            raise ValueError("development fold missing")
        if r.parent_id is not None:
            parent = ids.get(r.parent_id)
            if (
                parent is None
                or parent.withheld
                or any(
                    getattr(parent, field) != getattr(r, field)
                    for field in (
                        "partition",
                        "scenario",
                        "seed",
                        "window",
                        "related_group",
                        "fold",
                    )
                )
            ):
                raise ValueError("variant must retain its normal parent's window, seed and group")
    for group in _components(records):
        if len({r.partition for r in group}) > 1:
            raise ValueError("cross-partition related/overlapping 30-hour source windows")
        if len({r.fold for r in group}) > 1:
            raise ValueError("cross-fold related/overlapping 30-hour source windows")


def blocked_folds(records: tuple[Allocation, ...]) -> tuple[Allocation, ...]:
    """Propose three chronological blocks of connected groups (not shuffled rows).

    Boundaries divide group count as evenly as possible; episode counts can differ.
    Overlapping dates, all scenarios of a date and related variants stay together.
    """
    if any(r.partition != "development" for r in records):
        raise ValueError("fold allocation accepts development metadata only")
    validate_isolation(records, require_folds=False)
    components = _components(records)
    groups: list[list[Allocation]] = []
    # A related group can span distant dates. Absorb intervening components so
    # chronological folds cannot interleave even when their windows do not overlap.
    for group in components:
        if groups and min(r.window.start for r in group) < max(r.window.end for r in groups[-1]):
            groups[-1].extend(group)
        else:
            groups.append(group)
    if len(groups) < 3:
        raise ValueError("three blocked folds require at least three independent groups")
    sizes = [len(groups) // 3 + (i < len(groups) % 3) for i in range(3)]
    assigned = {}
    offset = 0
    for fold, size in enumerate(sizes):
        for group in groups[offset : offset + size]:
            for r in group:
                assigned[r.episode_id] = replace(r, fold=fold)
        offset += size
    result = tuple(assigned[r.episode_id] for r in records)
    validate_isolation(result)
    return result


def _rank(seed: int, namespace: str, value: str) -> tuple[str, str]:
    return digest([VERSION, seed, namespace, value]), value


def _dates(candidates: tuple[date, ...], low: int, high: int) -> tuple[date, ...]:
    if not candidates or any(type(d) is not date for d in candidates):
        raise ValueError("nonempty explicit date candidates required")
    if len(set(candidates)) != len(candidates):
        raise ValueError("duplicate candidate date")
    if any(d.year != 2022 or not low <= d.day <= high for d in candidates):
        raise ValueError(f"dates must be in 2022, days {low}..{high}")
    return tuple(sorted(candidates))


def _select_windows(dev_pool, held_pool, date_seed):
    selected: list[Window] = []
    partitions = []
    for partition, pool, count in (("development", dev_pool, 10), ("held_out", held_pool, 6)):
        chosen = []
        for day in sorted(pool, key=lambda d: _rank(date_seed, partition, d.isoformat())):
            window = Window(day)
            if partition == "held_out" and any(w.day.month == day.month for w in chosen):
                continue
            if any(window.overlaps(w) for w in selected):
                continue
            chosen.append(window)
            selected.append(window)
            if len(chosen) == count:
                break
        if len(chosen) != count:
            raise ValueError(
                f"insufficient isolated candidate dates for {partition}; no seed retry"
            )
        partitions.append((partition, sorted(chosen, key=lambda w: w.day)))
    return partitions


@dataclass(frozen=True)
class Proposal:
    """Private allocation plan, not an F02 object or approval token."""

    records: tuple[Allocation, ...]
    development_candidates: tuple[date, ...]
    held_out_candidates: tuple[date, ...]
    date_seed: int
    job_seed: int

    def validate(self) -> None:
        _seed(self.date_seed)
        _seed(self.job_seed)
        _dates(self.development_candidates, 1, 14)
        _dates(self.held_out_candidates, 15, 28)
        validate_isolation(self.records)
        dev = [r for r in self.records if r.partition == "development"]
        held = [r for r in self.records if r.partition == "held_out"]
        if len(dev) != 40 or len(held) != 30:
            raise ValueError("proposal requires 40 development and 30 held-out allocations")
        for rows, n, candidates in (
            (dev, 10, self.development_candidates),
            (held, 6, self.held_out_candidates),
        ):
            days = {r.window.day for r in rows}
            if len(days) != n or not days <= set(candidates):
                raise ValueError("allocation dates differ from candidate pool/count")
            for day in days:
                base = [r.scenario for r in rows if r.window.day == day and not r.withheld]
                if sorted(base) != sorted(SCENARIOS):
                    raise ValueError("each date needs all four base scenarios")
            if any(r.window.source_sha256 != carbon_source.SHA256 for r in rows):
                raise ValueError("proposal source must be the pinned D01 source")
        if any(r.withheld for r in dev) or sum(r.withheld for r in held) != 6:
            raise ValueError("six held-out normal withheld variants required")
        if len({r.window.day.month for r in held}) != 6:
            raise ValueError("six held-out dates must use different months")
        if {r.fold for r in dev} != {0, 1, 2}:
            raise ValueError("three nonempty development folds required")
        # Every selected day has exactly one variant, linked to that day's normal.
        if len({r.parent_id for r in held if r.withheld}) != 6:
            raise ValueError("withheld variants must have six distinct parents")

        selected = _select_windows(
            self.development_candidates, self.held_out_candidates, self.date_seed
        )
        for partition, windows in selected:
            if {r.window for r in self.records if r.partition == partition} != set(windows):
                raise ValueError("selected dates differ from recorded date seed/pools")
        for row in self.records:
            identity = digest([VERSION, row.window.day.isoformat(), row.scenario])[:24]
            expected_id = "EP-" + (
                digest([VERSION, identity, "withheld"])[:24] if row.withheld else identity
            )
            if row.episode_id != expected_id or row.related_group != digest(
                [row.window.source_sha256, row.window.day.isoformat()]
            ):
                raise ValueError("allocation ID/group differs from recorded derivation")
            expected_seed = int(
                digest([VERSION, self.job_seed, row.window.day.isoformat(), row.scenario])[:16], 16
            )
            if row.seed != expected_seed:
                raise ValueError("allocation seed differs from recorded derivation")
        unfolded = tuple(replace(r, fold=None) for r in dev)
        if tuple(dev) != blocked_folds(unfolded):
            raise ValueError("folds differ from chronological block proposal")

    def development_records(self) -> tuple[Allocation, ...]:
        """Private development tooling boundary. Never returns held-out metadata."""
        self.validate()
        return tuple(r for r in self.records if r.partition == "development")

    def development_record(self, episode_id: str) -> Allocation:
        for record in self.development_records():
            if record.episode_id == episode_id:
                return record
        raise ValueError("not a development allocation; held-out access is unavailable")

    def development_manifest(self, *, code_revision: str) -> dict:
        """Private training metadata with no held-out dates, seeds or parent records.

        Still not policy-visible: contains development split/scenario/seed metadata.
        Root selection/job seeds and candidate pools stay in evaluator custody.
        """
        private = self.private_manifest(code_revision=code_revision)
        allowed = (
            "version",
            "status",
            "code_revision",
            "code_file_sha256",
            "runtime",
            "schema_version",
            "generator_version",
            "source",
            "distribution_status",
            "distribution_specification",
            "fold_algorithm",
            "scientific_acceptance",
        )
        manifest = {key: private[key] for key in allowed}
        manifest["visibility"] = "private_development_tooling_not_policy_input"
        manifest["records"] = [r.metadata() for r in self.development_records()]
        manifest["overlaps"] = overlap_report(self.development_records())
        manifest["manifest_sha256"] = digest(manifest)
        return manifest

    def private_manifest(self, *, code_revision: str) -> dict:
        """Evaluator-custody metadata only. Caller supplies actual code SHA, never guessed."""
        self.validate()
        if len(code_revision) != 40 or any(c not in "0123456789abcdef" for c in code_revision):
            raise ValueError("exact code revision SHA required; record dirty file hashes too")
        root = Path(__file__).resolve().parents[1]
        paths = ("data/splits.py", "data/scenarios.py", "data/carbon_source.py", "schemas.py")
        manifest = {
            "version": VERSION,
            "status": "provisional_Q05_Q06_not_frozen",
            "visibility": "private_evaluator_metadata_not_policy_input",
            "code_revision": code_revision,
            "code_file_sha256": {
                p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths
            },
            "runtime": {
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "pydantic": version("pydantic"),
                "selection_rng": "none; SHA256 ranking",
                "job_rng": "D03 Python random.Random (MT19937); runtime pinned above",
            },
            "schema_version": SCHEMA_VERSION,
            "generator_version": scenarios.GENERATOR_VERSION,
            "selection_algorithm": "SHA256 rank with lexical tie break; greedy nonoverlap dates; distinct held months",
            "seed_derivation": "first 16 hex digits of SHA256([version, job_seed, date, scenario])",
            "fold_algorithm": "chronological connected components; three balanced group-count blocks",
            "date_seed": self.date_seed,
            "job_seed": self.job_seed,
            "development_candidates": [d.isoformat() for d in self.development_candidates],
            "held_out_candidates": [d.isoformat() for d in self.held_out_candidates],
            "source": {
                "commit": carbon_source.COMMIT,
                "path": carbon_source.SOURCE_PATH,
                "sha256": carbon_source.SHA256,
                "url": carbon_source.SOURCE_URL,
            },
            "distribution_status": "D03 provisional discrete uniforms; no empirical calibration adopted",
            "distribution_specification": scenarios.generate_jobs.__doc__,
            "records": [r.metadata() for r in self.records],
            "overlaps": overlap_report(self.records),
            "scientific_acceptance": False,
            "held_out_contents_generated": False,
        }
        manifest["manifest_sha256"] = digest(manifest)
        return manifest


def propose_allocation(
    *,
    development_candidates: tuple[date, ...],
    held_out_candidates: tuple[date, ...],
    date_seed: int,
    job_seed: int,
) -> Proposal:
    """Propose 10 dev dates × four scenarios and six held dates × five variants.

    Ten per development scenario, candidate pools, exact seeds, greedy selection and
    fold boundaries are implementation proposals, not approved Q06 distributions.
    Selection sees dates ONLY, never carbon, generated jobs, labels or performance.
    Insufficient greedy selections fail rather than relaxing isolation or retrying seeds.
    """
    _seed(date_seed)
    _seed(job_seed)
    dev_pool = _dates(development_candidates, 1, 14)
    held_pool = _dates(held_out_candidates, 15, 28)
    partitions = _select_windows(dev_pool, held_pool, date_seed)
    records = []
    for partition, windows in partitions:
        for window in windows:
            group = digest([window.source_sha256, window.day.isoformat()])
            for scenario in SCENARIOS:
                # Opaque ID avoids encoding split/scenario/seed in eventual F02 episode IDs.
                identity = digest([VERSION, window.day.isoformat(), scenario])[:24]
                seed = int(digest([VERSION, job_seed, window.day.isoformat(), scenario])[:16], 16)
                base = Allocation(f"EP-{identity}", partition, scenario, seed, window, group)
                records.append(base)
                if partition == "held_out" and scenario == "normal":
                    records.append(
                        replace(
                            base,
                            episode_id="EP-" + digest([VERSION, identity, "withheld"])[:24],
                            withheld=True,
                            parent_id=base.episode_id,
                        )
                    )
    dev = blocked_folds(tuple(r for r in records if r.partition == "development"))
    result = Proposal(
        dev + tuple(r for r in records if r.partition == "held_out"),
        dev_pool,
        held_pool,
        date_seed,
        job_seed,
    )
    result.validate()
    return result


def write_private_manifest(proposal: Proposal, directory: Path, *, code_revision: str) -> Path:
    """Write metadata once into caller-provided evaluator custody, with owner-only mode.

    Directory must already exist outside a Git checkout. POSIX permissions supplement,
    rather than establish, evaluator access control. No contents are materialized here.
    """
    directory = directory.resolve(strict=True)
    if not directory.is_dir() or any(
        (p / ".git").exists() for p in (directory, *directory.parents)
    ):
        raise ValueError("private output must be an existing directory outside Git checkouts")
    manifest = proposal.private_manifest(code_revision=code_revision)
    payload = (json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n").encode(
        "utf-8"
    )
    path = directory / "d04-provisional-private.json"
    import os

    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
    return path
