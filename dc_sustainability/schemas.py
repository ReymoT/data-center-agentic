"""F02 shared, versioned, strict records (contract version 1.0.0).

Owner: Ved. This module defines data contracts only. It contains no simulator, policy,
checker, solver, graph or impact-calculation logic. Where the team has not decided a rule
(Q01-Q05, Q08), a record provides explicit "unresolved" states instead of a default that
would silently become an assumption. See docs/INTERFACES.md for the human-readable contract.

Design rules
- Every scalar is strictly typed: no bool-as-int, no fractional slots, no NaN/inf.
- Unknown fields are rejected (extra="forbid") and records are immutable.
- Structural validity is separate from schedule feasibility. A job with an impossible
  deadline is a valid record; the checker and solver decide feasibility with a snapshot.
- Policy-visible records cannot carry private fixture data: they have no such fields.
- Observations (private, realized) and forecasts (policy-visible) are distinct types with a
  required ``fact_kind`` discriminator and different required fields.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, ClassVar, Literal, Optional, Union

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    Strict,
    StringConstraints,
    model_validator,
)

SCHEMA_VERSION = "1.0.0"
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")

# Contract-level episode shape from the proposal. Episode records carry the counts
# explicitly, so these are documentation constants, not hidden defaults.
PROPOSED_DECISION_SLOTS = 24
PROPOSED_COMPLETION_SLOTS = 6

# Keys that must never appear anywhere in a policy-visible serialization.
PRIVATE_KEYS = frozenset(
    {
        "scenario_id",
        "split",
        "seed",
        "synthetic",
        "intentionally_infeasible",
        "realized_carbon",
        "future_arrivals",
        "oracle",
        "reference_refs",
        "hindsight",
        "private_jobs",
    }
)

ContractError = ValueError  # pydantic.ValidationError subclasses ValueError


class MissingEvidenceError(ContractError):
    """Required evidence (for example the capacity constraint) is absent.

    Absence is never interpreted as "no limit".
    """


# --------------------------------------------------------------------------- scalar types
def _finite(value: float) -> float:
    """Normalize a validated finite number to float, including negative zero."""
    return float(value) + 0.0  # int -> float, -0.0 -> 0.0


Number = Annotated[float, Strict(), Field(allow_inf_nan=False), AfterValidator(_finite)]
NonNegNumber = Annotated[float, Strict(), Field(ge=0, allow_inf_nan=False), AfterValidator(_finite)]
PosNumber = Annotated[float, Strict(), Field(gt=0, allow_inf_nan=False), AfterValidator(_finite)]
Slot = Annotated[int, Strict(), Field(ge=0)]
PosInt = Annotated[int, Strict(), Field(ge=1)]
NonNegInt = Annotated[int, Strict(), Field(ge=0)]
Flag = Annotated[bool, Strict()]
Text = Annotated[str, Strict(), StringConstraints(min_length=1)]

_ID_BODY = r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,59}"
JobId = Annotated[str, Strict(), StringConstraints(pattern=rf"^{_ID_BODY}$")]
GenericId = Annotated[str, Strict(), StringConstraints(pattern=rf"^{_ID_BODY}$")]
FactId = Annotated[str, Strict(), StringConstraints(pattern=rf"^FACT-{_ID_BODY}$")]
ConstraintId = Annotated[str, Strict(), StringConstraints(pattern=rf"^CON-{_ID_BODY}$")]
DecisionId = Annotated[str, Strict(), StringConstraints(pattern=rf"^DEC-{_ID_BODY}$")]
CheckId = Annotated[str, Strict(), StringConstraints(pattern=rf"^CHK-{_ID_BODY}$")]
EvidenceId = Annotated[str, Strict(), StringConstraints(pattern=rf"^(FACT|CON)-{_ID_BODY}$")]
Hex64 = Annotated[str, Strict(), StringConstraints(pattern=r"^[0-9a-f]{64}$")]

_SPLIT_TOKENS = ("heldout", "held", "dev", "train", "test", "split", "seed", "oracle")


def _episode_safe(value: str) -> str:
    """Reject episode IDs containing obvious split, seed, or oracle labels."""
    low = value.lower().replace("_", "").replace("-", "")
    for token in _SPLIT_TOKENS:
        if token in low:
            raise ValueError(f"episode id must be opaque; contains split-like token {token!r}")
    return value


# Policy-visible episode id: "EP-" plus alphanumerics. Guards against obvious label leaks;
# it cannot prove opacity, so fixtures should use neutral ids.
EpisodeId = Annotated[
    str,
    Strict(),
    StringConstraints(pattern=r"^EP-[A-Za-z0-9]{1,32}$"),
    AfterValidator(_episode_safe),
]


def _parse_utc(value: Any) -> datetime:
    """Parse a datetime or ISO timestamp and require an explicit zero UTC offset."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"malformed UTC timestamp {value!r}") from exc
    else:
        raise ValueError("timestamp must be an ISO-8601 string or datetime")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be timezone-aware with a zero UTC offset")
    return parsed.astimezone(timezone.utc)


UtcTime = Annotated[
    datetime,
    BeforeValidator(_parse_utc),
    PlainSerializer(
        lambda d: d.isoformat().replace("+00:00", "Z"), return_type=str, when_used="json"
    ),
]

# Physical/dimensional units. Pollutant/model semantics live in separate fields.
Unit = Literal["kW", "kWh", "slot", "h", "g/kWh", "kg"]

SystemId = Literal[
    "agent", "plain_llm", "greedy_a", "greedy_b", "decision_tree_c", "random_forest_d"
]
Split = Literal["development", "held_out"]
ConstraintType = Literal["capacity", "arrival", "deadline", "nonflexible", "freshness"]
_CONSTRAINT_UNITS = {
    "capacity": "kW",
    "arrival": "slot",
    "deadline": "slot",
    "nonflexible": "slot",
    "freshness": "slot",
}


# --------------------------------------------------------------------------- base classes
def _check_version(value: str) -> str:
    # fullmatch rejects trailing newlines and any other data beyond MAJOR.MINOR.PATCH.
    """Require a semantic version in the supported major and no newer than this schema."""
    match = _VERSION_RE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid schema_version {value!r}; expected MAJOR.MINOR.PATCH")
    got = tuple(int(g) for g in match.groups())
    cur = tuple(int(g) for g in SCHEMA_VERSION.split("."))
    if got[0] != cur[0]:
        raise ValueError(f"unsupported schema major version {got[0]}; supported {cur[0]}")
    if got[1:] > cur[1:]:
        raise ValueError(f"schema_version {value} is newer than supported {SCHEMA_VERSION}")
    return value


SchemaVersion = Annotated[str, Strict(), AfterValidator(_check_version)]


def _get(obj: Any, dotted: str) -> Any:
    """Look up a nested mapping value using a dot-separated key path."""
    for part in dotted.split("."):
        obj = obj[part]
    return obj


# Collections whose semantic meaning is a set rather than an ordered sequence. This is
# deliberately explicit: timeline records such as EpisodeResult.slots remain ordered.
# Sorting is recursive so nested records (for example Constraint.applies_to_jobs) receive
# the same treatment as top-level collections.
_UNORDERED_SORT_KEYS: dict[str, Optional[str]] = {
    "applies_to_jobs": None,
    "constraints": "constraint_id",
    "sources": "source_id",
    "waiting_jobs": "job_id",
    "running_jobs": "job.job_id",
    "completed_jobs": "job_id",
    "missed_job_ids": None,
    "carbon_facts": "fact_id",
    "missing_carbon_slots": None,
    "constraint_ids": None,
    "evidence_ids": None,
    "ids": None,
    "job_ids": None,
    "starts": "job_id",
    "schedule": "job_id",
    "started_job_ids": None,
    "running_job_ids": None,
    "completed_job_ids": None,
    "deferrals": "job_id",
    "abstentions": None,
    "executed_starts": "job_id",
    "not_applicable_stages": None,
    "deadline_missed_job_ids": None,
    "unfinished_job_ids": None,
    "jobs": "job.job_id",
    "realized_carbon": "fact_id",
    "reference_refs": None,
    "performed": "name",
    "skipped": "name",
    "evidence": "kind",
    "violations": None,
    "claims": "claim_id",
}


