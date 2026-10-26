"""E01 hand-truth tests for independent episode replay.

Expected states and outcomes are worked out by hand from the shared timing rules (site
40 kW background, 100 kW capacity; J1 40 kW x 2 and J2 30 kW x 2 arrive at 0 with
deadline 6; J3 20 kW x 3 arrives at 4 with deadline 6, so it is impossible on arrival).
Only the last test runs the S01 simulator, as a consumer check, never as truth.
"""

import ast
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data.scenarios import SCENARIOS, generate_jobs
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation import validator as v
from dc_sustainability.evaluation.validator import Q03_DRAFT, Q03_OPTION_B
from dc_sustainability.simulator import SchedulingSimulator
from tests.contracts import fixtures as f


def starts(**by_slot):
    """starts(s0=["J1"], s2=["J2"]) -> {0: (J1@0,), 2: (J2@2,)}"""
    return {
        int(key[1:]): tuple(s.ApprovedStart(job_id=j, start_slot=int(key[1:])) for j in ids)
        for key, ids in by_slot.items()
    }


def replay(executed=None, episode=None):
    return r.replay_episode(episode or f.private_episode(), executed or {}, Q03_DRAFT)


def codes(result):
    return [(x.code, x.slot, x.job_id) for x in result.findings]


# ----------------------------------------------------------------- state and outcome
def test_hand_schedule_replays_to_the_hand_states():
    rep = replay(starts(s0=["J1"], s2=["J2"]))
    assert rep.valid
    b = rep.boundaries
    assert (b[0].waiting, b[0].running) == (("J1", "J2"), ())
    assert (b[1].waiting, b[1].running) == (("J2",), (("J1", 0),))
    assert (b[2].waiting, b[2].completed) == (("J2",), (("J1", 0, 2),))
    assert (b[3].waiting, b[3].running) == ((), (("J2", 2),))  # J3 has not arrived
    assert (b[4].waiting, b[4].missed) == ((), ("J3",))  # impossible on arrival
    assert b[30].completed == (("J1", 0, 2), ("J2", 2, 4))
    assert [(x.started, x.running, x.completed, x.job_load_kw) for x in rep.slots[:5]] == [
        (("J1",), ("J1",), (), 40.0),
        ((), ("J1",), ("J1",), 40.0),
        (("J2",), ("J2",), (), 30.0),
        ((), ("J2",), ("J2",), 30.0),
        ((), (), (), 0.0),
    ]
    assert rep.completed_job_ids == ("J1", "J2")
    assert rep.missed_job_ids == ("J3",)
    assert rep.unfinished_job_ids == ("J3",)
    assert rep.completed_it_energy_kwh == 140.0  # 40 x 2 + 30 x 2, before PUE


def test_completed_it_energy_excludes_pue():
    ep = f.private_episode().model_copy(update={"snapshot": f.snapshot(pue=1.2)})
    assert replay(starts(s0=["J1"], s2=["J2"]), ep).completed_it_energy_kwh == 140.0


def test_waiting_job_is_missed_after_its_last_legal_start():
    # J1 and J2 can start as late as slot 4 (4 + 2 = deadline 6).
    rep = replay()
    assert rep.boundaries[4].waiting == ("J1", "J2")
    assert rep.boundaries[5].missed == ("J1", "J2", "J3")
    assert rep.completed_job_ids == () and rep.completed_it_energy_kwh == 0.0
    assert rep.unfinished_job_ids == ("J1", "J2", "J3")


def test_q01_no_start_after_slot_23():
    late = s.Job(
        job_id="L1", arrival_slot=17, duration_slots=1, power_kw=10, deadline_slot=30, flexible=True
    )
    ep = episode_with([late])
    rep = replay(episode=ep)
    assert rep.boundaries[23].waiting == ("L1",)
    assert rep.boundaries[24].missed == ("L1",)
    executed = replay(starts(s24=["L1"]), ep)
    assert codes(executed) == [("executed_not_waiting", 24, "L1")]
    assert executed.findings[0].detail == "missed"


def test_nonflexible_job_is_missed_right_after_its_arrival():
    fixed = s.Job(
        job_id="N1", arrival_slot=3, duration_slots=1, power_kw=10, deadline_slot=10, flexible=False
    )
    rep = replay(episode=episode_with([fixed]))
    assert rep.boundaries[3].waiting == ("N1",)
    assert rep.boundaries[4].missed == ("N1",)


