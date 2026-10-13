"""Stable F02 example records for teammates to test against.

Everything here is the proposal's hand-calculated acceptance example (7 slots, J1/J2/J3),
a synthetic fixture. It is NOT SustainDC source data and makes no scientific claim: carbon
values are the proposal's shared-check series 500, 450, 300, 250, 400, 480, 520 g/kWh.
Semantics that the team has not resolved (Q05) are marked "unresolved"/"provisional".

Regenerate the committed JSON files with:  python -m tests.contracts.fixtures
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dc_sustainability import schemas as s

EXAMPLES_DIR = Path(__file__).parent / "examples"
SLOT0_UTC = datetime(2022, 1, 1, 7, tzinfo=timezone.utc)  # Phoenix midnight
HAND_CARBON = (500.0, 450.0, 300.0, 250.0, 400.0, 480.0, 520.0)
EPISODE_ID = "EP-HAND1"
SOURCE_ID = "SRC-HAND"


def source() -> s.SourceRef:
    """Return provenance for the team-authored synthetic hand-example fixtures."""
    return s.SourceRef(
        source_id=SOURCE_ID,
        path="tests/contracts/fixtures.py",
        redistribution_status="permitted",  # team-authored synthetic fixture
    )


def site(pue: float = 1.0) -> s.SiteConfig:
    """Build SITE1 with 40 kW background load, hourly slots, and the supplied PUE."""
    return s.SiteConfig(site_id="SITE1", background_kw=40, pue=pue, slot_hours=1)


def jobs() -> dict[str, s.Job]:
    """Return the three hand-example jobs, including J3 with an infeasible deadline."""
    return {
        "J1": s.Job(
            job_id="J1",
            arrival_slot=0,
            duration_slots=2,
            power_kw=40,
            deadline_slot=6,
            flexible=True,
        ),
        "J2": s.Job(
            job_id="J2",
            arrival_slot=0,
            duration_slots=2,
            power_kw=30,
            deadline_slot=6,
            flexible=True,
        ),
        # Structurally valid but infeasible: earliest finish is slot 7 > deadline 6.
        "J3": s.Job(
            job_id="J3",
            arrival_slot=4,
            duration_slots=3,
            power_kw=20,
            deadline_slot=6,
            flexible=True,
        ),
    }


def snapshot(
    capacity_kw: float = 100.0, include_capacity: bool = True, pue: float = 1.0
) -> s.ConstraintSnapshot:
    """Build hand-example constraints with optional capacity evidence and configurable site PUE."""
    cons = [
        s.Constraint(
            constraint_id="CON-FRESH-01",
            constraint_type="freshness",
            limit_value=2,
            unit="slot",
            applies_to_site="SITE1",
            source_id=SOURCE_ID,
        ),
        s.Constraint(
            constraint_id="CON-DL-J1",
            constraint_type="deadline",
            limit_value=6,
            unit="slot",
            applies_to_jobs=("J1",),
            source_id=SOURCE_ID,
        ),
        s.Constraint(
            constraint_id="CON-DL-J3",
            constraint_type="deadline",
            limit_value=6,
            unit="slot",
            applies_to_jobs=("J3",),
            source_id=SOURCE_ID,
        ),
    ]
    if include_capacity:
        cons.insert(
            0,
            s.Constraint(
                constraint_id="CON-CAP-01",
                constraint_type="capacity",
                limit_value=capacity_kw,
                unit="kW",
                applies_to_site="SITE1",
                source_id=SOURCE_ID,
            ),
        )
    return s.ConstraintSnapshot(
        snapshot_id="SNAP1", site=site(pue), constraints=tuple(cons), sources=(source(),)
    )


def semantics() -> s.CarbonSemantics:
    """Return explicitly unresolved carbon semantics with a provisional slot mapping."""
    return s.CarbonSemantics(
        pollutant_basis="unresolved",
        interval_convention="unresolved",
        emissions_factor_type="average",
        slot_mapping_status="provisional",
    )


def forecasts(issued_slot: int = 0) -> tuple[s.CarbonForecast, ...]:
    """Build seven perfect-foresight synthetic forecasts issued at the requested slot."""
    issued = SLOT0_UTC + timedelta(hours=issued_slot)
    return tuple(
        s.CarbonForecast(
            fact_id=f"FACT-CI-s{i:02d}",
            value=v,
            unit="g/kWh",
            source_id=SOURCE_ID,
            valid_slot=i,
            issued_at_utc=issued,
            forecast_kind="perfect_foresight",
            semantics=semantics(),
            quality_status="unvalidated",
        )
        for i, v in enumerate(HAND_CARBON)
    )


def observations() -> tuple[s.CarbonObservation, ...]:
    """Build seven private realized carbon observations from the synthetic hand series."""
    return tuple(
        s.CarbonObservation(
            fact_id=f"FACT-OBS-CI-s{i:02d}",
            value=v,
            unit="g/kWh",
            source_id=SOURCE_ID,
            observed_at_utc=SLOT0_UTC + timedelta(hours=i),
            valid_slot=i,
            semantics=semantics(),
            quality_status="unvalidated",
        )
        for i, v in enumerate(HAND_CARBON)
    )


def visible_state(
    snap: s.ConstraintSnapshot | None = None,
    *,
    current_slot: int = 0,
    waiting_job_ids: tuple[str, ...] = ("J1", "J2"),
    completed_job_ids: tuple[str, ...] = (),
    missed_job_ids: tuple[str, ...] = (),
) -> s.VisibleState:
    """Build a policy-visible state with projected constraints and only current/future forecasts."""
    snap = snap or snapshot()
    all_jobs = jobs()
    visible_end = min(
        current_slot + s.PROPOSED_DECISION_SLOTS,
        s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS,
    )
    visible_forecasts = tuple(
        fact for fact in forecasts() if current_slot <= fact.valid_slot < visible_end
    )
    return s.VisibleState.from_snapshot(
        snap,
        episode_id=EPISODE_ID,
        current_slot=current_slot,
        state_version=current_slot,
        waiting_jobs=tuple(all_jobs[job_id] for job_id in waiting_job_ids),
        completed_jobs=tuple(
            s.CompletedJobView(
                job_id=job_id,
                start_slot=0 if job_id == "J1" else 2,
                end_slot=2 if job_id == "J1" else 4,
            )
            for job_id in completed_job_ids
        ),
        missed_job_ids=missed_job_ids,
        carbon_facts=visible_forecasts,
    )


def plan(status: str = "proposed") -> s.Plan:
    """Hand-example run-as-soon-as-feasible plan: J2's slot-2 start is a future intention."""
    return s.Plan(
        episode_id=EPISODE_ID,
        slot=0,
        state_version=0,
        starts=(
            s.PlannedStart(job_id="J1", start_slot=0),
            s.PlannedStart(job_id="J2", start_slot=2),
        ),
        evidence_ids=("CON-CAP-01", "FACT-JOB-J1", "FACT-JOB-J2"),
        status=status,
    )