def _canonicalize_unordered(
    value: Any, 
    *, 
    field_name: Optional[str] = None,
    root_sort_keys: Optional[dict[str, str]] = None,
) -> Any:
    """Recursively sort only collections whose order is semantically irrelevant."""
    if isinstance(value, dict):
        normalized = {
            key: _canonicalize_unordered(item, field_name=key) for key, item in value.items()
        }
        # Sort each unordered list at the point where its parent field is known.
        for key, item in tuple(normalized.items()):
            if not isinstance(item, list):
                continue
            dotted = (root_sort_keys or {}).get(key) if field_name is None else None
            if dotted is None:
                dotted = _UNORDERED_SORT_KEYS.get(key, "__ordered__")
            if dotted == "__ordered__":
                continue
            if dotted:
                normalized[key] = sorted(item, key=lambda entry, path=dotted: _get(entry, path))
            elif all(isinstance(entry, (str, int, float, bool)) or entry is None for entry in item):
                normalized[key] = sorted(
                    item,
                    key=lambda entry: (entry is None, type(entry).__name__, entry),
                )
            else:
                normalized[key] = sorted(item, key=canonical_json)
        return normalized
    if isinstance(value, list):
        return [_canonicalize_unordered(item) for item in value]
    return value


def canonical_json(data: Any) -> str:
    """Serialize data as compact, sorted UTF-8-friendly JSON, rejecting nonfinite numbers."""
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def sha256_hex(data: Any) -> str:
    """Return the SHA-256 hex digest of the canonical JSON encoding of data."""
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


class Record(BaseModel):
    """Strict immutable record without a version envelope (nested use)."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    # field name -> dotted key used to sort that collection in canonical form ("" = itself)
    _SORT_KEYS: ClassVar[dict[str, str]] = {}
    _HASH_EXCLUDE: ClassVar[frozenset] = frozenset()

    def to_jsonable(self) -> dict:
        """Return JSON-compatible field values without excluding or reordering collections."""
        return self.model_dump(mode="json")

    def canonical_dict(self) -> dict:
        """Normalize unordered collections and omit fields excluded from content identity."""
        data = self.to_jsonable()
        for name in self._HASH_EXCLUDE:
            data.pop(name, None)
        return _canonicalize_unordered(data, root_sort_keys=self._SORT_KEYS)

    def canonical_hash(self) -> str:
        """Hash the normalized record content with SHA-256."""
        return sha256_hex(self.canonical_dict())

    def to_json(self) -> str:
        """Serialize all record fields as compact JSON with sorted object keys."""
        return canonical_json(self.to_jsonable())

    @classmethod
    def from_json(cls, text: str):
        """Construct this record from JSON text using strict field validation."""
        return cls.model_validate_json(text)

    @classmethod
    def from_jsonable(cls, data: dict):
        """Validate decoded JSON with the same strictness as JSON text (no bool/float slots)."""
        try:
            text = json.dumps(data, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ContractError(f"not strict-JSON serializable: {exc}") from exc
        return cls.model_validate_json(text)


class Versioned(Record):
    """Top-level exchanged record carrying ``record_type`` and ``schema_version``.

    Direct Python construction may use the current schema default. External deserialization
    requires both envelope fields so an unversioned payload cannot silently masquerade as a
    compatible record.
    """

    schema_version: SchemaVersion = SCHEMA_VERSION

    @classmethod
    def _require_envelope(cls, data: Any) -> None:
        """Require an object with this record type and an explicit schema version."""
        if not isinstance(data, dict):
            raise ContractError("versioned record JSON must be an object")
        expected_type = cls.model_fields["record_type"].default
        if "record_type" not in data:
            raise ContractError("missing required record_type envelope field")
        if data["record_type"] != expected_type:
            raise ContractError(
                f"record_type {data['record_type']!r} does not match {expected_type!r}"
            )
        if "schema_version" not in data:
            raise ContractError("missing required schema_version envelope field")

    @classmethod
    def from_json(cls, text: str):
        """Validate JSON text after requiring its explicit version and type envelope."""
        try:
            data = json.loads(text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ContractError(f"invalid JSON record: {exc}") from exc
        cls._require_envelope(data)
        return cls.model_validate_json(text)

    @classmethod
    def from_jsonable(cls, data: dict):
        """Validate decoded JSON with an explicit envelope and strict scalar types."""
        cls._require_envelope(data)
        try:
            text = json.dumps(data, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ContractError(f"not strict-JSON serializable: {exc}") from exc
        return cls.model_validate_json(text)


def assert_no_private_keys(data: Any, *, path: str = "$") -> None:
    """Defense in depth: reject private-fixture keys anywhere in a policy-visible payload."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in PRIVATE_KEYS:
                raise ContractError(f"private key {key!r} found at {path}")
            assert_no_private_keys(value, path=f"{path}.{key}")
    elif isinstance(data, (list, tuple)):
        for index, value in enumerate(data):
            assert_no_private_keys(value, path=f"{path}[{index}]")


def _unique(values, what: str) -> None:
    """Raise ValueError listing duplicate values in a named collection."""
    seen, dups = set(), set()
    for v in values:
        (dups if v in seen else seen).add(v)
    if dups:
        raise ValueError(f"duplicate {what}: {sorted(dups)}")


# --------------------------------------------------------------------------- source / site
class SourceRef(Versioned):
    """Provenance of a fact or constraint (maps to sched:SourceFile / PROV-O)."""

    record_type: Literal["SourceRef"] = "SourceRef"
    source_id: GenericId
    path: Text
    commit: Optional[Text] = None
    sha256: Optional[Hex64] = None
    # Q05: redistribution status is stated explicitly; "unresolved" is a legal honest value.
    redistribution_status: Literal["unresolved", "permitted", "restricted"]


class SiteConfig(Versioned):
    """Site constants. Capacity is a Constraint (single authoritative copy), not a site field."""

    record_type: Literal["SiteConfig"] = "SiteConfig"
    site_id: GenericId
    background_kw: NonNegNumber
    pue: Annotated[float, Strict(), Field(ge=1.0, allow_inf_nan=False), AfterValidator(_finite)]
    slot_hours: PosNumber


class Constraint(Versioned):
    record_type: Literal["Constraint"] = "Constraint"
    constraint_id: ConstraintId
    constraint_type: ConstraintType
    limit_value: Number
    unit: Unit
    applies_to_site: Optional[GenericId] = None
    applies_to_jobs: tuple[JobId, ...] = ()
    source_id: GenericId
    source_version: Optional[Text] = None

    @model_validator(mode="after")
    def _check(self):
        """Validate units, exclusive site/job applicability, limit ranges, and unique job IDs."""
        if self.unit != _CONSTRAINT_UNITS[self.constraint_type]:
            raise ValueError(
                f"{self.constraint_type} constraint requires unit "
                f"{_CONSTRAINT_UNITS[self.constraint_type]!r}, got {self.unit!r}"
            )
        has_site, has_jobs = self.applies_to_site is not None, bool(self.applies_to_jobs)
        if has_site == has_jobs:
            raise ValueError(
                "constraint must apply to exactly one of a site or a non-empty job list"
            )
        if self.constraint_type == "capacity" and not has_site:
            raise ValueError("capacity constraint must apply to a site")
        if self.constraint_type in ("arrival", "deadline", "nonflexible") and not has_jobs:
            raise ValueError(f"{self.constraint_type} constraint must apply to jobs")
        if self.constraint_type == "capacity" and self.limit_value <= 0:
            raise ValueError("capacity limit must be positive")
        if self.constraint_type in ("arrival", "deadline", "nonflexible", "freshness"):
            if self.limit_value < 0 or self.limit_value != int(self.limit_value):
                raise ValueError("slot-valued constraint limit must be a non-negative integer")
        _unique(self.applies_to_jobs, "applies_to_jobs")
        return self


