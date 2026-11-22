"""Deterministic, explainable rules-v1 scheduler (RULE-02, issue #240; spec RULE-01 R01-R09).

Pure functions over F02 ``VisibleState`` + ``ConstraintSnapshot``. This module has no
simulator, checker, filesystem, clock or model access; ``runner.py`` owns checked execution.
Existing F02 records (Job, VisibleState, ConstraintSnapshot, Plan) are reused unchanged.

Scoped envelope (RULE-01): at most four visible waiting jobs, every candidate start in the
absolute slots 0-5 (six start choices) plus one *unscheduled* option per job, so at most
7**4 = 2401 assignments, all enumerated. Anything outside is rejected explicitly with a
structured error; nothing is truncated or sampled.

Arithmetic is integer: power, capacity, background and score weights must be integral.
IT capacity is checked before PUE; PUE is never multiplied into the R04 limit.

SCORE CONVENTION (source and limits). The merged RULE-04 generator defines the artificial
accounting unit as ``impact = power_kW x 1 h x PUE 1.0 x weight (score-kWh)``
(``dc_sustainability/evaluation/rule_study_generator.py``, accounting ``units`` field), the
review-2 decision (docs/decisions/NOV19_RULE01_REVIEW_REVISION.md item 13) requires reporting
"artificial score weights" with that weighted-energy convention and forbids calling them
g/kWh or emissions, and Edison's reply (#239 comment 7052918378) accepts the artificial units.
``ScoreKwhConvention`` implements exactly that with integer arithmetic (slot-hour and PUE are
both 1 in every authored/generated case, so the integer sum of power_kW x weight over the
occupied slots is the score-kWh value). Independent accounting receiving by Edison is still
pending. ``UnweightedSlotScore`` is a TEST-ONLY alternative that proves the isolation; it is
not agreed and is never used for a study run. Weights are not measured g/kWh or emissions.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import product
from typing import Literal, Mapping, Optional

from dc_sustainability import schemas as s
from dc_sustainability.rule_study.records import ArithmeticEntry, ArithmeticTerm, RecordError
from dc_sustainability.verification.rules import assess_forecasts

# ----------------------------------------------------------------------------- scope bounds
MAX_WAITING_JOBS = 4
FIRST_START_SLOT = 0
LAST_START_SLOT = 5  # six candidate start slots: 0..5
MAX_START_SLOTS = 6
MAX_ASSIGNMENTS = (MAX_START_SLOTS + 1) ** MAX_WAITING_JOBS  # 7**4 == 2401
LAST_DECISION_SLOT = s.PROPOSED_DECISION_SLOTS - 1  # Q01: new starts only in slots 0-23
HORIZON = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS  # 30
UNSCHEDULED_START = 99  # sorts after every legal start in the start vector

# ----------------------------------------------------------------------------- score conventions
SCORE_KWH_STATUS = (
    "defined by the merged RULE-04 generator accounting units (power_kW x 1 h x PUE 1.0 x "
    "weight, artificial score-kWh) and accepted as artificial units by Edison (#239 comment "
    "7052918378); independent accounting receiving is still pending; not g/kWh or emissions"
)
TEST_ONLY_SCORE_STATUS = "TEST-ONLY alternative convention; not agreed; never used in a study run"


@dataclass(frozen=True)
class ScoreTerm:
    slot: int
    power_kw: int
    weight: int
    value: int


@dataclass(frozen=True)
class JobScore:
    total: int
    terms: tuple[ScoreTerm, ...]


class ScoreConvention:
    """Isolated score calculation: replace it without touching the scheduler."""

    convention_id: str = ""
    unit: str = ""
    status: str = ""
    formula: str = ""

    def job_score(
        self, *, power_kw: int, start: int, duration_slots: int, weights: Mapping[int, int]
    ) -> JobScore:
        raise NotImplementedError


class ScoreKwhConvention(ScoreConvention):
    """Artificial score-kWh: sum over occupied slots of integer kW x weight (slot-hour 1, PUE 1).

    PUE multiplies the (power x weight) sum by a common positive factor, so it cannot change any
    ordering; in every authored/generated case it is exactly 1.0, so none is applied here.
    """

    convention_id = "score-kwh-v1"
    unit = "score-kWh (artificial score weight x kWh; not g/kWh, not emissions)"
    status = SCORE_KWH_STATUS
    formula = (
        "sum over occupied slots t in [start, start+duration): power_kw * 1 h * PUE(1.0) * "
        "weight[t] (integer arithmetic)"
    )

    def job_score(self, *, power_kw, start, duration_slots, weights):
        terms = tuple(
            ScoreTerm(t, power_kw, weights[t], power_kw * weights[t])
            for t in range(start, start + duration_slots)
        )
        return JobScore(sum(term.value for term in terms), terms)


class UnweightedSlotScore(ScoreConvention):
    """TEST-ONLY alternative that ignores job power; exists to prove the isolation."""

    convention_id = "test-only-slot-sum"
    unit = "artificial score weight x slot (test only)"
    status = TEST_ONLY_SCORE_STATUS
    formula = "sum over occupied slots t in [start, start+duration): weight[t] (integer)"

    def job_score(self, *, power_kw, start, duration_slots, weights):
        terms = tuple(
            ScoreTerm(t, power_kw, weights[t], weights[t])
            for t in range(start, start + duration_slots)
        )
        return JobScore(sum(term.value for term in terms), terms)


# ----------------------------------------------------------------------------- result types
@dataclass(frozen=True)
class ObjectiveTuple:
    """R06 objective. ``sort_key`` is minimized; vectors are in canonical priority order."""

    scheduled_count: int
    inclusion_vector: tuple[int, ...]
    synthetic_score: int
    completion_sum: int
    start_vector: tuple[int, ...]

    @property
    def sort_key(self) -> tuple:
        return (
            -self.scheduled_count,
            tuple(-bit for bit in self.inclusion_vector),
            self.synthetic_score,
            self.completion_sum,
            self.start_vector,
        )


@dataclass(frozen=True)
class ScheduleCandidate:
    schedule_id: str
    starts: tuple[tuple[str, Optional[int]], ...]  # canonical job order; None = unscheduled
    feasible: bool
    first_violation: Optional[tuple[int, int]]  # (slot, signed excess) when infeasible
    objective: Optional[ObjectiveTuple]


@dataclass(frozen=True)
class SearchSummary:
    job_order: tuple[str, ...]
    windows: tuple[tuple[str, tuple[int, ...]], ...]
    total_assignments: int
    accepted: tuple[str, ...]
    rejected: tuple[tuple[str, int, int], ...]  # (schedule_id, first violating slot, excess)
    candidates: tuple[ScheduleCandidate, ...]  # every enumerated assignment, none dropped


@dataclass(frozen=True)
class RulesV1Decision:
    """``proposed``: plan is the unchanged selection. ``fallback_required``: R08 disabled
    score optimization (no rules plan exists). ``rejected``: R01/scope failed closed."""

    status: Literal["proposed", "fallback_required", "rejected"]
    plan: Optional[s.Plan]
    fallback_reason: Optional[str]
    selected: Optional[ScheduleCandidate]
    objective: Optional[ObjectiveTuple]
    search: Optional[SearchSummary]
    arithmetic: tuple[ArithmeticEntry, ...]
    rule_ids: tuple[str, ...]
    errors: tuple[RecordError, ...]
    unscheduled_job_ids: tuple[str, ...]
    score_convention_id: Optional[str]


# ----------------------------------------------------------------------------- small helpers
def _term(label, value, unit, job_id=None):
    return ArithmeticTerm(label=label, job_id=job_id, value=int(value), unit=unit)


def _entry(rule_id, terms, *, outcome, unit, formula, total=None, limit=None, slot=None, cid=None):
    excess = None if total is None or limit is None else total - limit
    return ArithmeticEntry(
        rule_id=rule_id,
        constraint_id=cid,
        slot=slot,
        terms=tuple(terms),
        total=total,
        limit=limit,
        signed_excess=excess,
        outcome=outcome,
        unit=unit,
        formula=formula,
    )


def _error(code, message, stage=None):
    return RecordError(stage=stage, code=code, message=message)


def legal_window(job: s.Job, now: int) -> tuple[int, ...]:
    """R02/R03 start slots ignoring capacity: arrived, >= now, <= 23, done by deadline and 30."""
    first = max(now, job.arrival_slot)
    last = min(
        LAST_DECISION_SLOT, job.deadline_slot - job.duration_slots, HORIZON - job.duration_slots
    )
    return tuple(t for t in range(first, last + 1) if job.flexible or t == job.arrival_slot)


def latest_start(job: s.Job) -> int:
    """Latest legal start slot (arrival for nonflexible work); may be below arrival if impossible."""
    last = min(
        LAST_DECISION_SLOT, job.deadline_slot - job.duration_slots, HORIZON - job.duration_slots
    )
    return last if job.flexible else min(last, job.arrival_slot)


def priority_key(job: s.Job) -> tuple:
    """R06 level 2 order: nonflexible, earliest latest-start, earlier deadline, job ID."""
    return (job.flexible, latest_start(job), job.deadline_slot, job.job_id)


def _is_integral(value: float) -> bool:
    return float(value).is_integer()


def _coverage_reason(assessment, fact_slots: set[int]) -> Optional[str]:
    """Same reason labels/precedence Greedy B reports, so fallback reasons are comparable."""
    if assessment.beyond_horizon_slots:
        return "beyond-horizon"
    if assessment.future_issued_slots:
        return "future"
    if assessment.stale_slots:
        return "stale"
    if assessment.missing_slots and set(assessment.required_slots) & fact_slots:
        return "partial"
    if assessment.missing_slots:
        return "missing"
    return None


# ----------------------------------------------------------------------------- R01 / scope
@dataclass(frozen=True)
class _Validated:
    state: s.VisibleState
    snapshot: s.ConstraintSnapshot
    capacity: int
    capacity_id: str
    background: int


def _validate_r01(state, snapshot, decision_time_utc, expected_state_version):
    errors: list[RecordError] = []
    if not isinstance(state, s.VisibleState) or not isinstance(snapshot, s.ConstraintSnapshot):
        return None, [_error("R01_MALFORMED_INPUT", "state/snapshot must be F02 records")]
    try:
        state = s.VisibleState.model_validate(
            state.model_dump(mode="python", warnings="none"), strict=True
        )
        snapshot = s.ConstraintSnapshot.model_validate(
            snapshot.model_dump(mode="python", warnings="none"), strict=True
        )
    except ValueError as exc:
        return None, [_error("R01_MALFORMED_INPUT", f"strict revalidation failed: {exc}")]
    if state.constraint_snapshot_id != snapshot.snapshot_id:
        errors.append(_error("R01_SNAPSHOT_MISMATCH", "state and constraint snapshot IDs differ"))
    else:
        try:
            s.Context.build(state, snapshot, representation="flat")
        except ValueError as exc:
            errors.append(_error("R01_INCONSISTENT_EVIDENCE", f"evidence is inconsistent: {exc}"))
    if state.current_slot >= HORIZON:
        errors.append(_error("R01_SLOT_OUT_OF_HORIZON", f"slot {state.current_slot} >= {HORIZON}"))
    if expected_state_version is not None and expected_state_version != state.state_version:
        errors.append(
            _error(
                "R01_STALE_STATE_VERSION",
                f"expected state version {expected_state_version}, visible {state.state_version}",
            )
        )
    if not isinstance(decision_time_utc, datetime) or decision_time_utc.utcoffset() != timedelta(0):
        errors.append(
            _error("R01_DECISION_TIME", "an explicit trusted UTC decision time is required")
        )
    capacities = snapshot.constraints_of("capacity")
    capacity = capacity_id = None
    if not capacities:
        errors.append(
            _error(
                "R01_MISSING_CAPACITY", "authoritative capacity evidence is missing; not unlimited"
            )
        )
    elif not _is_integral(capacities[0].limit_value):
        errors.append(_error("R01_NON_INTEGER_CAPACITY", "IT capacity must be integral kW"))
    else:
        capacity, capacity_id = int(capacities[0].limit_value), capacities[0].constraint_id
    if not _is_integral(state.site.background_kw):
        errors.append(_error("R01_NON_INTEGER_POWER", "background load must be integral kW"))
    for job in (*state.waiting_jobs, *(r.job for r in state.running_jobs)):
        if not _is_integral(job.power_kw):
            errors.append(
                _error("R01_NON_INTEGER_POWER", f"job {job.job_id} power must be integral kW")
            )
    if errors:
        return None, errors
    return _Validated(state, snapshot, capacity, capacity_id, int(state.site.background_kw)), []


def _scope_errors(state: s.VisibleState) -> list[RecordError]:
    errors = []
    if len(state.waiting_jobs) > MAX_WAITING_JOBS:
        errors.append(
            _error(
                "SCOPE_TOO_MANY_WAITING_JOBS",
                f"{len(state.waiting_jobs)} visible waiting jobs exceed the scoped maximum "
                f"{MAX_WAITING_JOBS}; nothing is truncated or sampled",
            )
        )
    for job in sorted(state.waiting_jobs, key=lambda j: j.job_id):
        window = legal_window(job, state.current_slot)
        if len(window) > MAX_START_SLOTS:
            errors.append(
                _error(
                    "SCOPE_TOO_MANY_START_SLOTS",
                    f"job {job.job_id} has {len(window)} candidate starts; the scope is "
                    f"{MAX_START_SLOTS} (slots {FIRST_START_SLOT}-{LAST_START_SLOT})",
                )
            )
        outside = [t for t in window if not FIRST_START_SLOT <= t <= LAST_START_SLOT]
        if outside:
            errors.append(
                _error(
                    "SCOPE_START_SLOT_OUTSIDE",
                    f"job {job.job_id} has candidate starts {outside} outside slots "
                    f"{FIRST_START_SLOT}-{LAST_START_SLOT}",
                )
            )
    return errors


# ----------------------------------------------------------------------------- main entry
def propose_rules_v1(
    state: s.VisibleState,
    snapshot: s.ConstraintSnapshot,
    *,
    decision_time_utc: datetime,
    score_convention: ScoreConvention,
    expected_state_version: Optional[int] = None,
) -> RulesV1Decision:
    """Return the rules-v1 decision. Never mutates anything and never raises on bad data."""
    if not isinstance(score_convention, ScoreConvention) or not score_convention.convention_id:
        raise TypeError("an explicit ScoreConvention is required; none is assumed")
    validated, errors = _validate_r01(state, snapshot, decision_time_utc, expected_state_version)
    if validated is None:
        return _rejected(errors, ("R01", "R09"))
    state, snapshot = validated.state, validated.snapshot
    scope = _scope_errors(state)
    if scope:
        return _rejected(scope, ("R01", "R05", "R09"))

    now = state.current_slot
    r01 = _entry(
        "R01",
        [
            _term("state_version", state.state_version, "version"),
            _term("current_slot", now, "slot"),
            _term("capacity_kw", validated.capacity, "kW"),
            _term("background_kw", validated.background, "kW"),
            _term("waiting_jobs", len(state.waiting_jobs), "jobs"),
        ],
        outcome="computed",
        unit="mixed",
        formula="validated exact visible state/version, unique job IDs, authoritative capacity",
        cid=validated.capacity_id,
    )

    # R08: forecast coverage gates score optimization.
    reason = None
    try:
        assessment = assess_forecasts(state, snapshot, decision_time_utc=decision_time_utc)
        reason = _coverage_reason(assessment, {f.valid_slot for f in state.carbon_facts})
        counts = {
            "required_slots": len(assessment.required_slots),
            "missing_slots": len(assessment.missing_slots),
            "stale_slots": len(assessment.stale_slots),
            "future_issued_slots": len(assessment.future_issued_slots),
            "beyond_horizon_slots": len(assessment.beyond_horizon_slots),
        }
    except s.MissingEvidenceError as exc:
        reason, counts = "freshness_evidence_missing", None
        missing_message = str(exc)
    if counts is not None:
        problems = sum(v for k, v in counts.items() if k != "required_slots")
        r08 = _entry(
            "R08",
            [_term(k, v, "slot") for k, v in counts.items()],
            outcome="fail" if reason else "pass",
            unit="slot",
            formula="problem slots (missing+stale+future+beyond) <= 0 for usable coverage",
            total=problems,
            limit=0,
        )
    else:
        r08 = _entry(
            "R08",
            [_term("freshness_constraint_present", 0, "flag")],
            outcome="fail",
            unit="flag",
            formula="authoritative freshness constraint is required to assess staleness",
            total=1,
            limit=0,
        )
    if reason is not None:
        err = _error(
            "R08_SCORE_OPTIMIZATION_DISABLED",
            f"forecast coverage not usable ({reason})"
            + (f": {missing_message}" if counts is None else "")
            + "; route to independently production-checked Greedy A",
        )
        return RulesV1Decision(
            status="fallback_required",
            plan=None,
            fallback_reason=reason,
            selected=None,
            objective=None,
            search=None,
            arithmetic=(r01, r08),
            rule_ids=("R01", "R08", "R09"),
            errors=(err,),
            unscheduled_job_ids=(),
            score_convention_id=None,
        )

    weights: dict[int, int] = {}
    fact_ids: dict[int, str] = {}
    for fact in state.carbon_facts:
        if not _is_integral(fact.value):
            return _rejected(
                [
                    _error(
                        "R01_NON_INTEGER_SCORE",
                        f"score weight at slot {fact.valid_slot} is not integral",
                    )
                ],
                ("R01", "R06", "R09"),
            )
        weights[fact.valid_slot] = int(fact.value)
        fact_ids[fact.valid_slot] = fact.fact_id

    return _search_and_plan(validated, weights, fact_ids, score_convention, (r01, r08))


def _rejected(errors, rule_ids) -> RulesV1Decision:
    return RulesV1Decision(
        status="rejected",
        plan=None,
        fallback_reason=None,
        selected=None,
        objective=None,
        search=None,
        arithmetic=(),
        rule_ids=tuple(rule_ids),
        errors=tuple(errors),
        unscheduled_job_ids=(),
        score_convention_id=None,
    )


# ----------------------------------------------------------------------------- R04/R05/R06
def _base_load(validated: _Validated) -> dict[int, int]:
    state = validated.state
    load = {t: validated.background for t in range(state.current_slot, HORIZON)}
    for running in state.running_jobs:
        for t in range(running.start_slot, running.end_slot):
            if t in load:
                load[t] += int(running.job.power_kw)
    return load


def _search_and_plan(validated, weights, fact_ids, convention, lead_entries) -> RulesV1Decision:
    state = validated.state
    now, capacity = state.current_slot, validated.capacity
    jobs = sorted(state.waiting_jobs, key=priority_key)
    base = _base_load(validated)
    over = [(t, base[t] - capacity) for t in sorted(base) if base[t] > capacity]
    if over:
        slot, excess = over[0]
        return _rejected(
            [
                _error(
                    "R04_BASE_LOAD_EXCEEDS_CAPACITY",
                    f"background+running load exceeds IT capacity at slot {slot} by {excess} kW",
                )
            ],
            ("R01", "R04", "R09"),
        )

    windows = {job.job_id: legal_window(job, now) for job in jobs}
    options = [(*windows[job.job_id], None) for job in jobs]
    power = {job.job_id: int(job.power_kw) for job in jobs}
    job_score: dict[tuple[str, int], JobScore] = {}
    candidates: list[ScheduleCandidate] = []
    accepted, rejected = [], []
    for index, choice in enumerate(product(*options)):
        schedule_id = f"SCH-{index:04d}"
        extra = [0] * HORIZON
        for job, start in zip(jobs, choice):
            if start is not None:
                for t in range(start, start + job.duration_slots):
                    extra[t] += power[job.job_id]
        violation = next(
            (
                (t, base[t] + extra[t] - capacity)
                for t in range(now, HORIZON)
                if base[t] + extra[t] > capacity
            ),
            None,
        )
        starts = tuple((job.job_id, start) for job, start in zip(jobs, choice))
        if violation is not None:
            rejected.append((schedule_id, violation[0], violation[1]))
            candidates.append(ScheduleCandidate(schedule_id, starts, False, violation, None))
            continue
        total = 0
        for job, start in zip(jobs, choice):
            if start is None:
                continue
            key = (job.job_id, start)
            if key not in job_score:
                try:
                    job_score[key] = convention.job_score(
                        power_kw=power[job.job_id],
                        start=start,
                        duration_slots=job.duration_slots,
                        weights=weights,
                    )
                except KeyError as exc:
                    return _rejected(
                        [
                            _error(
                                "R06_SCORE_WEIGHT_MISSING",
                                f"no score weight for slot {exc.args[0]}",
                            )
                        ],
                        ("R06", "R09"),
                    )
            total += job_score[key].total
        objective = ObjectiveTuple(
            scheduled_count=sum(start is not None for start in choice),
            inclusion_vector=tuple(int(start is not None) for start in choice),
            synthetic_score=total,
            completion_sum=sum(
                start + job.duration_slots for job, start in zip(jobs, choice) if start is not None
            ),
            start_vector=tuple(UNSCHEDULED_START if start is None else start for start in choice),
        )
        accepted.append(schedule_id)
        candidates.append(ScheduleCandidate(schedule_id, starts, True, None, objective))

    selected = min((c for c in candidates if c.feasible), key=lambda c: c.objective.sort_key)
    search = SearchSummary(
        job_order=tuple(job.job_id for job in jobs),
        windows=tuple((job.job_id, windows[job.job_id]) for job in jobs),
        total_assignments=len(candidates),
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        candidates=tuple(candidates),
    )
    chosen = dict(selected.starts)
    entries = list(lead_entries)
    entries += _explain_search(search, jobs)
    entries += _explain_selected(
        validated, jobs, chosen, base, selected, convention, job_score, fact_ids
    )
    unscheduled = tuple(job.job_id for job in jobs if chosen[job.job_id] is None)
    entries += _explain_unscheduled(validated, jobs, chosen, base, unscheduled)
    entries.append(_disposition_entry(state, jobs, chosen))

    plan = _build_plan(validated, jobs, chosen, selected, windows, base, fact_ids)
    return RulesV1Decision(
        status="proposed",
        plan=plan,
        fallback_reason=None,
        selected=selected,
        objective=selected.objective,
        search=search,
        arithmetic=tuple(entries),
        rule_ids=tuple(sorted({entry.rule_id for entry in entries} | {"R09"})),
        errors=(),
        unscheduled_job_ids=unscheduled,
        score_convention_id=convention.convention_id,
    )


# ----------------------------------------------------------------------------- explanations
def _explain_search(search: SearchSummary, jobs) -> list[ArithmeticEntry]:
    return [
        _entry(
            "R05",
            [
                _term("waiting_jobs", len(jobs), "jobs"),
                _term("start_slots_per_job_max", MAX_START_SLOTS, "slots"),
                _term("assignments_enumerated", search.total_assignments, "assignments"),
                _term("assignments_accepted_r04", len(search.accepted), "assignments"),
                _term("assignments_rejected_r04", len(search.rejected), "assignments"),
            ],
            outcome="pass",
            unit="assignments",
            formula="all assignments (each job: legal start slots plus unscheduled) <= 7**4 bound; "
            "none truncated or sampled",
            total=search.total_assignments,
            limit=MAX_ASSIGNMENTS,
        )
    ]


def _explain_selected(validated, jobs, chosen, base, selected, convention, job_score, fact_ids):
    state, snapshot = validated.state, validated.snapshot
    now, capacity = state.current_slot, validated.capacity
    deadline_ids = {
        job_id: c.constraint_id
        for c in snapshot.constraints_of("deadline")
        for job_id in c.applies_to_jobs
    }
    entries: list[ArithmeticEntry] = []
    scheduled = [job for job in jobs if chosen[job.job_id] is not None]
    for job in scheduled:
        start = chosen[job.job_id]
        end = start + job.duration_slots
        entries.append(
            _entry(
                "R02",
                [
                    _term("arrival_slot", job.arrival_slot, "slot", job.job_id),
                    _term("current_slot", now, "slot", job.job_id),
                    _term("start_slot", start, "slot", job.job_id),
                    _term("duration_slots", job.duration_slots, "slot", job.job_id),
                    _term("end_slot_exclusive", end, "slot", job.job_id),
                    _term("deadline_slot", job.deadline_slot, "slot", job.job_id),
                    _term("episode_end_slot", HORIZON, "slot", job.job_id),
                    _term("last_start_slot", LAST_DECISION_SLOT, "slot", job.job_id),
                ],
                outcome="pass",
                unit="slot",
                formula="max(now, arrival) <= start <= 23 and start + duration <= min(deadline, 30)",
                total=end,
                limit=min(job.deadline_slot, HORIZON),
                slot=start,
                cid=deadline_ids.get(job.job_id),
            )
        )
        if not job.flexible:
            entries.append(
                _entry(
                    "R03",
                    [
                        _term("start_slot", start, "slot", job.job_id),
                        _term("arrival_slot", job.arrival_slot, "slot", job.job_id),
                    ],
                    outcome="pass",
                    unit="slot",
                    formula="nonflexible job start == arrival (start - arrival must be 0)",
                    total=start,
                    limit=job.arrival_slot,
                    slot=start,
                )
            )
    started_ids = {r.job.job_id for r in state.running_jobs} | {
        c.job_id for c in state.completed_jobs
    }
    waiting_ids = {job.job_id for job in jobs}
    restarted = len(waiting_ids & started_ids)
    entries.append(
        _entry(
            "R03",
            [
                _term("selected_jobs", len(scheduled), "jobs"),
                _term("selected_already_running_or_completed", restarted, "jobs"),
                _term("running_or_completed_jobs", len(started_ids), "jobs"),
            ],
            outcome="pass",
            unit="jobs",
            formula="no duplicate or restarted job: selected-and-already-started count must be 0",
            total=restarted,
            limit=0,
        )
    )
    # R04: every occupied slot (running or selected work) of the selected schedule.
    selected_load = {t: [] for t in range(now, HORIZON)}
    for job in scheduled:
        for t in range(chosen[job.job_id], chosen[job.job_id] + job.duration_slots):
            selected_load[t].append(job)
    for t in range(now, HORIZON):
        running = [r.job for r in state.running_jobs if r.start_slot <= t < r.end_slot]
        if not running and not selected_load[t]:
            continue
        terms = [_term("background_kw", validated.background, "kW")]
        terms += [_term("running_kw", int(j.power_kw), "kW", j.job_id) for j in running]
        terms += [_term("selected_kw", int(j.power_kw), "kW", j.job_id) for j in selected_load[t]]
        total = sum(term.value for term in terms)
        entries.append(
            _entry(
                "R04",
                terms,
                outcome="pass" if total <= capacity else "fail",
                unit="kW",
                formula="background + running + selected IT load <= IT capacity (PUE not applied)",
                total=total,
                limit=capacity,
                slot=t,
                cid=validated.capacity_id,
            )
        )
    # R06 objective, one entry per lexicographic level.
    objective = selected.objective
    order = [job.job_id for job in jobs]
    entries += [
        _entry(
            "R06",
            [
                _term("scheduled", bit, "flag", jid)
                for jid, bit in zip(order, objective.inclusion_vector)
            ],
            outcome="computed",
            unit="jobs",
            formula="level 1: maximize number of scheduled jobs",
            total=objective.scheduled_count,
        ),
        _entry(
            "R06",
            [
                _term("included", bit, "flag", jid)
                for jid, bit in zip(order, objective.inclusion_vector)
            ],
            outcome="computed",
            unit="flag",
            formula="level 2: inclusion vector in priority order (nonflexible, earliest latest-start, "
            "earlier deadline, job ID), lexicographically larger is better",
        ),
    ]
    score_terms = []
    for job in scheduled:
        js = job_score[(job.job_id, chosen[job.job_id])]
        for term in js.terms:
            score_terms.append(
                _term(
                    f"{convention.convention_id}:slot{term.slot}:power{term.power_kw}*weight{term.weight}",
                    term.value,
                    convention.unit,
                    job.job_id,
                )
            )
    entries.append(
        _entry(
            "R06",
            score_terms,
            outcome="computed",
            unit=convention.unit,
            formula=f"level 3: minimize summed synthetic impact score; {convention.formula}; "
            f"{convention.status}",
            total=objective.synthetic_score,
        )
    )
    entries += [
        _entry(
            "R06",
            [
                _term(
                    "completion_slot", chosen[job.job_id] + job.duration_slots, "slot", job.job_id
                )
                for job in scheduled
            ],
            outcome="computed",
            unit="slot",
            formula="level 4: minimize sum of completion times (start + duration)",
            total=objective.completion_sum,
        ),
        _entry(
            "R06",
            [
                _term("start_slot_or_99_unscheduled", value, "slot", jid)
                for jid, value in zip(order, objective.start_vector)
            ],
            outcome="computed",
            unit="slot",
            formula="level 5: start vector in priority order, lexicographically smaller wins; "
            "unscheduled encoded 99 (after every legal start)",
        ),
    ]
    # R07: only starts equal to the current slot may execute; the rest are advisory.
    for job in scheduled:
        start = chosen[job.job_id]
        entries.append(
            _entry(
                "R07",
                [
                    _term("selected_start", start, "slot", job.job_id),
                    _term("current_slot", now, "slot", job.job_id),
                ],
                outcome="pass" if start == now else "computed",
                unit="slot",
                formula="start - current_slot == 0 executes after production recheck; "
                "> 0 is advisory and re-evaluated at its slot",
                total=start,
                limit=now,
                slot=start,
            )
        )
    return entries


def _explain_unscheduled(validated, jobs, chosen, base, unscheduled) -> list[ArithmeticEntry]:
    """Why each job is unscheduled: individual window failure, or the failed joint R04 sum."""
    state = validated.state
    now, capacity = state.current_slot, validated.capacity
    entries = []
    for job in jobs:
        if job.job_id not in unscheduled:
            continue
        window = legal_window(job, now)
        if not window:
            if not job.flexible and job.arrival_slot < now:
                entries.append(
                    _entry(
                        "R03",
                        [
                            _term("current_slot", now, "slot", job.job_id),
                            _term("arrival_slot", job.arrival_slot, "slot", job.job_id),
                        ],
                        outcome="fail",
                        unit="slot",
                        formula="nonflexible start must equal arrival; arrival is already past",
                        total=now,
                        limit=job.arrival_slot,
                    )
                )
            else:
                first = max(now, job.arrival_slot)
                end = first + job.duration_slots
                limit = min(job.deadline_slot, HORIZON, LAST_DECISION_SLOT + job.duration_slots)
                entries.append(
                    _entry(
                        "R02",
                        [
                            _term("earliest_start", first, "slot", job.job_id),
                            _term("duration_slots", job.duration_slots, "slot", job.job_id),
                            _term("deadline_slot", job.deadline_slot, "slot", job.job_id),
                        ],
                        outcome="fail",
                        unit="slot",
                        formula="earliest end must be <= min(deadline, 30, 23 + duration)",
                        total=end,
                        limit=limit,
                    )
                )
            continue
        start = window[0]
        extra = {t: [] for t in range(start, start + job.duration_slots)}
        for other in jobs:
            other_start = chosen[other.job_id]
            if other_start is None or other.job_id == job.job_id:
                continue
            for t in range(other_start, other_start + other.duration_slots):
                if t in extra:
                    extra[t].append(other)
        slot = next(
            (
                t
                for t in sorted(extra)
                if base[t] + sum(int(o.power_kw) for o in extra[t]) + int(job.power_kw) > capacity
            ),
            None,
        )
        if slot is None:
            slot = max(extra)  # window start fit; unscheduled only because a legal alternative won
        running = [r.job for r in state.running_jobs if r.start_slot <= slot < r.end_slot]
        terms = [_term("background_kw", validated.background, "kW")]
        terms += [_term("running_kw", int(j.power_kw), "kW", j.job_id) for j in running]
        terms += [_term("selected_kw", int(o.power_kw), "kW", o.job_id) for o in extra[slot]]
        terms.append(_term("excluded_candidate_kw", int(job.power_kw), "kW", job.job_id))
        total = sum(term.value for term in terms)
        # Filed under R05 (candidate enumeration/rejection), not R04: the merged trace reader
        # treats every R04 entry as the load of the stage's OWN plan, and this entry describes
        # a rejected candidate that is deliberately not that plan.
        entries.append(
            _entry(
                "R05",
                terms,
                outcome="pass" if total <= capacity else "fail",
                unit="kW",
                formula=f"rejected candidate (R04 capacity predicate): selected schedule plus "
                f"{job.job_id} at its earliest legal start {start}; "
                f"background + running + selected + candidate <= capacity",
                total=total,
                limit=capacity,
                slot=slot,
                cid=validated.capacity_id,
            )
        )
    return entries


def _disposition_entry(state, jobs, chosen) -> ArithmeticEntry:
    now = state.current_slot
    terms = []
    for job in jobs:
        start = chosen[job.job_id]
        label = (
            "waiting:unscheduled"
            if start is None
            else "waiting:start_now"
            if start == now
            else "waiting:advisory_future_start"
        )
        terms.append(_term(label, -1 if start is None else start, "slot", job.job_id))
    terms += [_term("running", len(state.running_jobs), "jobs")]
    terms += [_term("completed", len(state.completed_jobs), "jobs")]
    terms += [_term("missed", 1, "flag", jid) for jid in sorted(state.missed_job_ids)]
    return _entry(
        "R09",
        terms,
        outcome="computed",
        unit="slot",
        formula="waiting/unscheduled/missed/completed distinctions; -1 = unscheduled; a missed or "
        "unscheduled job is never reported completed",
    )


def _build_plan(validated, jobs, chosen, selected, windows, base, fact_ids) -> s.Plan:
    state = validated.state
    now = state.current_slot
    capacity_ids = (validated.capacity_id,)
    used_slots = {
        t
        for job in jobs
        if chosen[job.job_id] is not None
        for t in range(chosen[job.job_id], chosen[job.job_id] + job.duration_slots)
    }
    evidence = {validated.capacity_id, *(f"FACT-JOB-{job.job_id}" for job in jobs)}
    evidence |= {fact_ids[t] for t in used_slots if t in fact_ids}
    starts, abstentions = [], []
    for job in jobs:
        start = chosen[job.job_id]
        if start is not None:
            starts.append(s.PlannedStart(job_id=job.job_id, start_slot=start))
            continue
        individually = any(
            all(
                base[t] + int(job.power_kw) <= validated.capacity
                for t in range(w, w + job.duration_slots)
            )
            for w in windows[job.job_id]
        )
        if not windows[job.job_id]:
            reason, why = "infeasible_deadline", "no legal start (R02/R03) before deadline/slot 24"
        elif not individually:
            reason, why = "constraint_violation", "no individually capacity-feasible start (R04)"
        else:
            reason, why = (
                "constraint_violation",
                f"jointly excluded by R04/R05/R06 in schedule {selected.schedule_id}; the job fits "
                "alone, so this is not an individual physical certificate",
            )
        abstentions.append(
            s.Abstention(
                job_id=job.job_id,
                reason=reason,
                detail=f"rules-v1 unscheduled: {why}",
                evidence_ids=(f"FACT-JOB-{job.job_id}",),
                constraint_ids=capacity_ids,
            )
        )
    return s.Plan(
        episode_id=state.episode_id,
        slot=now,
        state_version=state.state_version,
        starts=tuple(starts),
        abstentions=tuple(abstentions),
        evidence_ids=tuple(sorted(evidence)),
        status="proposed",
    )


def explain_plan_capacity(
    state: s.VisibleState, snapshot: s.ConstraintSnapshot, plan: s.Plan
) -> tuple[ArithmeticEntry, ...]:
    """R04 arithmetic for any plan (for example an injected fault), one entry per occupied slot.

    Deterministic evidence only: it is not a verdict and never replaces the production check.
    Unknown jobs in the plan are ignored here (the production checker reports them).
    """
    capacities = snapshot.constraints_of("capacity")
    if not capacities or not _is_integral(capacities[0].limit_value):
        return ()
    capacity, capacity_id = int(capacities[0].limit_value), capacities[0].constraint_id
    waiting = {job.job_id: job for job in state.waiting_jobs}
    entries = []
    for t in range(state.current_slot, HORIZON):
        running = [r.job for r in state.running_jobs if r.start_slot <= t < r.end_slot]
        planned = [
            waiting[p.job_id]
            for p in plan.starts
            if p.job_id in waiting
            and p.start_slot <= t < p.start_slot + waiting[p.job_id].duration_slots
        ]
        if not running and not planned:
            continue
        terms = [_term("background_kw", int(state.site.background_kw), "kW")]
        terms += [_term("running_kw", int(j.power_kw), "kW", j.job_id) for j in running]
        terms += [_term("selected_kw", int(j.power_kw), "kW", j.job_id) for j in planned]
        total = sum(term.value for term in terms)
        entries.append(
            _entry(
                "R04",
                terms,
                outcome="pass" if total <= capacity else "fail",
                unit="kW",
                formula="background + running + all proposed IT load <= IT capacity (PUE not applied)",
                total=total,
                limit=capacity,
                slot=t,
                cid=capacity_id,
            )
        )
    return tuple(entries)