# ----------------------------------------------------------------- arrival option B
def replay_b(executed=None, episode=None):
    return r.replay_episode(episode or f.private_episode(), executed or {}, Q03_OPTION_B)


def test_option_b_impossible_arrival_waits_one_decision_then_is_missed():
    # J3 arrives at 4 needing 3 slots by deadline 6: no legal start, but under B it is
    # shown for its arrival decision and missed at boundary 5.
    rep = replay_b(starts(s0=["J1"], s2=["J2"]))
    assert rep.valid
    assert (rep.boundaries[4].waiting, rep.boundaries[4].missed) == (("J3",), ())
    assert (rep.boundaries[5].waiting, rep.boundaries[5].missed) == ((), ("J3",))
    assert rep.missed_job_ids == rep.unfinished_job_ids == ("J3",)
    assert rep.completed_job_ids == ("J1", "J2") and rep.completed_it_energy_kwh == 140.0


def test_option_b_leaves_ordinary_expiry_unchanged():
    # J1 and J2 still wait through their last legal start (4) and are missed at 5.
    rep = replay_b()
    assert rep.boundaries[4].waiting == ("J1", "J2", "J3")
    assert rep.boundaries[5].missed == ("J1", "J2", "J3")


def test_option_b_start_of_an_impossible_arrival_is_reported_and_not_applied():
    rep = replay_b(starts(s0=["J1"], s2=["J2"], s4=["J3"]))
    assert codes(rep) == [("executed_no_legal_start", 4, "J3")]
    assert rep.slots[4].running == () and rep.boundaries[5].missed == ("J3",)
    assert rep.completed_job_ids == ("J1", "J2")


def test_option_b_mixed_arrival_still_serves_the_feasible_job():
    ok = s.Job(
        job_id="F1", arrival_slot=4, duration_slots=1, power_kw=10, deadline_slot=6, flexible=True
    )
    ep = episode_with(list(f.jobs().values()) + [ok])
    rep = replay_b(starts(s0=["J1"], s2=["J2"], s4=["F1"]), ep)
    assert rep.valid
    assert rep.boundaries[4].waiting == ("F1", "J3")
    assert rep.boundaries[5].missed == ("J3",)
    assert rep.completed_job_ids == ("F1", "J1", "J2")


def test_option_b_nonflexible_impossible_arrival():
    fixed = s.Job(
        job_id="N2", arrival_slot=3, duration_slots=3, power_kw=10, deadline_slot=5, flexible=False
    )
    rep = replay_b(episode=episode_with([fixed]))
    assert rep.boundaries[3].waiting == ("N2",)
    assert rep.boundaries[4].missed == ("N2",)
    assert codes(replay_b(starts(s3=["N2"]), episode_with([fixed]))) == [
        ("executed_no_legal_start", 3, "N2")
    ]


def test_option_b_impossible_arrival_at_the_last_decision_slot():
    # Arriving at 23 needing 8 slots cannot end by 30; it waits at 23 and is missed at 24.
    late = s.Job(
        job_id="L2", arrival_slot=23, duration_slots=8, power_kw=10, deadline_slot=30, flexible=True
    )
    rep = replay_b(episode=episode_with([late]))
    assert rep.boundaries[23].waiting == ("L2",)
    assert rep.boundaries[24].missed == ("L2",)
    assert replay(episode=episode_with([late])).boundaries[23].missed == ("L2",)  # draft rule


def test_protocol_option_must_be_explicit_boolean():
    with pytest.raises(ValueError, match="Boolean"):
        v.Protocol(name="x", status="y", last_start_slot=23, impossible_arrival_waits=1)


# ----------------------------------------------------------------- executions the rules forbid
def test_overlap_above_capacity_is_applied_and_reported_in_each_slot():
    # 40 + 40 + 30 = 110 kW > 100 kW in slots 0 and 1. The jobs did run.
    rep = replay(starts(s0=["J1", "J2"]))
    assert codes(rep) == [("capacity", 0, None), ("capacity", 1, None)]
    assert rep.completed_job_ids == ("J1", "J2")


def test_exact_capacity_is_allowed():
    exact = s.Job(
        job_id="X1", arrival_slot=0, duration_slots=1, power_kw=60, deadline_slot=5, flexible=True
    )
    over = exact.model_copy(update={"power_kw": 60.0000000001})
    assert replay(starts(s0=["X1"]), episode_with([exact])).valid
    assert codes(replay(starts(s0=["X1"]), episode_with([over]))) == [("capacity", 0, None)]