class ConstraintSnapshot(Versioned):
    """The one authoritative constraint set shared by graph, policies, solver and checker.

    A snapshot may lack a capacity constraint (that is how missing evidence is represented);
    ``capacity_kw`` then raises ``MissingEvidenceError`` rather than assuming no limit.
    """

    record_type: Literal["ConstraintSnapshot"] = "ConstraintSnapshot"
    snapshot_id: GenericId
    site: SiteConfig
    constraints: tuple[Constraint, ...]
    sources: tuple[SourceRef, ...] = ()
    _SORT_KEYS: ClassVar[dict[str, str]] = {"constraints": "constraint_id", "sources": "source_id"}

    @model_validator(mode="after")
    def _check(self):
        """Validate unique IDs, source/site references, and at most one capacity constraint."""
        _unique([c.constraint_id for c in self.constraints], "constraint ids")
        _unique([s.source_id for s in self.sources], "source ids")
        capacity_constraints = [c for c in self.constraints if c.constraint_type == "capacity"]
        if len(capacity_constraints) > 1:
            raise ValueError("constraint snapshot must contain at most one capacity constraint")
        known = {s.source_id for s in self.sources}
        missing = {c.source_id for c in self.constraints} - known
        if missing:
            raise ValueError(f"constraints reference unknown sources: {sorted(missing)}")
        for c in self.constraints:
            if c.applies_to_site is not None and c.applies_to_site != self.site.site_id:
                raise ValueError(f"{c.constraint_id} applies to unknown site {c.applies_to_site!r}")
        return self

    def constraints_of(self, constraint_type: str) -> tuple[Constraint, ...]:
        """Return snapshot constraints matching the requested type in their stored order."""
        return tuple(c for c in self.constraints if c.constraint_type == constraint_type)

    @property
    def capacity_kw(self) -> float:
        """Return the single capacity limit in kW, raising if capacity evidence is absent."""
        caps = self.constraints_of("capacity")
        if not caps:
            raise MissingEvidenceError(
                "no capacity constraint in snapshot; capacity is not unlimited"
            )
        if len(caps) > 1:
            raise ContractError("multiple capacity constraints in snapshot")
        return caps[0].limit_value


# --------------------------------------------------------------------------- jobs
class Job(Versioned):
    """Policy-visible job. Scenario/split/seed live only in ``PrivateJob``.

    Only per-field structure is validated. Arrival, duration and deadline relations
    (feasibility) are deliberately not enforced so impossible jobs stay representable.
    """

    record_type: Literal["Job"] = "Job"
    job_id: JobId
    arrival_slot: Slot
    duration_slots: PosInt
    power_kw: PosNumber
    deadline_slot: Slot
    flexible: Flag

    @property
    def slack_slots(self) -> int:
        """deadline - arrival - duration; may be negative. Arithmetic, not a feasibility verdict."""
        return self.deadline_slot - self.arrival_slot - self.duration_slots


class RunningJobView(Record):
    job: Job
    start_slot: Slot

    @property
    def end_slot(self) -> int:
        """Exclusive occupancy boundary: the job occupies [start_slot, end_slot)."""
        return self.start_slot + self.job.duration_slots


class CompletedJobView(Record):
    job_id: JobId
    start_slot: Slot
    end_slot: Slot


# --------------------------------------------------------------------------- carbon
class CarbonSemantics(Record):
    """Unresolved source semantics (Q05) stated explicitly rather than assumed.

    ``unit`` of the value is always g/kWh (dimension); pollutant and interval meaning are
    separate and may be "unresolved". An "agreed" slot mapping requires a resolved interval
    convention, so the schema cannot certify a mapping the team has not verified.
    """

    pollutant_basis: Literal["co2", "co2e", "unresolved"]
    interval_convention: Literal["hour_start", "hour_end", "unresolved"]
    emissions_factor_type: Literal["average", "marginal", "unresolved"]
    slot_mapping_status: Literal["unresolved", "provisional", "agreed"]

    @model_validator(mode="after")
    def _check(self):
        """Reject an agreed slot mapping when its interval convention is still unresolved."""
        if self.slot_mapping_status == "agreed" and self.interval_convention == "unresolved":
            raise ValueError(
                "slot mapping cannot be 'agreed' while interval convention is unresolved"
            )
        return self


QualityStatus = Literal["validated", "unvalidated", "suspect"]


def _interval_ok(start: Optional[datetime], end: Optional[datetime]) -> None:
    """Require both optional interval endpoints together and a strictly increasing interval."""
    if (start is None) != (end is None):
        raise ValueError("valid_from_utc and valid_to_utc must be given together")
    if start is not None and end <= start:
        raise ValueError("valid interval must have valid_to_utc after valid_from_utc")


class CarbonObservation(Versioned):
    """PRIVATE realized source value. Never part of a VisibleState or Context."""

    record_type: Literal["CarbonObservation"] = "CarbonObservation"
    fact_kind: Literal["observation"] = "observation"
    fact_id: FactId
    value: NonNegNumber
    unit: Literal["g/kWh"]
    source_id: GenericId
    source_sha256: Optional[Hex64] = None
    observed_at_utc: UtcTime  # raw source timestamp label; meaning depends on semantics
    valid_slot: Optional[Slot] = None
    valid_from_utc: Optional[UtcTime] = None
    valid_to_utc: Optional[UtcTime] = None
    semantics: CarbonSemantics
    quality_status: QualityStatus

    @model_validator(mode="after")
    def _check(self):
        """Validate interval endpoints and require stated semantics for interval or slot mapping."""
        _interval_ok(self.valid_from_utc, self.valid_to_utc)
        if self.valid_from_utc is not None and self.semantics.interval_convention == "unresolved":
            raise ValueError("a valid UTC interval requires a resolved interval convention")
        if self.valid_slot is not None and self.semantics.slot_mapping_status == "unresolved":
            raise ValueError("valid_slot requires a provisional or agreed slot mapping")
        return self


class CarbonForecast(Versioned):
    """Policy-visible carbon value with a simulated issue time.

    The issue time is simulated metadata (Q04 decides how it is generated) and is a
    required, separate field: an observation timestamp is never used as an issue time.
    Staleness is NOT computed here; it needs the freshness constraint and the Q04 rule.
    """

    record_type: Literal["CarbonForecast"] = "CarbonForecast"
    fact_kind: Literal["forecast"] = "forecast"
    fact_id: FactId
    value: NonNegNumber
    unit: Literal["g/kWh"]
    source_id: GenericId
    source_sha256: Optional[Hex64] = None
    valid_slot: Slot
    valid_from_utc: Optional[UtcTime] = None
    valid_to_utc: Optional[UtcTime] = None
    issued_at_utc: UtcTime
    forecast_kind: Literal["perfect_foresight", "persistence", "unresolved"]
    semantics: CarbonSemantics
    quality_status: QualityStatus

    @model_validator(mode="after")
    def _check(self):
        """Validate the optional interval and require a provisional or agreed slot mapping."""
        _interval_ok(self.valid_from_utc, self.valid_to_utc)
        if self.valid_from_utc is not None and self.semantics.interval_convention == "unresolved":
            raise ValueError("a valid UTC interval requires a resolved interval convention")
        if self.semantics.slot_mapping_status == "unresolved":
            raise ValueError("a visible forecast needs a provisional or agreed slot mapping")
        return self


CarbonFact = Annotated[Union[CarbonObservation, CarbonForecast], Field(discriminator="fact_kind")]


