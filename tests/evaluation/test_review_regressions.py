"""Hand-derived review regressions over synthetic inputs, never model outputs.

No production checker, simulator or shared impact implementation establishes truth.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import claims as c
from dc_sustainability.evaluation import validator as v
from tests.contracts import fixtures as f


def evaluate(plan, state=None, snapshot=None):
    snapshot = snapshot or f.snapshot()
    state = state or f.visible_state(snapshot)
    return v.validate_plan(plan, v.facts_from_state(state, snapshot), v.Q03_DRAFT)


def test_any_capacity_excess_is_invalid_without_an_agreed_margin():
    # 40 background + 40 J1 + 20.0000000001 EPS > 100, only at slot 2.
    epsilon = s.Job(
        job_id="EPS",
        arrival_slot=0,
        duration_slots=1,
        power_kw=20.0000000001,
        deadline_slot=6,
        flexible=True,
    )
    state = f.visible_state().model_copy(update={"waiting_jobs": (f.jobs()["J1"], epsilon)})
    plan = f.plan().model_copy(
        update={
            "starts": (
                s.PlannedStart(job_id="J1", start_slot=2),
                s.PlannedStart(job_id="EPS", start_slot=2),
            )
        }
    )
    result = evaluate(plan, state)
    assert result.status == "invalid"
    assert [(x.code, x.slot) for x in result.findings] == [("capacity", 2)]


def test_tiny_physical_excess_can_justify_abstention():
    # Capacity is slightly below the 80 kW needed by J1 at every legal start.
    snapshot = f.snapshot(capacity_kw=79.9999999999)
    state = f.visible_state(snapshot).model_copy(update={"waiting_jobs": (f.jobs()["J1"],)})
    plan = f.plan().model_copy(
        update={
            "starts": (),
            "abstentions": (s.Abstention(job_id="J1", reason="constraint_violation"),),
        }
    )
    result = evaluate(plan, state, snapshot)
    assert result.valid and result.justified_abstentions == ("J1",)


@pytest.mark.parametrize("kind,limit", [("arrival", 1), ("nonflexible", 0)])
def test_contradictory_authoritative_job_facts_are_refused(kind, limit):
    extra = s.Constraint(
        constraint_id="CON-CONFLICT",
        constraint_type=kind,
        limit_value=limit,
        unit="slot",
        applies_to_jobs=("J1",),
        source_id=f.SOURCE_ID,
    )
    snapshot = f.snapshot().model_copy(update={"constraints": f.snapshot().constraints + (extra,)})
    state = f.visible_state(snapshot)
    with pytest.raises(ValueError, match="contradict"):
        v.facts_from_state(state, snapshot)


def test_wrong_nonflexible_start_slot_is_refused():
    fixed = f.jobs()["J1"].model_copy(update={"flexible": False})
    extra = s.Constraint(
        constraint_id="CON-FIXED",
        constraint_type="nonflexible",
        limit_value=1,
        unit="slot",
        applies_to_jobs=("J1",),
        source_id=f.SOURCE_ID,
    )
    snapshot = f.snapshot().model_copy(update={"constraints": f.snapshot().constraints + (extra,)})
    state = f.visible_state(snapshot).model_copy(update={"waiting_jobs": (fixed,)})
    with pytest.raises(ValueError, match="contradict"):
        v.facts_from_state(state, snapshot)


@pytest.mark.parametrize("ids", [(), ("CON-MADE-UP",)])
def test_state_cannot_hide_or_invent_visible_constraint_ids(ids):
    state = f.visible_state().model_copy(update={"constraint_ids": ids})
    with pytest.raises(ValueError, match="constraint IDs"):
        v.facts_from_state(state, f.snapshot())


def test_duplicate_jobs_are_not_silently_collapsed_to_a_valid_state():
    state = f.visible_state().model_copy(update={"waiting_jobs": (f.jobs()["J1"],) * 2})
    with pytest.raises(ValueError):
        v.facts_from_state(state, f.snapshot())


def test_invalid_snapshot_cannot_create_unlimited_or_nonfinite_capacity():
    snapshot = f.snapshot()
    capacity = snapshot.constraints[0].model_copy(update={"limit_value": float("nan")})
    bad = snapshot.model_copy(update={"constraints": (capacity,) + snapshot.constraints[1:]})
    with pytest.raises(ValueError):
        v.facts_from_state(f.visible_state(), bad)


@pytest.mark.parametrize("start", [-1, True, 0.5])
def test_bypassed_plan_schema_is_refused(start):
    original = f.plan()
    bad_start = original.starts[0].model_copy(update={"start_slot": start})
    malformed = original.model_copy(update={"starts": (bad_start,) + original.starts[1:]})
    with pytest.raises(ValueError):
        evaluate(malformed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("episode_id", "EP-OTHER"),
        ("slot", 1),
        ("state_version", 1),
        ("plan_hash", "a" * 64),
    ],
)
def test_check_for_another_decision_is_not_reported_as_agreement(field, value):
    result = evaluate(f.plan())
    wrong_check = f.check_pass().model_copy(update={field: value})
    assert v.compare_with_check(result, wrong_check) == "not_comparable"


@pytest.mark.parametrize(
    "value,reference,expected",
    [
        (0.55, 0.5, "correct"),
        (0.45, 0.5, "correct"),
        (0.5500000001, 0.5, "incorrect"),
        (0.4499999999, 0.5, "incorrect"),
    ],
)
def test_claim_boundary_has_no_extra_tolerance(value, reference, expected):
    claim = s.Claim(claim_id="C-BOUNDARY", text="Synthetic claim", value=value, unit="kg")
    assert c.score_numeric_claim(claim, reference, "kg").status == expected


@pytest.mark.parametrize("reference", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_claim_reference_is_unavailable(reference):
    claim = s.Claim(claim_id="C-REF", text="Synthetic claim", value=1.0, unit="kg")
    result = c.score_numeric_claim(claim, reference, "kg")
    assert result.status == "reference_unavailable"
    assert result.reference is None and result.abs_error is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0])
def test_invalid_carbon_mapping_cannot_produce_reference_emissions(value):
    with pytest.raises(ValueError):
        c.job_emissions_kg(f.jobs()["J1"], 0, f.site(), {0: value, 1: 500.0})


@pytest.mark.parametrize("candidate,baseline", [(float("nan"), 1.0), (1.0, float("inf"))])
def test_nonfinite_emissions_never_become_comparable_savings(candidate, baseline):
    with pytest.raises(ValueError):
        c.compare_emissions(("J1",), candidate, ("J1",), baseline, same_horizon_and_inputs=True)