def abstention_plan() -> s.Plan:
    """Build a slot-4 proposal abstaining from J3 because of its infeasible deadline."""
    return s.Plan(
        episode_id=EPISODE_ID,
        slot=4,
        state_version=4,
        abstentions=(
            s.Abstention(job_id="J3", reason="infeasible_deadline", constraint_ids=("CON-DL-J3",)),
        ),
        status="proposed",
    )


def check_pass(p: s.Plan | None = None) -> s.CheckResult:
    """Build a synthetic passing result bound to the supplied plan and capacity evidence."""
    p = p or plan()
    return s.CheckResult(
        check_id="CHK-DEC-HAND1-00-1",
        episode_id=p.episode_id,
        slot=p.slot,
        state_version=p.state_version,
        plan_hash=p.plan_hash,
        status="pass",
        performed=tuple(
            s.PerformedCheck(
                name=n,
                outcome="pass",
                constraint_ids=("CON-CAP-01",) if n == "capacity" else (),
            )
            for n in ("schema", "ids", "timing", "deadline", "nonflexible", "capacity")
        ),
        evidence=(
            s.EvidenceItem(kind="capacity", status="available", ids=("CON-CAP-01",)),
            s.EvidenceItem(kind="carbon", status="available"),
        ),
        impact_claim_support="supported",
    )


def check_missing_capacity(p: s.Plan | None = None) -> s.CheckResult:
    """Build an error result for the supplied plan with missing capacity evidence."""
    p = p or plan()
    return s.CheckResult(
        check_id="CHK-DEC-HAND1-00-2",
        episode_id=p.episode_id,
        slot=p.slot,
        state_version=p.state_version,
        plan_hash=p.plan_hash,
        status="error",
        skipped=(s.SkippedCheck(name="capacity", reason="no capacity constraint available"),),
        evidence=(s.EvidenceItem(kind="capacity", status="missing"),),
        impact_claim_support="not_assessed",
        errors=("missing capacity evidence",),
    )


def approved_actions() -> s.ApprovedActions:
    """Derive the hand plan's current-slot actions from its synthetic passing check."""
    return s.ApprovedActions.from_checked_plan(
        plan("approved"), check_pass(), expected_state_version=0
    )