# --------------------------------------------------------------------------- visible state
class VisibleState(Versioned):
    """Everything a policy may see at one decision. No private fixture fields exist here."""

    record_type: Literal["VisibleState"] = "VisibleState"
    episode_id: EpisodeId
    current_slot: Slot
    state_version: NonNegInt
    site: SiteConfig
    waiting_jobs: tuple[Job, ...] = ()
    running_jobs: tuple[RunningJobView, ...] = ()
    completed_jobs: tuple[CompletedJobView, ...] = ()
    missed_job_ids: tuple[JobId, ...] = ()
    carbon_facts: tuple[CarbonForecast, ...] = ()
    # Explicit coverage gaps (withheld forecasts); Q04 decides fallback behaviour.
    missing_carbon_slots: tuple[Slot, ...] = ()
    constraint_snapshot_id: GenericId
    constraint_ids: tuple[ConstraintId, ...]

    _SORT_KEYS: ClassVar[dict[str, str]] = {
        "waiting_jobs": "job_id",
        "running_jobs": "job.job_id",
        "completed_jobs": "job_id",
        "missed_job_ids": "",
        "carbon_facts": "fact_id",
        "missing_carbon_slots": "",
        "constraint_ids": "",
    }

    @model_validator(mode="after")
    def _check(self):
        """Validate unique IDs, job timing, and forecast availability within the visible horizon."""
        ids = (
            [j.job_id for j in self.waiting_jobs]
            + [r.job.job_id for r in self.running_jobs]
            + [c.job_id for c in self.completed_jobs]
        )
        _unique(ids, "job ids across waiting/running/completed")
        _unique(self.missed_job_ids, "missed job ids")
        _unique([f.fact_id for f in self.carbon_facts], "carbon fact ids")
        _unique([f.valid_slot for f in self.carbon_facts], "forecast valid slots")
        _unique(self.constraint_ids, "constraint ids")
        _unique(self.missing_carbon_slots, "missing carbon slots")
        late = [j.job_id for j in self.waiting_jobs if j.arrival_slot > self.current_slot]
        if late:
            raise ValueError(f"waiting jobs have not arrived by slot {self.current_slot}: {late}")
        early = [r.job.job_id for r in self.running_jobs if r.start_slot > self.current_slot]
        if early:
            raise ValueError(f"running jobs start after the current slot: {early}")
        inactive = [r.job.job_id for r in self.running_jobs if r.end_slot <= self.current_slot]
        if inactive:
            raise ValueError(
                f"running jobs must still occupy the current slot (half-open intervals): {inactive}"
            )
        invalid_completed = [
            view.job_id
            for view in self.completed_jobs
            if view.end_slot <= view.start_slot or view.end_slot > self.current_slot
        ]
        if invalid_completed:
            raise ValueError(
                "completed jobs must have a positive interval ending no later than the current "
                f"slot: {invalid_completed}"
            )
        overlap = {f.valid_slot for f in self.carbon_facts} & set(self.missing_carbon_slots)
        if overlap:
            raise ValueError(f"slots both present and listed missing: {sorted(overlap)}")

        # A policy sees only current/future forecasts within its up-to-24-slot episode
        # horizon. The fixed proposal episode ends after slots 0..29.
        visible_end = min(
            self.current_slot + PROPOSED_DECISION_SLOTS,
            PROPOSED_DECISION_SLOTS + PROPOSED_COMPLETION_SLOTS,
        )
        forecast_slots = [f.valid_slot for f in self.carbon_facts]
        out_of_window = [
            slot for slot in forecast_slots if not self.current_slot <= slot < visible_end
        ]
        if out_of_window:
            raise ValueError(
                "carbon forecasts must be current/future slots within the visible episode horizon: "
                f"{sorted(out_of_window)}"
            )
        bad_missing = [
            slot 
            for slot in self.missing_carbon_slots 
            if not self.current_slot <= slot < visible_end
        ]
        if bad_missing:
            raise ValueError(
                "missing carbon slots must be current/future slots within the visible episode horizon: "
                f"{sorted(bad_missing)}"
            )
        return self

    @classmethod
    def from_snapshot(cls, snapshot: ConstraintSnapshot, **fields: Any) -> "VisibleState":
        """Construct a policy-visible state with constraint IDs projected from a full snapshot.

        Pass state fields such as episode_id, current_slot, state_version, waiting_jobs and
        carbon_facts. Site, snapshot ID and constraint IDs are derived here so producers do not
        accidentally serialize future-job constraint IDs into a policy-visible state.
        """
        reserved = {"site", "constraint_snapshot_id", "constraint_ids"}.intersection(fields)
        if reserved:
            raise ContractError(
                "from_snapshot derives site, constraint_snapshot_id and constraint_ids; "
                f"do not supply {sorted(reserved)}"
            )
        provisional = cls(
            **fields,
            site=snapshot.site,
            constraint_snapshot_id=snapshot.snapshot_id,
            constraint_ids=(),
        )
        projected_ids = tuple(
            constraint.constraint_id 
            for constraint in visible_constraints_for(provisional, snapshot)
        )
        return cls(**{**provisional.model_dump(), "constraint_ids": projected_ids})

    def running_job_load_kw(self, slot: int) -> float:
        """Job power of already-running work in a slot (background and PUE excluded)."""
        return sum(r.job.power_kw for r in self.running_jobs if r.start_slot <= slot < r.end_slot)


# --------------------------------------------------------------------------- context
def visible_constraints_for(
    state: VisibleState, snapshot: ConstraintSnapshot
) -> tuple[Constraint, ...]:
    """Return only constraints that do not reveal not-yet-visible jobs.

    Site-wide constraints are always visible. A job-specific constraint is visible only when
    every job named by it is already present in the state (waiting, running, completed, or
    explicitly missed). This conservative rule avoids leaking a future job through either its
    constraint ID or an ``applies_to_jobs`` list. The complete snapshot remains authoritative
    for the simulator and checker; this is only the policy-facing projection.
    """
    if state.site.site_id != snapshot.site.site_id:
        raise ContractError("state site differs from constraint snapshot site")
    visible_job_ids = {j.job_id for j in state.waiting_jobs}
    visible_job_ids |= {r.job.job_id for r in state.running_jobs}
    visible_job_ids |= {j.job_id for j in state.completed_jobs}
    visible_job_ids |= set(state.missed_job_ids)
    visible = []
    for constraint in snapshot.constraints:
        if constraint.applies_to_site == state.site.site_id:
            visible.append(constraint)
        elif constraint.applies_to_jobs and set(constraint.applies_to_jobs) <= visible_job_ids:
            visible.append(constraint)
    return tuple(sorted(visible, key=lambda item: item.constraint_id))


def evidence_ids_for(state: VisibleState, snapshot: ConstraintSnapshot) -> tuple[str, ...]:
    """Stable evidence IDs for policy-visible records, never hidden future jobs."""
    ids = {"FACT-SITE-BG", "FACT-SITE-PUE", "FACT-SITE-SLOTH"}
    ids |= {f"FACT-JOB-{j.job_id}" for j in state.waiting_jobs}
    ids |= {f"FACT-JOB-{r.job.job_id}" for r in state.running_jobs}
    ids |= {f"FACT-JOB-{j.job_id}" for j in state.completed_jobs}
    ids |= {f"FACT-JOB-{job_id}" for job_id in state.missed_job_ids}
    ids |= {f.fact_id for f in state.carbon_facts}
    ids |= {c.constraint_id for c in visible_constraints_for(state, snapshot)}
    return tuple(sorted(ids))


