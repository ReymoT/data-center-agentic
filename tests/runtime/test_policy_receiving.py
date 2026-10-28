"""Real deterministic-policy receiving; synthetic facts and no model calls."""

from datetime import timedelta

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.knowledge import retrieve
from dc_sustainability.policies import propose
from dc_sustainability.runtime import ExecutionController, TraceStore, execute_policy_output
from dc_sustainability.simulator import SchedulingSimulator
from tests.contracts import fixtures as f
from tests.simulator.test_core import episode


def setup(tmp_path, *, withheld=False):
    ep = episode((f.jobs()["J1"], f.jobs()["J2"]), withheld=withheld)
    sim = SchedulingSimulator(allow_completion_starts=False)
    forecast_map = (
        {}
        if withheld
        else {
            slot: tuple(fact for fact in f.forecasts(issued_slot=slot) if fact.valid_slot >= slot)
            for slot in range(30)
        }
    )
    sim.reset(ep, forecasts_by_slot=forecast_map)
    store = TraceStore(tmp_path / "traces")
    return ep, sim, store, ExecutionController(sim, lambda: ep.snapshot, store)


@pytest.mark.parametrize(
    "requested,withheld,effective,stage",
    [
        ("greedy_a", False, "greedy_a", "initial"),
        ("greedy_b", False, "greedy_b", "initial"),
        ("greedy_b", True, "greedy_a", "fallback"),
    ],
)
def test_actual_policy_output_reaches_checked_controller(
    tmp_path, requested, withheld, effective, stage
):
    ep, sim, store, controller = setup(tmp_path, withheld=withheld)
    view = sim.state()
    output = propose(
        view,
        retrieve(view, ep.snapshot).context,
        system=requested,
        decision_time_utc=f.SLOT0_UTC if requested == "greedy_b" else None,
    )
    assert output.system == effective
    result = execute_policy_output(
        controller,
        output,
        view,
        ep.snapshot,
        requested_system=requested,
        decision_id="DEC-POLICY-0",
        run_id="RUN-POLICY",
        trial=0,
    )
    record = result.record
    assert record.system == requested and record.final_status == "executed"
    assert record.execution_check.status == "pass"
    assert getattr(record, stage).check.status == "pass"
    assert store.read(record.decision_id) == record
    assert sim.state().current_slot == 1


def test_unsuccessful_policy_output_is_recorded_and_advances_once(tmp_path):
    ep, sim, store, controller = setup(tmp_path)
    view = sim.state()
    output = s.PolicyOutput(system="greedy_a", output_status="error", raw_response="retained")
    result = execute_policy_output(
        controller,
        output,
        view,
        ep.snapshot,
        requested_system="greedy_a",
        decision_id="DEC-ERROR-0",
        run_id="RUN-ERROR",
    )
    record = result.record
    assert record.final_status == "blocked" and record.raw_response == "retained"
    assert record.errors == (
        "policy output status: error",
        "no selected actually passing proposal check",
        "simulator refusal: requires runtime-approved ApprovedActions",
    )
    assert store.read(record.decision_id) == record
    assert sim.state().current_slot == 1


def test_mismatched_effective_policy_is_refused_before_mutation(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    view = sim.state()
    output = propose(view, retrieve(view, ep.snapshot).context)
    with pytest.raises(ValueError, match="does not match"):
        execute_policy_output(
            controller,
            output,
            view,
            ep.snapshot,
            requested_system="decision_tree_c",
            decision_id="DEC-MISMATCH-0",
            run_id="RUN-MISMATCH",
        )
    assert sim.state().current_slot == 0


def test_greedy_b_decision_time_stays_an_explicit_policy_input(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    view = sim.state()
    context = retrieve(view, ep.snapshot).context
    with pytest.raises(ValueError, match="trusted UTC"):
        propose(view, context, system="greedy_b")
    assert sim.state().current_slot == 0
    output = propose(
        view,
        context,
        system="greedy_b",
        decision_time_utc=f.SLOT0_UTC + timedelta(hours=view.current_slot),
    )
    assert output.output_status == "ok"