def decision_record() -> s.DecisionRecord:
    """Build an executed greedy-A trace for J1 with checked stages and no model calls."""
    p, chk = plan(), check_pass()
    return s.DecisionRecord(
        decision_id="DEC-HAND1-00",
        system="greedy_a",
        run_id="RUN-HAND",
        episode_id=EPISODE_ID,
        slot=0,
        initial=s.StageRecord(plan=p, check=chk),
        not_applicable_stages=("repaired", "fallback"),
        execution_check=chk,
        final_status="executed",
        executed_starts=(s.ApprovedStart(job_id="J1", start_slot=0),),
        evidence_ids=("CON-CAP-01",),
        model_call_count=0,
        repair_count=0,
    )


def solver_result() -> s.SolverResult:
    """Return the hand-enumerated optimal reference schedule for J1 and J2."""
    return s.SolverResult(
        solver_result_id="SOLVE-HAND-1",
        kind="visible",
        uses_future_arrivals=False,
        input_hash="0" * 64,
        status="certified_optimal",
        backend="hand-enumeration",
        backend_version="n/a",
        elapsed_s=0.0,
        termination="exhaustive enumeration",
        objective_kg=48.4,
        certification_basis="exhaustive enumeration of 12 feasible pairs",
        schedule=(
            s.PlannedStart(job_id="J1", start_slot=2),
            s.PlannedStart(job_id="J2", start_slot=4),
        ),
        matching_work_job_ids=("J1", "J2"),
    )


def episode_result() -> s.EpisodeResult:
    """Build a 30-slot synthetic episode result with completed work and uncomputed totals."""
    load = {0: 40.0, 1: 40.0, 2: 30.0, 3: 30.0}
    return s.EpisodeResult(
        episode_id=EPISODE_ID,
        run_id="RUN-HAND",
        system="greedy_a",
        n_decision_slots=24,
        n_completion_slots=6,
        slots=tuple(
            s.SlotRecord(
                slot=i,
                phase="decision" if i < 24 else "completion",
                job_load_kw=load.get(i, 0.0),
                background_load_kw=40.0,
            )
            for i in range(30)
        ),
        totals=s.EpisodeTotals(),
        job_count_total=2,
        completed_job_ids=("J1", "J2"),
        completed_work=s.CompletedWork(
            value=140.0, unit="kWh", definition="IT job energy of jobs run to completion (example)"
        ),
    )


def private_episode() -> s.PrivateEpisode:
    """Build the private synthetic manifest with jobs, generator metadata, and observations."""
    return s.PrivateEpisode(
        episode_id=EPISODE_ID,
        scenario_id="hand-example",
        split="development",
        seed=0,
        n_decision_slots=24,
        n_completion_slots=6,
        snapshot=snapshot(),
        jobs=tuple(
            s.PrivateJob(
                job=job,
                scenario_id="hand-example",
                split="development",
                seed=0,
                synthetic=True,
                intentionally_infeasible=(job.job_id == "J3"),
            )
            for job in jobs().values()
        ),
        realized_carbon=observations(),
        forecast_visibility="perfect_foresight",
    )


def policy_output() -> s.PolicyOutput:
    """Wrap the hand plan in a greedy-A output with a template explanation and claim."""
    return s.PolicyOutput(
        system="greedy_a",
        output_status="ok",
        plan=plan(),
        explanation=s.Explanation(
            source="template",
            summary="J1 starts now; J2 is a future intention.",
            claims=(
                s.Claim(
                    claim_id="C1",
                    text="Hand-example job energy.",
                    evidence_ids=("FACT-JOB-J1",),
                    value=140.0,
                    unit="kWh",
                ),
            ),
            limitations=("Hand fixture; perfect-foresight forecast.",),
        ),
    )


def build_examples() -> dict[str, s.Record]:
    """Return named synthetic records used to generate and validate committed JSON examples."""
    snap = snapshot()
    state = visible_state(snap)
    j = jobs()
    return {
        "job": j["J1"],
        "job_infeasible_but_valid": j["J3"],
        "constraint_snapshot": snap,
        "carbon_forecast": forecasts()[0],
        "carbon_observation_private": observations()[0],
        "visible_state": state,
        "context_flat": s.Context.build(state, snap, "flat"),
        "plan": plan(),
        "plan_abstention": abstention_plan(),
        "policy_output": policy_output(),
        "check_result_pass": check_pass(),
        "check_result_missing_capacity": check_missing_capacity(),
        "approved_actions": approved_actions(),
        "decision_record": decision_record(),
        "solver_result": solver_result(),
        "episode_result": episode_result(),
        "private_episode": private_episode(),
    }


def main() -> None:
    """Write all synthetic example records as sorted, indented JSON files in EXAMPLES_DIR."""
    EXAMPLES_DIR.mkdir(exist_ok=True)
    for name, rec in build_examples().items():
        (EXAMPLES_DIR / f"{name}.json").write_text(
            json.dumps(rec.to_jsonable(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"wrote {len(build_examples())} examples to {EXAMPLES_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