def test_impossible_executions_are_reported_and_not_applied():
    executed = starts(s0=["J1", "J9"], s1=["J1"], s4=["J3"])
    executed[2] = (s.ApprovedStart(job_id="J2", start_slot=3),)
    rep = replay(executed)
    assert codes(rep) == [
        ("executed_unknown_job", 0, "J9"),
        ("executed_not_waiting", 1, "J1"),
        ("executed_slot_mismatch", 2, "J2"),
        ("executed_not_waiting", 4, "J3"),
    ]
    assert [x.detail for x in rep.findings[1:]] == ["already running", "start_slot 3", "missed"]
    assert rep.completed_job_ids == ("J1",)  # J2 never ran
    assert rep.missed_job_ids == ("J2", "J3")


def test_starting_a_job_twice_in_one_slot_is_reported():
    rep = replay(starts(s0=["J1", "J1"]))
    assert codes(rep) == [("executed_not_waiting", 0, "J1")]
    assert rep.findings[0].detail == "started twice in one slot"


def test_starting_before_arrival_is_reported():
    rep = replay(starts(s3=["J3"]))
    assert codes(rep) == [("executed_not_waiting", 3, "J3")]
    assert rep.findings[0].detail == "not arrived"


def test_start_without_capacity_evidence_is_unverifiable():
    ep = f.private_episode().model_copy(update={"snapshot": f.snapshot(include_capacity=False)})
    assert codes(replay(starts(s0=["J1"]), ep)) == [("capacity_unverifiable", 0, None)]
    assert replay(episode=ep).valid  # nothing ran, so nothing needed capacity


# ----------------------------------------------------------------- recorded records
def hand_result(**changes):
    started = {0: ("J1",), 2: ("J2",)}
    running = {0: ("J1",), 1: ("J1",), 2: ("J2",), 3: ("J2",)}
    done = {1: ("J1",), 3: ("J2",)}
    load = {0: 40.0, 1: 40.0, 2: 30.0, 3: 30.0}
    fields = dict(
        episode_id=f.EPISODE_ID,
        run_id="RUN-HAND",
        system="greedy_a",
        n_decision_slots=24,
        n_completion_slots=6,
        slots=tuple(
            s.SlotRecord(
                slot=t,
                phase="decision" if t < 24 else "completion",
                job_load_kw=load.get(t, 0.0),
                background_load_kw=40.0,
                started_job_ids=started.get(t, ()),
                running_job_ids=running.get(t, ()),
                completed_job_ids=done.get(t, ()),
            )
            for t in range(30)
        ),
        totals=s.EpisodeTotals(),
        job_count_total=3,
        completed_job_ids=("J1", "J2"),
        deadline_missed_job_ids=("J3",),
        unfinished_job_ids=("J3",),
    )
    return s.EpisodeResult(**(fields | changes))


def test_matching_episode_result_has_no_mismatches():
    assert r.compare_result(replay(starts(s0=["J1"], s2=["J2"])), hand_result()) == ()


def test_episode_result_mismatches_are_reported_not_corrected():
    rep = replay(starts(s0=["J1"], s2=["J2"]))
    bad = hand_result(completed_job_ids=("J1",), unfinished_job_ids=("J2", "J3"))
    slots = list(bad.slots)
    slots[2] = slots[2].model_copy(update={"job_load_kw": 35.0})
    bad = bad.model_copy(update={"slots": tuple(slots)})
    found = [(m.field, m.slot) for m in r.compare_result(rep, bad)]
    assert found == [("completed_job_ids", None), ("unfinished_job_ids", None), ("job_load_kw", 2)]
    assert rep.completed_job_ids == ("J1", "J2")


def test_result_for_another_episode_is_refused():
    with pytest.raises(ValueError):
        r.compare_result(replay(), hand_result(episode_id="EP-OTHER"))


def test_recorded_state_matches_or_mismatches_the_replay():
    rep = replay(starts(s0=["J1"], s2=["J2"]))
    snap = f.snapshot()
    jobs = f.jobs()
    same = s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=2,
        state_version=2,
        waiting_jobs=(jobs["J2"],),
        completed_jobs=(s.CompletedJobView(job_id="J1", start_slot=0, end_slot=2),),
    )
    assert r.compare_state(rep, same) == ()
    # A state showing J3 waiting at its arrival contradicts the miss-on-arrival rule.
    shown = s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=4,
        state_version=4,
        waiting_jobs=(jobs["J3"],),
        completed_jobs=(
            s.CompletedJobView(job_id="J1", start_slot=0, end_slot=2),
            s.CompletedJobView(job_id="J2", start_slot=2, end_slot=4),
        ),
    )
    assert [(m.field, m.expected, m.recorded) for m in r.compare_state(rep, shown)] == [
        ("waiting", (), ("J3",)),
        ("missed", ("J3",), ()),
    ]