class ContextContent(Record):
    """The information payload whose hash proves graph/flat equivalence."""

    episode_id: EpisodeId
    current_slot: Slot
    state_version: NonNegInt
    snapshot_id: GenericId
    site: SiteConfig
    waiting_jobs: tuple[Job, ...]
    running_jobs: tuple[RunningJobView, ...]
    completed_jobs: tuple[CompletedJobView, ...]
    missed_job_ids: tuple[JobId, ...]
    carbon_facts: tuple[CarbonForecast, ...]
    missing_carbon_slots: tuple[Slot, ...]
    constraints: tuple[Constraint, ...]
    sources: tuple[SourceRef, ...] = ()
    evidence_ids: tuple[EvidenceId, ...]

    _SORT_KEYS: ClassVar[dict[str, str]] = {
        "waiting_jobs": "job_id",
        "running_jobs": "job.job_id",
        "completed_jobs": "job_id",
        "missed_job_ids": "",
        "carbon_facts": "fact_id",
        "missing_carbon_slots": "",
        "constraints": "constraint_id",
        "sources": "source_id",
        "evidence_ids": "",
    }

    @model_validator(mode="after")
    def _check_unique(self):
        """Reject duplicate job, forecast, constraint, source, and evidence identifiers."""
        job_ids = (
            [job.job_id for job in self.waiting_jobs]
            + [running.job.job_id for running in self.running_jobs]
            + [job.job_id for job in self.completed_jobs]
        )
        _unique(job_ids, "context job ids")
        _unique(self.missed_job_ids, "context missed job ids")
        _unique([fact.fact_id for fact in self.carbon_facts], "context carbon fact ids")
        _unique([fact.valid_slot for fact in self.carbon_facts], "context forecast slots")
        _unique(self.missing_carbon_slots, "context missing carbon slots")
        _unique(
            [constraint.constraint_id for constraint in self.constraints],
            "context constraint ids",
        )
        _unique([source.source_id for source in self.sources], "context source ids")
        _unique(self.evidence_ids, "context evidence IDs")
        return self


def _validate_job_constraint_consistency(
    state: VisibleState, constraints: tuple[Constraint, ...]
) -> None:
    """Reject contradictory duplicated job facts before they become policy context.

    Job fields carry the job's structural facts. Constraint records are authoritative limits
    used by checks. When both representations are supplied, they must agree; absence of a
    redundant constraint is allowed and is not interpreted as a different value.
    """
    visible_jobs = {job.job_id: job for job in state.waiting_jobs}
    visible_jobs.update({view.job.job_id: view.job for view in state.running_jobs})
    for constraint in constraints:
        for job_id in constraint.applies_to_jobs:
            job = visible_jobs.get(job_id)
            if job is None:
                # Completed/missed records do not retain all Job fields, so consistency cannot
                # be checked from those reduced views alone.
                continue
            if (
                constraint.constraint_type == "arrival"
                and constraint.limit_value != job.arrival_slot
            ):
                raise ContractError(
                    f"{constraint.constraint_id} arrival limit conflicts with Job {job_id}"
                )
            if (
                constraint.constraint_type == "deadline"
                and constraint.limit_value != job.deadline_slot
            ):
                raise ContractError(
                    f"{constraint.constraint_id} deadline limit conflicts with Job {job_id}"
                )
            if constraint.constraint_type == "nonflexible":
                if job.flexible:
                    raise ContractError(
                        f"{constraint.constraint_id} marks flexible Job {job_id} nonflexible"
                    )
                if constraint.limit_value != job.arrival_slot:
                    raise ContractError(
                        f"{constraint.constraint_id} nonflexible start slot conflicts with "
                        f"Job {job_id} arrival"
                    )


class Context(Versioned):
    """Evidence supplied to a policy; ``representation`` may differ, ``content`` may not."""

    record_type: Literal["Context"] = "Context"
    representation: Literal["graph", "flat"]
    content: ContextContent
    content_hash: Hex64
    presentation_sha256: Optional[Hex64] = None  # hash of any rendered text, for traceability

    @model_validator(mode="after")
    def _check(self):
        """Validate the content hash, visibility, provenance, evidence IDs, and job consistency."""
        if self.content_hash != self.content.canonical_hash():
            raise ValueError("content_hash does not match canonical content")
        assert_no_private_keys(self.content.to_jsonable())
        visible_job_ids = {job.job_id for job in self.content.waiting_jobs}
        visible_job_ids |= {running.job.job_id for running in self.content.running_jobs}
        visible_job_ids |= {job.job_id for job in self.content.completed_jobs}
        visible_job_ids |= set(self.content.missed_job_ids)
        for constraint in self.content.constraints:
            if (
                constraint.applies_to_site is not None
                and constraint.applies_to_site != self.content.site.site_id
            ):
                raise ValueError("context contains a site constraint for a different site")
            if (
                constraint.applies_to_jobs
                and not set(constraint.applies_to_jobs) <= visible_job_ids
            ):
                raise ValueError("context contains a constraint for a not-yet-visible job")
        source_ids = {source.source_id for source in self.content.sources}
        required_source_ids = {c.source_id for c in self.content.constraints}
        required_source_ids |= {f.source_id for f in self.content.carbon_facts}
        missing_sources = required_source_ids - source_ids
        if missing_sources:
            raise ValueError("context is missing source provenance records: " f"{sorted(missing_sources)}")
        unrelated_sources = source_ids - required_source_ids
        if unrelated_sources:
            raise ValueError("context includes unrelated source records: " f"{sorted(unrelated_sources)}")
        expected_evidence_ids = {"FACT-SITE-BG", "FACT-SITE-PUE", "FACT-SITE-SLOTH"}
        expected_evidence_ids |= {f"FACT-JOB-{j.job_id}" for j in self.content.waiting_jobs}
        expected_evidence_ids |= {
            f"FACT-JOB-{running.job.job_id}" for running in self.content.running_jobs
        }
        expected_evidence_ids |= {f"FACT-JOB-{job.job_id}" for job in self.content.completed_jobs}
        expected_evidence_ids |= {f"FACT-JOB-{job_id}" for job_id in self.content.missed_job_ids}
        expected_evidence_ids |= {fact.fact_id for fact in self.content.carbon_facts}
        expected_evidence_ids |= {constraint.constraint_id for constraint in self.content.constraints}
        if set(self.content.evidence_ids) != expected_evidence_ids:
            raise ValueError("context evidence IDs do not match visible records")
        # Context may arrive from JSON rather than Context.build. Re-run cross-record checks
        # after deserialization so tampered job/constraint duplicates cannot slip through.
        projected_state = VisibleState(
            episode_id=self.content.episode_id,
            current_slot=self.content.current_slot,
            state_version=self.content.state_version,
            site=self.content.site,
            waiting_jobs=self.content.waiting_jobs,
            running_jobs=self.content.running_jobs,
            completed_jobs=self.content.completed_jobs,
            missed_job_ids=self.content.missed_job_ids,
            carbon_facts=self.content.carbon_facts,
            missing_carbon_slots=self.content.missing_carbon_slots,
            constraint_snapshot_id=self.content.snapshot_id,
            constraint_ids=tuple(c.constraint_id for c in self.content.constraints),
        )
        _validate_job_constraint_consistency(projected_state, self.content.constraints)
        return self

    @classmethod
    def build(
        cls,
        state: VisibleState,
        snapshot: ConstraintSnapshot,
        representation: Literal["graph", "flat"],
        presentation_sha256: Optional[str] = None,
    ) -> "Context":
        """Build hashed policy context from matching inputs with visible evidence only."""
        if state.constraint_snapshot_id != snapshot.snapshot_id:
            raise ContractError("state and constraint snapshot ids differ")
        if state.site != snapshot.site:
            raise ContractError("state site differs from snapshot site")
        visible_constraints = visible_constraints_for(state, snapshot)
        expected_constraint_ids = {c.constraint_id for c in visible_constraints}
        if set(state.constraint_ids) != expected_constraint_ids:
            raise ContractError("state constraint ids do not match policy-visible constraints")
        _validate_job_constraint_consistency(state, visible_constraints)
        visible_source_ids = {c.source_id for c in visible_constraints}
        visible_source_ids |= {f.source_id for f in state.carbon_facts}
        available_source_ids = {source.source_id for source in snapshot.sources}
        missing_sources = visible_source_ids - available_source_ids
        if missing_sources:
            raise ContractError(
                "visible facts/constraints reference missing source records: "
                f"{sorted(missing_sources)}"
            )
        visible_sources = tuple(
            sorted(
                (source for source in snapshot.sources if source.source_id in visible_source_ids),
                key=lambda source: source.source_id,
            )
        )
        content = ContextContent(
            episode_id=state.episode_id,
            current_slot=state.current_slot,
            state_version=state.state_version,
            snapshot_id=snapshot.snapshot_id,
            site=state.site,
            waiting_jobs=state.waiting_jobs,
            running_jobs=state.running_jobs,
            completed_jobs=state.completed_jobs,
            missed_job_ids=state.missed_job_ids,
            carbon_facts=state.carbon_facts,
            missing_carbon_slots=state.missing_carbon_slots,
            constraints=visible_constraints,
            sources=visible_sources,
            evidence_ids=evidence_ids_for(state, snapshot),
        )
        return cls(
            representation=representation,
            content=content,
            content_hash=content.canonical_hash(),
            presentation_sha256=presentation_sha256,
        )


