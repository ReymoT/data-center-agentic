"""RULE-04: deterministic synthetic case generator for the rule-system study (#242).

Implements the review-2 generator in docs/rule_study/RULE01_SPECIFICATION.md exactly as
accepted in #239 (issuecomment-7052918378). Standard library only. It imports no
scheduler, checker, policy, simulator or the RULE-03 verifier: the feasibility label is
this module's own claim, and Nisha's case checker recomputes it independently.

Draw order, per seed domain (one ``random.Random``, every draw a ``choice``):

- strata in the order ``normal_feasible``, ``overloaded_impossible``, ``missing_forecast``,
  accepted case indices 0-39 in each;
- per proposal: job count; then for J1..Jn power, duration, arrival, flexible, slack, with
  ``deadline = min(6, arrival + duration + slack)``; then six scores for slots 0-5 (slots
  6-29 use the drain score 200);
- overload proposals draw J1/J2 like any job, then replace them with the fixed immediate
  nonflexible 30 kW pair, so the random stream does not depend on the stratum's rules.

Acceptance: normal and missing-forecast proposals need joint feasibility, at least one
flexible job and a nonconstant slot 0-5 profile; overload proposals need joint
infeasibility. A repeated full-case identity or an authored example (A, B, B-progress)
counts as a rejected attempt and is redrawn; final-domain proposals also reject any
development case. Each stratum stops after 10,000 attempts.

Outputs are two separate objects: the policy-visible case set (the shape the RULE-03
case checker reads; missing-forecast scores are null) and an evaluator-only accounting
file with every case's synthetic weights. Policies must only ever receive the first.
Scores are artificial weights, not g/kWh or emissions.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

RECORD_KIND = "rule_study_case_set_v1"
ACCOUNTING_RECORD_KIND = "rule_study_accounting_weights_v1"
GENERATOR_VERSION = "rule04-generator-v1"
STUDY_ID = "rule-study-20261119-v1"
SUPPORTED_SPEC_SHA256 = "9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd"
SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "rule_study" / "specification.json"

SEED_DOMAINS = {"development": 2026111901, "final": 2026111902}
STRATA = ("normal_feasible", "overloaded_impossible", "missing_forecast")
CASES_PER_STRATUM = 40
MAX_ATTEMPTS_PER_STRATUM = 10_000

CAPACITY_KW = 60
BACKGROUND_KW = 20
HORIZON = 30
LAST_START_SLOT = 23
AUTHORED_SLOTS = 6
DRAIN_SCORE = 200
MAX_DEADLINE = 6

JOB_COUNTS = {
    "normal_feasible": (2, 3, 4),
    "overloaded_impossible": (3, 4),
    "missing_forecast": (2, 3, 4),
}
POWERS = (10, 20, 30)
DURATIONS = (1, 2)
ARRIVALS = (0, 1, 2)
FLEXIBLE = (False, True)
SLACKS = (0, 1, 2)
SCORES = (100, 200, 300)

AUTHORIZATION_PATTERN = re.compile(
    r"^https://github\.com/ReymoT/data-center-agentic/(issues|pull)/\d+#issuecomment-\d+$"
)


@dataclass(frozen=True)
class Job:
    job_id: str
    power_kw: int
    duration_slots: int
    arrival_slot: int
    deadline_slot: int
    flexible: bool

    def legal_starts(self) -> range:
        """Starts a full-knowledge schedule may use: before slot 24, ending by the deadline."""
        latest = min(self.deadline_slot - self.duration_slots, LAST_START_SLOT)
        if not self.flexible:
            return range(
                self.arrival_slot, self.arrival_slot + 1 if self.arrival_slot <= latest else 0
            )
        return range(self.arrival_slot, latest + 1)

    def as_list(self) -> list:
        return [
            self.job_id,
            self.power_kw,
            self.duration_slots,
            self.arrival_slot,
            self.deadline_slot,
            self.flexible,
        ]

    def as_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "power_kw": self.power_kw,
            "duration_slots": self.duration_slots,
            "arrival_slot": self.arrival_slot,
            "deadline_slot": self.deadline_slot,
            "flexible": self.flexible,
        }


CONFLICT_PAIR = (Job("J1", 30, 1, 0, 1, False), Job("J2", 30, 1, 0, 1, False))


@dataclass(frozen=True)
class Proposal:
    jobs: tuple[Job, ...]
    weights: tuple[int, ...]  # all 30 slots: the perfect artificial forecast and accounting weights


# --- Identity ------------------------------------------------------------------------------


def canonical_sha256(value) -> str:
    """Adapter proposal-1 convention: sorted keys, compact separators, one final LF."""
    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256((text + "\n").encode("utf-8")).hexdigest()


def workload_identity(jobs: tuple[Job, ...], capacity_kw: int, background_kw: int) -> dict:
    return {
        "capacity_kw": capacity_kw,
        "background_kw": background_kw,
        "horizon": HORIZON,
        "jobs": [j.as_list() for j in sorted(jobs, key=lambda j: j.job_id)],
    }


def full_case_identity(
    jobs: tuple[Job, ...], capacity_kw: int, background_kw: int, scores: tuple[int, ...] | None
) -> dict:
    identity = workload_identity(jobs, capacity_kw, background_kw)
    return {**identity, "scores": None if scores is None else list(scores)}


def source_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# --- Feasibility ---------------------------------------------------------------------------


def jointly_feasible(jobs: tuple[Job, ...], capacity_kw: int, background_kw: int) -> bool:
    """True if some assignment completes every job within capacity, knowing all arrivals."""
    for starts in itertools.product(*(job.legal_starts() for job in jobs)):
        load = [background_kw] * HORIZON
        for job, start in zip(jobs, starts):
            for slot in range(start, start + job.duration_slots):
                load[slot] += job.power_kw
        if max(load) <= capacity_kw:
            return True
    return False


# --- Drawing -------------------------------------------------------------------------------


def draw_proposal(rng: random.Random, stratum: str) -> Proposal:
    count = rng.choice(JOB_COUNTS[stratum])
    jobs = []
    for index in range(1, count + 1):
        power = rng.choice(POWERS)
        duration = rng.choice(DURATIONS)
        arrival = rng.choice(ARRIVALS)
        flexible = rng.choice(FLEXIBLE)
        slack = rng.choice(SLACKS)
        deadline = min(MAX_DEADLINE, arrival + duration + slack)
        jobs.append(Job(f"J{index}", power, duration, arrival, deadline, flexible))
    head = tuple(rng.choice(SCORES) for _ in range(AUTHORED_SLOTS))
    if stratum == "overloaded_impossible":
        jobs[0], jobs[1] = CONFLICT_PAIR
    return Proposal(tuple(jobs), head + (DRAIN_SCORE,) * (HORIZON - AUTHORED_SLOTS))


def rejection_reason(proposal: Proposal, stratum: str) -> str | None:
    """Stratum acceptance predicate; None means the proposal is accepted."""
    feasible = jointly_feasible(proposal.jobs, CAPACITY_KW, BACKGROUND_KW)
    if stratum == "overloaded_impossible":
        return "jointly_feasible" if feasible else None
    if not feasible:
        return "jointly_infeasible"
    if not any(job.flexible for job in proposal.jobs):
        return "no_flexible_job"
    if len(set(proposal.weights[:AUTHORED_SLOTS])) == 1:
        return "constant_profile"
    return None


def visible_scores(proposal: Proposal, stratum: str) -> tuple[int, ...] | None:
    return None if stratum == "missing_forecast" else proposal.weights


# --- Specification -------------------------------------------------------------------------


def load_specification(path: Path = SPEC_PATH) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    if canonical_sha256(spec) != SUPPORTED_SPEC_SHA256:
        raise ValueError("unsupported specification revision; review generator assumptions first")
    return spec


def authored_full_identities(spec: Mapping) -> set[str]:
    """Full-case hashes of authored cases A, B and B-progress (fault injection shares B's)."""
    out = set()
    for scenario in spec["scenarios"]:
        jobs = tuple(
            Job(
                j["job_id"],
                j["power_kw"],
                j["duration_slots"],
                j["arrival_slot"],
                j["deadline_slot"],
                j["flexible"],
            )
            for j in scenario["jobs"]
        )
        first = tuple(scenario["first_scores"])
        profile = first + (scenario["remaining_score"],) * (HORIZON - len(first))
        cap, bg = scenario["capacity_kw"], scenario["background_kw"]
        out.add(canonical_sha256(full_case_identity(jobs, cap, bg, profile)))
        sub = scenario.get("feasible_progress_subcase")
        if sub:
            changed = tuple(
                Job(
                    j.job_id,
                    j.power_kw,
                    j.duration_slots,
                    j.arrival_slot,
                    sub["deadline_slot"],
                    sub["flexible"],
                )
                if j.job_id == sub["change_job"]
                else j
                for j in jobs
            )
            out.add(canonical_sha256(full_case_identity(changed, cap, bg, profile)))
    return out


# --- Generation ----------------------------------------------------------------------------


@dataclass(frozen=True)
class _Accepted:
    stratum: str
    index: int
    attempt: int
    proposal: Proposal
    full_sha256: str
    workload_sha256: str


def _generate(
    domain: str,
    authored: set[str],
    excluded: set[str],
    *,
    per_stratum: int = CASES_PER_STRATUM,
    max_attempts: int = MAX_ATTEMPTS_PER_STRATUM,
) -> tuple[list[_Accepted], dict]:
    rng = random.Random(SEED_DOMAINS[domain])
    accepted: list[_Accepted] = []
    report = {}
    for stratum in STRATA:
        seen: set[str] = set()
        rejected: Counter = Counter()
        attempts = 0
        cases: list[_Accepted] = []
        while len(cases) < per_stratum:
            if attempts >= max_attempts:
                raise RuntimeError(
                    f"{domain}/{stratum}: only {len(cases)} of {per_stratum} cases accepted "
                    f"within {max_attempts} attempts"
                )
            attempts += 1
            proposal = draw_proposal(rng, stratum)
            scores = visible_scores(proposal, stratum)
            full = canonical_sha256(
                full_case_identity(proposal.jobs, CAPACITY_KW, BACKGROUND_KW, scores)
            )
            reason = rejection_reason(proposal, stratum)
            if reason is None and full in seen:
                reason = "duplicate_full_case"
            if reason is None and full in authored:
                reason = "authored_overlap"
            if reason is None and full in excluded:
                reason = "development_overlap"
            if reason is not None:
                rejected[reason] += 1
                continue
            seen.add(full)
            workload = canonical_sha256(
                workload_identity(proposal.jobs, CAPACITY_KW, BACKGROUND_KW)
            )
            cases.append(_Accepted(stratum, len(cases), attempts, proposal, full, workload))
        report[stratum] = {
            "accepted": len(cases),
            "attempts": attempts,
            "rejected": dict(sorted(rejected.items())),
            "distinct_full_case_hashes": len({c.full_sha256 for c in cases}),
            "distinct_workload_hashes": len({c.workload_sha256 for c in cases}),
        }
        accepted.extend(cases)
    return accepted, report


def generate(
    domain: str,
    *,
    authorization: str | None = None,
    spec: Mapping | None = None,
    per_stratum: int = CASES_PER_STRATUM,
    max_attempts: int = MAX_ATTEMPTS_PER_STRATUM,
) -> tuple[dict, dict]:
    """Return (policy-visible case set, evaluator-only accounting weights) for a seed domain.

    The final domain needs an explicit issue-comment authorization reference. It is recorded,
    not verified: it does not itself grant approval.
    """
    if domain not in SEED_DOMAINS:
        raise ValueError(f"unknown seed domain {domain!r}")
    if domain == "final":
        if not isinstance(authorization, str) or not AUTHORIZATION_PATTERN.match(authorization):
            raise PermissionError(
                "final-domain generation needs --authorization with the approving issue comment URL"
            )
    elif authorization is not None:
        raise ValueError("authorization applies only to the final domain")
    spec = load_specification() if spec is None else spec
    if canonical_sha256(spec) != SUPPORTED_SPEC_SHA256:
        raise ValueError("unsupported specification revision; review generator assumptions first")
    authored = authored_full_identities(spec)
    excluded: set[str] = set()
    if domain == "final":
        development, _ = _generate(
            "development", authored, set(), per_stratum=per_stratum, max_attempts=max_attempts
        )
        excluded = {c.full_sha256 for c in development}
    accepted, report = _generate(
        domain, authored, excluded, per_stratum=per_stratum, max_attempts=max_attempts
    )

    set_id = f"{STUDY_ID}-{domain}"
    cases, weights = [], []
    for item in accepted:
        case_id = f"{domain}-{item.stratum}-{item.index:02d}"
        scores = visible_scores(item.proposal, item.stratum)
        label = (
            "jointly_infeasible" if item.stratum == "overloaded_impossible" else "jointly_feasible"
        )
        cases.append(
            {
                "case_id": case_id,
                "capacity_kw": CAPACITY_KW,
                "background_kw": BACKGROUND_KW,
                "jobs": [j.as_dict() for j in item.proposal.jobs],
                "scores": None if scores is None else list(scores),
                "stratum": item.stratum,
                "feasibility_label": label,
                "generator_attempt": item.attempt,
            }
        )
        weights.append(
            {
                "case_id": case_id,
                "full_case_sha256": item.full_sha256,
                "workload_sha256": item.workload_sha256,
                "weights": list(item.proposal.weights),
                "weights_visible_to_policy": scores is not None,
            }
        )
    case_set = {
        "set_id": set_id,
        "cases": cases,
        "metadata": {
            "record_kind": RECORD_KIND,
            "generator_version": GENERATOR_VERSION,
            "generator_source_sha256": source_sha256(),
            "spec_sha256": SUPPORTED_SPEC_SHA256,
            "seed_domain": domain,
            "seed": SEED_DOMAINS[domain],
            "authorization": authorization,
            "per_stratum": per_stratum,
            "max_attempts_per_stratum": max_attempts,
            "report": report,
            "units": "artificial score weights; not g/kWh, not emissions",
            "labels": "generator claims; independent check is RULE-03's case checker",
        },
    }
    accounting = {
        "record_kind": ACCOUNTING_RECORD_KIND,
        "set_id": set_id,
        "case_set_sha256": canonical_sha256(case_set),
        "generator_source_sha256": case_set["metadata"]["generator_source_sha256"],
        "visibility": "evaluator-only; never supply to a policy",
        "units": "artificial score weights per slot; impact = power_kW x 1 h x PUE 1.0 x weight (score-kWh)",
        "cases": weights,
    }
    return case_set, accounting


def dumps(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