def test_replayed_state_feeds_the_decision_validator():
    rep = replay()
    facts = v.facts_from_state(rep.state_at(0), f.snapshot())
    assert v.validate_plan(f.plan(), facts, Q03_DRAFT).valid
    with pytest.raises(ValueError):
        rep.state_at(24)  # completion slots have no decision


def test_executed_starts_are_collected_from_one_run():
    record = f.decision_record()
    assert r.executed_starts([record], f.EPISODE_ID) == {
        0: (s.ApprovedStart(job_id="J1", start_slot=0),)
    }
    with pytest.raises(ValueError):
        r.executed_starts([record, record], f.EPISODE_ID)
    with pytest.raises(ValueError):
        r.executed_starts([record], "EP-OTHER")
    other = record.model_copy(update={"slot": 1, "run_id": "RUN-OTHER"})
    with pytest.raises(ValueError):
        r.executed_starts([record, other], f.EPISODE_ID)


def test_replay_does_not_import_production_or_shared_logic():
    tree = ast.parse(Path(r.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for forbidden in ("verification", "simulator", "metrics", "policies", "runtime"):
        assert not any(forbidden in module for module in imported), forbidden


# ----------------------------------------------------------------- S01 consumer check
def episode_with(jobs, scenario="hand-example", episode_id="EP-REPLAY"):
    """A private episode for the given jobs, keeping only constraints that name them."""
    ids = {j.job_id for j in jobs}
    snap = f.snapshot()
    snap = snap.model_copy(
        update={"constraints": tuple(c for c in snap.constraints if set(c.applies_to_jobs) <= ids)}
    )
    return s.PrivateEpisode(
        episode_id=episode_id,
        scenario_id=scenario,
        split="development",
        seed=0,
        n_decision_slots=24,
        n_completion_slots=6,
        snapshot=snap,
        jobs=tuple(
            s.PrivateJob(job=j, scenario_id=scenario, split="development", seed=0, synthetic=True)
            for j in jobs
        ),
        realized_carbon=f.observations(),
        forecast_visibility="perfect_foresight",
    )


def greedy_ids(state, capacity):
    """Start waiting jobs in ID order while every occupied slot stays within capacity."""
    occupied = [(v.job, v.start_slot) for v in state.running_jobs]
    chosen = []
    for job in state.waiting_jobs:
        trial = occupied + [(job, state.current_slot)]
        if all(
            state.site.background_kw
            + sum(j.power_kw for j, st in trial if st <= t < st + j.duration_slots)
            <= capacity
            for t in range(state.current_slot, state.current_slot + job.duration_slots)
        ):
            occupied, chosen = trial, chosen + [job.job_id]
    return chosen


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_s01_simulator_agrees_with_the_replay(scenario):
    for seed in range(3):
        jobs = [p.job for p in generate_jobs(scenario, seed=seed, split="development")]
        ep = episode_with(jobs, scenario, f"EP-{scenario.upper()}{seed}")
        sim = SchedulingSimulator(allow_completion_starts=False)
        states = [sim.reset(ep)]
        executed = {}
        for t in range(30):
            state = sim.state()
            ids = greedy_ids(state, 100.0) if t < 24 else []
            if seed == 1 and t == 2:
                ids += ["NOT-A-JOB"]  # the simulator rejects the batch; nothing runs
            action = s.ApprovedActions(
                episode_id=ep.episode_id,
                slot=t,
                state_version=t,
                plan_hash="a" * 64,
                check_id="CHK-SYNTHETIC",
                starts=tuple(s.ApprovedStart(job_id=j, start_slot=t) for j in ids),
            )
            ran = sim.step(action).slot.started_job_ids
            executed[t] = tuple(s.ApprovedStart(job_id=j, start_slot=t) for j in ran)
            states.append(sim.state())
        rep = r.replay_episode(ep, executed, Q03_DRAFT)
        assert rep.valid, (scenario, seed, rep.findings)
        assert r.compare_result(rep, sim.result(run_id="RUN-S01", system="greedy_a")) == ()
        for state in states[:24]:
            assert r.compare_state(rep, state) == (), (scenario, seed, state.current_slot)