# --------------------------------------------------------------------------- plan
class PlannedStart(Record):
    job_id: JobId
    start_slot: Slot


DeferralReason = Literal["waiting_for_lower_carbon", "capacity", "missing_evidence", "other"]
AbstentionReason = Literal[
    "infeasible_deadline", "constraint_violation", "missing_evidence", "stale_evidence", "other"
]


class Deferral(Record):
    job_id: JobId
    reason: DeferralReason
    detail: Optional[Text] = None
    evidence_ids: tuple[EvidenceId, ...] = ()


class Abstention(Record):
    """``job_id`` None abstains for the whole decision (Q02 per-job vs whole is open)."""

    job_id: Optional[JobId] = None
    reason: AbstentionReason
    detail: Optional[Text] = None
    evidence_ids: tuple[EvidenceId, ...] = ()
    constraint_ids: tuple[ConstraintId, ...] = ()


PlanStatus = Literal["proposed", "approved", "executed", "rejected"]


class Plan(Versioned):
    """A proposal. Starts may be future intentions; only current-slot starts are executable.

    Coverage (must every visible job appear?) and omission semantics are Q02/Q03 and are
    intentionally not enforced. Backdated or unknown-job starts are structurally valid so the
    checker can report them as violations.
    """

    record_type: Literal["Plan"] = "Plan"
    episode_id: EpisodeId
    slot: Slot  # decision slot at which the plan was proposed
    state_version: NonNegInt
    starts: tuple[PlannedStart, ...] = ()
    deferrals: tuple[Deferral, ...] = ()
    abstentions: tuple[Abstention, ...] = ()
    evidence_ids: tuple[EvidenceId, ...] = ()
    status: PlanStatus

    _HASH_EXCLUDE: ClassVar[frozenset] = frozenset({"status"})
    _SORT_KEYS: ClassVar[dict[str, str]] = {
        "starts": "job_id",
        "deferrals": "job_id",
        "evidence_ids": "",
    }

    @model_validator(mode="after")
    def _check(self):
        """Reject duplicate starts/deferrals and jobs both started and deferred or abstained."""
        _unique([s.job_id for s in self.starts], "started job ids")
        _unique([d.job_id for d in self.deferrals], "deferred job ids")
        started = {s.job_id for s in self.starts}
        contradictory = started & (
            {d.job_id for d in self.deferrals}
            | {a.job_id for a in self.abstentions if a.job_id is not None}
        )
        if contradictory:
            raise ValueError(f"jobs both started and deferred/abstained: {sorted(contradictory)}")
        return self

    @property
    def plan_hash(self) -> str:
        """Identity of the proposal content; excludes ``status`` so approval keeps the hash."""
        return self.canonical_hash()

    @property
    def current_starts(self) -> tuple[PlannedStart, ...]:
        """Executable-now candidates; later starts are intentions, not commitments."""
        return tuple(s for s in self.starts if s.start_slot == self.slot)

    @property
    def future_intentions(self) -> tuple[PlannedStart, ...]:
        """Starts strictly after this decision slot; backdated starts remain violations."""
        return tuple(s for s in self.starts if s.start_slot > self.slot)


class ApprovedStart(Record):
    job_id: JobId
    start_slot: Slot


class ApprovedActions(Versioned):
    """Strict input to ``step``: current-slot starts only, bound to a checked plan."""

    record_type: Literal["ApprovedActions"] = "ApprovedActions"
    episode_id: EpisodeId
    slot: Slot
    state_version: NonNegInt
    plan_hash: Hex64
    check_id: CheckId
    starts: tuple[ApprovedStart, ...]

    @model_validator(mode="after")
    def _check(self):
        """Require unique approved job IDs and starts in the action set's current slot."""
        _unique([s.job_id for s in self.starts], "approved job ids")
        bad = [s.job_id for s in self.starts if s.start_slot != self.slot]
        if bad:
            raise ValueError(f"approved actions must start in the current slot {self.slot}: {bad}")
        return self

    @classmethod
    def from_checked_plan(
        cls, plan: Plan, check: "CheckResult", expected_state_version: int
    ) -> "ApprovedActions":
        """Contract demonstration of the execute_step gate; not the runtime gate itself.

        ``expected_state_version`` is the latest state version checked by the gate and may
        differ from ``plan.state_version`` if the same-slot state changed after proposal.
        The production runtime must atomically compare this version with live state at apply.
        """
        if type(expected_state_version) is not int or expected_state_version < 0:
            raise ContractError("expected_state_version must be a non-negative integer")
        if check.status != "pass":
            raise ContractError(f"check status is {check.status!r}, not 'pass'")
        if check.plan_hash != plan.plan_hash:
            raise ContractError("check was performed on a different plan")
        if check.episode_id != plan.episode_id:
            raise ContractError("check episode does not match the plan episode")
        if check.slot != plan.slot:
            raise ContractError("check slot does not match the plan slot")
        if check.state_version != expected_state_version:
            raise ContractError("check state version does not match latest expected state version")
        return cls(
            episode_id=plan.episode_id,
            slot=plan.slot,
            # Bind the action to the latest state actually checked, not the plan's origin state.
            state_version=check.state_version,
            plan_hash=plan.plan_hash,
            check_id=check.check_id,
            starts=tuple(
                ApprovedStart(job_id=s.job_id, start_slot=s.start_slot) for s in plan.current_starts
            ),
        )


class Claim(Record):
    claim_id: GenericId
    text: Text
    evidence_ids: tuple[EvidenceId, ...] = ()
    value: Optional[Number] = None
    unit: Optional[Unit] = None

    @model_validator(mode="after")
    def _check(self):
        """Require a numeric claim value and its unit to be supplied together."""
        if (self.value is None) != (self.unit is None):
            raise ValueError("claim value and unit must be given together")
        return self


class Explanation(Record):
    source: Literal["llm", "template"]
    summary: Text
    claims: tuple[Claim, ...] = ()
    limitations: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check(self):
        """Reject duplicate claim IDs within the explanation."""
        _unique([c.claim_id for c in self.claims], "claim ids")
        return self


class PolicyOutput(Versioned):
    """Envelope returned by ``propose``; ``plan`` is None when there is no usable plan."""

    record_type: Literal["PolicyOutput"] = "PolicyOutput"
    system: SystemId
    output_status: Literal["ok", "no_output", "malformed", "error"]
    plan: Optional[Plan] = None
    explanation: Optional[Explanation] = None
    raw_response: Optional[str] = None

    @model_validator(mode="after")
    def _check(self):
        """Require a plan exactly when the output status is successful."""
        if self.output_status == "ok" and self.plan is None:
            raise ValueError("output_status 'ok' requires a plan")
        if self.output_status != "ok" and self.plan is not None:
            raise ValueError("a plan may only accompany output_status 'ok'")
        return self


