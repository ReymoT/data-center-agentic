"""Actual A03/E01 consumer comparison on hand-derived synthetic cases.

The production checker is exercised here, never imported by the independent
validator. Neither implementation supplies the expected arithmetic or verdict.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import validator as v
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as f


@pytest.mark.parametrize(
    "j2_power,capacity,overlap,expected_capacity,expected_independent",
    [
        (30.0, 100.0, False, "pass", "valid"),  # 80 then 70 kW
        (30.0, 100.0, True, "fail", "invalid"),  # future 110 kW
        (20.0, 100.0, True, "pass", "valid"),  # exact 100 before PUE 1.2
        (20.0000000001, 100.0, True, "fail", "invalid"),
        (30.0, 70.0, False, "fail", "invalid"),  # J1 alone exceeds 70
    ],
)
def test_current_checker_and_independent_capacity_agree(
    j2_power, capacity, overlap, expected_capacity, expected_independent
):
    snapshot = f.snapshot(capacity_kw=capacity, pue=1.2)
    j2 = f.jobs()["J2"].model_copy(update={"power_kw": j2_power})
    state = s.VisibleState.from_snapshot(
        snapshot,
        episode_id=f.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=(f.jobs()["J1"], j2),
    )
    plan = s.Plan(
        episode_id=f.EPISODE_ID,
        slot=0,
        state_version=0,
        starts=(
            s.PlannedStart(job_id="J1", start_slot=2 if overlap else 0),
            s.PlannedStart(job_id="J2", start_slot=2),
        ),
        status="proposed",
    )
    production = check_schedule(plan, state, snapshot)
    reference = v.validate_plan(plan, v.facts_from_state(state, snapshot), v.Q03_DRAFT)
    assert (
        next(c.outcome for c in production.performed if c.name == "capacity") == expected_capacity
    )
    assert reference.status == expected_independent
    if expected_capacity == "fail":
        assert production.status == "fail"
        assert v.compare_with_check(reference, production) == "agree"
    else:
        # Do not manufacture overall approval while Q02/Q03 are still unresolved.
        assert production.status == "error"
        assert v.compare_with_check(reference, production) == "not_comparable"