# --------------------------------------------------------------------------- check result
ViolationType = Literal[
    "schema",
    "unknown_job",
    "duplicate_job",
    "start_before_arrival",
    "start_before_current",
    "deadline",
    "nonflexible_start",
    "capacity",
    "missing_evidence",
    "stale_evidence",
    "other",
]
CheckName = Literal[
    "schema", "ids", "timing", "deadline", "nonflexible", "capacity", "evidence", "freshness"
]
Outcome = Literal["pass", "fail", "error"]
EvidenceKind = Literal["capacity", "constraints", "jobs", "carbon", "freshness"]


class Violation(Record):
    violation_type: ViolationType
    job_ids: tuple[JobId, ...] = ()
    constraint_ids: tuple[ConstraintId, ...] = ()
    slot: Optional[Slot] = None
    message: Text


class PerformedCheck(Record):
    name: CheckName
    outcome: Outcome
    constraint_ids: tuple[ConstraintId, ...] = ()


class SkippedCheck(Record):
    name: CheckName
    reason: Text


class EvidenceItem(Record):
    kind: EvidenceKind
    status: Literal["available", "missing", "stale", "partial"]
    ids: tuple[EvidenceId, ...] = ()


class CheckResult(Versioned):
    """Feasibility verdict (``status``) kept separate from impact-claim support."""

    record_type: Literal["CheckResult"] = "CheckResult"
    check_id: CheckId
    episode_id: EpisodeId
    slot: Slot
    state_version: NonNegInt
    plan_hash: Hex64
    status: Outcome
    violations: tuple[Violation, ...] = ()
    performed: tuple[PerformedCheck, ...] = ()
    skipped: tuple[SkippedCheck, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()
    impact_claim_support: Literal["supported", "unsupported", "not_assessed"]
    errors: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check(self):
        """Validate verdicts and performed checks, requiring traceable capacity for passes."""
        _unique([p.name for p in self.performed], "performed checks")
        _unique([e.kind for e in self.evidence], "evidence kinds")
        outcomes = {p.outcome for p in self.performed}
        performed_names = {p.name for p in self.performed}
        skipped_names = {check.name for check in self.skipped}
        if performed_names & skipped_names:
            raise ValueError("a check cannot be both performed and skipped")
        if self.status == "pass":
            if not self.performed:
                raise ValueError("a passing result must list the checks actually performed")
            if outcomes != {"pass"} or self.violations or self.errors:
                raise ValueError(
                    "a passing result cannot contain failed/error checks or violations"
                )
            required_pass_checks = {
              "schema", 
              "ids", 
              "timing", 
              "deadline", 
              "nonflexible", 
              "capacity"
            }
            missing_checks = required_pass_checks - performed_names
            if missing_checks:
                raise ValueError(
                    "a passing result requires the core checks to be performed: "
                    f"{sorted(missing_checks)}"
                )
            capacity = [e for e in self.evidence if e.kind == "capacity"]
            if not capacity or capacity[0].status != "available":
                raise ValueError("a passing result requires available capacity evidence")
            capacity_ids = {item for item in capacity[0].ids if item.startswith("CON-")}
            capacity_check = next(p for p in self.performed if p.name == "capacity")
            if not capacity_ids or not capacity_check.constraint_ids:
                raise ValueError(
                    "passing capacity evidence and the performed capacity check must identify "
                    "the capacity constraint"
                )
            if not capacity_ids.intersection(capacity_check.constraint_ids):
                raise ValueError(
                    "passing capacity evidence must match the constraint checked for capacity"
                )
        if self.status == "fail":
            if not self.violations:
                raise ValueError("a failing result must list at least one violation")
            if "fail" not in outcomes or "error" in outcomes:
                raise ValueError(
                    "a failing result requires a failed performed check and cannot contain "
                    "an errored check"
                )
        if self.status == "error" and not (self.errors or "error" in outcomes):
            raise ValueError("an error result must report an error")
        return self


# --------------------------------------------------------------------------- decision record
Stage = Literal["initial", "repaired", "fallback"]


class StageRecord(Record):
    """One proposal stage; ``check`` None means it was not checked (never an implied pass)."""

    plan: Plan
    check: Optional[CheckResult] = None

    @model_validator(mode="after")
    def _check(self):
        """Bind an optional stage check to its plan hash, episode, slot, and state version."""
        if self.check is not None:
            if self.check.plan_hash != self.plan.plan_hash:
                raise ValueError("stage check refers to a different plan")
            if self.check.episode_id != self.plan.episode_id or self.check.slot != self.plan.slot:
                raise ValueError("stage check episode/slot does not match its plan")
            if self.check.state_version != self.plan.state_version:
                raise ValueError("stage check state version does not match its plan")
        return self


class DecisionRecord(Versioned):
    record_type: Literal["DecisionRecord"] = "DecisionRecord"
    decision_id: DecisionId
    system: SystemId
    run_id: GenericId
    episode_id: EpisodeId
    trial: Optional[NonNegInt] = None
    slot: Slot
    input_hash: Optional[Hex64] = None
    config_hash: Optional[Hex64] = None
    raw_response: Optional[str] = None
    initial: Optional[StageRecord] = None
    repaired: Optional[StageRecord] = None
    fallback: Optional[StageRecord] = None
    # Stages that do not exist for this system. Absent AND unlisted = not performed.
    not_applicable_stages: tuple[Stage, ...] = ()
    execution_check: Optional[CheckResult] = None  # latest-state recheck gating execution
    final_status: Literal["executed", "blocked", "abstained", "escalated", "error"]
    executed_starts: tuple[ApprovedStart, ...] = ()
    explanation: Optional[Explanation] = None
    evidence_ids: tuple[EvidenceId, ...] = ()
    model_call_count: NonNegInt = 0
    repair_count: NonNegInt = 0
    latency_ms: Optional[NonNegNumber] = None
    prompt_tokens: Optional[NonNegInt] = None
    completion_tokens: Optional[NonNegInt] = None
    cost_usd: Optional[NonNegNumber] = None
    errors: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check(self):
        """Validate stages and require execution to match the checked current starts."""
        _unique(self.not_applicable_stages, "not_applicable_stages")
        for stage_name in ("initial", "repaired", "fallback"):
            stage_record = getattr(self, stage_name)
            if stage_record is not None and (
                stage_record.plan.episode_id != self.episode_id
                or stage_record.plan.slot != self.slot
            ):
                raise ValueError(f"{stage_name} plan episode/slot does not match decision record")
        if self.execution_check is not None:
            if self.execution_check.episode_id != self.episode_id:
                raise ValueError("execution_check episode does not match decision record")
            if self.execution_check.slot != self.slot:
                raise ValueError("execution_check slot does not match decision record")
            recorded_plans = [
                stage_record.plan
                for stage_record in (self.initial, self.repaired, self.fallback)
                if stage_record is not None
            ]
            matching_plans = [
                plan for plan in recorded_plans if plan.plan_hash == self.execution_check.plan_hash
            ]
            if not matching_plans:
                raise ValueError("execution_check does not match a recorded stage plan")
            # A latest-state execution recheck may legitimately use a newer state version
            # than the proposal. Its plan hash/episode/slot must still match. The execution
            # gate must compare this check's state_version with the live version at apply time.
        for stage in self.not_applicable_stages:
            if getattr(self, stage) is not None:
                raise ValueError(f"stage {stage!r} is marked not applicable but has content")
        _unique([s.job_id for s in self.executed_starts], "executed job ids")
        if self.final_status == "executed":
            gate = self.execution_check
            if gate is None or gate.status != "pass":
                raise ValueError("final_status 'executed' requires a passing execution_check")
            plans = [
                stage_record.plan
                for stage_record in (self.initial, self.repaired, self.fallback)
                if stage_record is not None and stage_record.plan.plan_hash == gate.plan_hash
            ]
            if not plans:
                raise ValueError("execution_check does not match any recorded stage plan")
            allowed = {(item.job_id, item.start_slot) for item in plans[0].current_starts}
            actual = {(item.job_id, item.start_slot) for item in self.executed_starts}
            if actual != allowed:
                missing = allowed - actual
                extra = actual - allowed
                raise ValueError(
                    "executed starts must exactly match the checked plan's current starts; "
                    f"missing={sorted(missing)}, extra={sorted(extra)}"
                )
        elif self.executed_starts:
            raise ValueError("executed starts require final_status 'executed'")
        return self


# --------------------------------------------------------------------------- solver result
SolverStatus = Literal[
    "certified_optimal", "certified_infeasible", "unresolved", "insufficient_evidence"
]


class SolverResult(Versioned):
    """Offline reference output. Timeout/unknown never means infeasible or optimal.

    ``insufficient_evidence`` (for example forecast missing before a deadline) is distinct
    from physical infeasibility (Q08). Backend, tolerances and tie-breaking are recorded,
    not chosen, here.
    """

    record_type: Literal["SolverResult"] = "SolverResult"
    solver_result_id: GenericId
    kind: Literal["visible", "hindsight"]
    uses_future_arrivals: Flag
    offline_only: Literal[True] = True
    input_hash: Hex64
    status: SolverStatus
    backend: Text
    backend_version: Text
    time_limit_s: Optional[PosNumber] = None
    elapsed_s: NonNegNumber
    termination: Text
    tolerance: Optional[NonNegNumber] = None
    objective_kg: Optional[NonNegNumber] = None
    bound_kg: Optional[NonNegNumber] = None
    gap: Optional[NonNegNumber] = None
    tie_break: Optional[Text] = None
    certification_basis: Optional[Text] = None
    schedule: Optional[tuple[PlannedStart, ...]] = None
    unresolved_reason: Optional[Text] = None
    matching_work_job_ids: tuple[JobId, ...] = ()

    @model_validator(mode="after")
    def _check(self):
        """Validate visibility, certification, status-dependent outputs, and schedule IDs."""
        if self.kind == "visible" and self.uses_future_arrivals:
            raise ValueError("a visible-state solve cannot use future arrivals")
        if self.kind == "hindsight" and not self.uses_future_arrivals:
            raise ValueError("a hindsight solve is defined by using future arrivals")
        certified = self.status in ("certified_optimal", "certified_infeasible")
        if certified and not self.certification_basis:
            raise ValueError("certified statuses require certification_basis")
        if not certified and self.certification_basis:
            raise ValueError("uncertified statuses cannot carry a certification_basis")
        if self.status == "certified_optimal":
            if self.objective_kg is None or self.schedule is None:
                raise ValueError("certified_optimal requires objective_kg and schedule")
        else:
            if self.objective_kg is not None or self.schedule is not None:
                raise ValueError(f"{self.status} cannot carry an objective or schedule")
        if self.status in ("unresolved", "insufficient_evidence") and not self.unresolved_reason:
            raise ValueError(f"{self.status} requires unresolved_reason")
        if self.schedule is not None:
            _unique([s.job_id for s in self.schedule], "scheduled job ids")
        return self


# --------------------------------------------------------------------------- episode results
class SlotRecord(Record):
    """Per-slot values supplied by the simulator/impact modules; nothing is recomputed here."""

    slot: Slot
    phase: Literal["decision", "completion"]
    job_load_kw: NonNegNumber
    background_load_kw: NonNegNumber
    energy_kwh: Optional[NonNegNumber] = None
    emissions_kg: Optional[NonNegNumber] = None
    started_job_ids: tuple[JobId, ...] = ()
    running_job_ids: tuple[JobId, ...] = ()
    completed_job_ids: tuple[JobId, ...] = ()


class EpisodeTotals(Record):
    """All fields optional: None means the calculation module has not supplied the value."""

    job_energy_kwh: Optional[NonNegNumber] = None
    background_energy_kwh: Optional[NonNegNumber] = None
    site_energy_kwh: Optional[NonNegNumber] = None
    job_emissions_kg: Optional[NonNegNumber] = None
    background_emissions_kg: Optional[NonNegNumber] = None
    site_emissions_kg: Optional[NonNegNumber] = None


class CompletedWork(Record):
    """Q03 leaves the unit of completed work open, so the definition is stated explicitly."""

    value: NonNegNumber
    unit: Text
    definition: Text


class EpisodeResult(Versioned):
    record_type: Literal["EpisodeResult"] = "EpisodeResult"
    episode_id: EpisodeId
    run_id: GenericId
    system: SystemId
    trial: Optional[NonNegInt] = None
    n_decision_slots: PosInt
    n_completion_slots: NonNegInt
    slots: tuple[SlotRecord, ...]
    totals: EpisodeTotals
    job_count_total: NonNegInt
    completed_job_ids: tuple[JobId, ...] = ()
    deadline_missed_job_ids: tuple[JobId, ...] = ()
    unfinished_job_ids: tuple[JobId, ...] = ()
    completed_work: Optional[CompletedWork] = None
    reference_solver_result_id: Optional[GenericId] = None
    reference_status: Optional[SolverStatus] = None
    trace_refs: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check(self):
        """Validate contiguous slot phases, unique job outcomes, and completed-job counts."""
        expected = self.n_decision_slots + self.n_completion_slots
        if [s.slot for s in self.slots] != list(range(expected)):
            raise ValueError(f"slots must be contiguous 0..{expected - 1}")
        for s in self.slots:
            phase = "decision" if s.slot < self.n_decision_slots else "completion"
            if s.phase != phase:
                raise ValueError(f"slot {s.slot} phase must be {phase!r}")
        for name in ("completed_job_ids", "deadline_missed_job_ids", "unfinished_job_ids"):
            _unique(getattr(self, name), name)
        both = set(self.completed_job_ids) & (
            set(self.deadline_missed_job_ids) | set(self.unfinished_job_ids)
        )
        if both:
            raise ValueError(f"jobs both completed and missed/unfinished: {sorted(both)}")
        if len(self.completed_job_ids) > self.job_count_total:
            raise ValueError("more completed jobs than job_count_total")
        return self


# --------------------------------------------------------------------------- private fixture
class PrivateJob(Record):
    """Private view of a job with generator metadata. Never policy-visible."""

    job: Job
    scenario_id: GenericId
    split: Split
    seed: Annotated[int, Strict()]
    synthetic: Flag
    intentionally_infeasible: Optional[Flag] = None


class PrivateEpisode(Versioned):
    """Immutable private episode manifest consumed by ``reset``; not a policy input."""

    record_type: Literal["PrivateEpisode"] = "PrivateEpisode"
    episode_id: EpisodeId
    scenario_id: GenericId
    split: Split
    seed: Annotated[int, Strict()]
    n_decision_slots: PosInt
    n_completion_slots: NonNegInt
    snapshot: ConstraintSnapshot
    jobs: tuple[PrivateJob, ...]
    realized_carbon: tuple[CarbonObservation, ...] = ()
    forecast_visibility: Literal["perfect_foresight", "persistence", "withheld", "unresolved"]
    reference_refs: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check(self):
        """Reject duplicate private job IDs and realized carbon observation IDs."""
        _unique([j.job.job_id for j in self.jobs], "job ids")
        _unique([o.fact_id for o in self.realized_carbon], "carbon observation ids")
        return self


RECORD_TYPES: dict[str, type] = {
    cls.model_fields["record_type"].default: cls
    for cls in (
        SourceRef,
        SiteConfig,
        Constraint,
        ConstraintSnapshot,
        Job,
        CarbonObservation,
        CarbonForecast,
        VisibleState,
        Context,
        Plan,
        ApprovedActions,
        PolicyOutput,
        CheckResult,
        DecisionRecord,
        SolverResult,
        EpisodeResult,
        PrivateEpisode,
    )
}


def parse_record(data: dict):
    """Dispatch decoded JSON to its record class by ``record_type`` (strict validation)."""
    kind = data.get("record_type") if isinstance(data, dict) else None
    if kind not in RECORD_TYPES:
        raise ContractError(f"unknown or missing record_type {kind!r}")
    return RECORD_TYPES[kind].from_jsonable(data)
