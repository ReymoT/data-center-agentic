"""Q10 selection tests on synthetic manifests (#22).

Windows are worked out by hand from latest_start = min(deadline, 30) - duration, capped
at arrival for a nonflexible job, with t restricted to 0-23.
"""

import ast
import random
from collections import Counter
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation import sampling as q
from dc_sustainability.evaluation.validator import Q03_DRAFT
from tests.contracts import fixtures as f
from tests.evaluation.test_replay import episode_with, starts


def job(job_id, arrival, duration, deadline, flexible=True, power=10):
    return s.Job(
        job_id=job_id,
        arrival_slot=arrival,
        duration_slots=duration,
        power_kw=power,
        deadline_slot=deadline,
        flexible=flexible,
    )


def episode(jobs, episode_id="EP-SAMPLE", scenario="normal", forecast="perfect_foresight"):
    return episode_with(jobs, scenario, episode_id).model_copy(
        update={"forecast_visibility": forecast}
    )


# ----------------------------------------------------------------- eligibility boundaries
def test_window_runs_from_arrival_to_latest_legal_start():
    # Arrives at 3, 2 slots, deadline 8: latest start 6. Slot 2 is before arrival and
    # slot 7 is the first slot after the latest start.
    assert q.eligible_slots(episode([job("A1", 3, 2, 8)])) == (3, 4, 5, 6)


def test_nonflexible_job_has_only_its_arrival_slot():
    assert q.eligible_slots(episode([job("N1", 5, 2, 10, flexible=False)])) == (5,)


def test_impossible_window_makes_no_slot_eligible():
    impossible = episode([job("X1", 4, 3, 6)])  # latest start 3 < arrival 4
    assert q.eligible_slots(impossible) == ()


def test_window_stops_at_slot_23_and_boundary_30():
    assert q.eligible_slots(episode([job("L1", 20, 4, 40)])) == (20, 21, 22, 23)
    assert q.eligible_slots(episode([job("L2", 23, 8, 30)])) == ()  # 23 + 8 > 30
    # A deadline after 30 still has to finish by 30: latest start 30 - 8 = 22, not 32.
    assert q.eligible_slots(episode([job("L3", 20, 8, 40)])) == (20, 21, 22)


def test_union_of_windows_and_timing_only():
    # Too big for capacity on its own, but eligibility never looks at capacity.
    huge = job("H1", 0, 1, 2, power=1000)
    ep = episode([huge, job("A2", 10, 1, 12)])
    assert q.eligible_slots(ep) == (0, 1, 10, 11)


# ----------------------------------------------------------------- selection
def manifest(n=30, seed=0):
    """Thirty synthetic episodes over two scenarios and two forecast kinds, each with
    several eligible slots; arrivals vary so selections differ between episodes."""
    rng = random.Random(seed)
    episodes = []
    for i in range(n):
        arrival = rng.randrange(0, 12)
        jobs = [job("J1", arrival, 2, arrival + 8), job("J2", rng.randrange(0, 20), 1, 30)]
        episodes.append(
            episode(
                jobs,
                f"EP-S{i:02d}",
                scenario=("normal", "spike")[i % 2],
                forecast=("perfect_foresight", "persistence")[(i // 2) % 2],
            )
        )
    return episodes


def test_two_distinct_eligible_slots_per_episode_balanced_over_trials_and_strata():
    episodes = manifest()
    record = q.select(episodes)
    assert (record.target, record.achieved, record.shortfall) == (60, 60, {})
    by_episode = Counter(x.episode_id for x in record.selections)
    assert set(by_episode.values()) == {2}
    for x in record.selections:
        assert x.slot in record.eligible[x.episode_id]
    assert len({(x.episode_id, x.slot) for x in record.selections}) == 60
    assert record.counts_by_trial == {0: 20, 1: 20, 2: 20}
    for name in record.counts_by_stratum:
        per_trial = Counter(x.trial for x in record.selections if x.stratum == name)
        assert max(per_trial.values()) - min(per_trial.values()) <= 1
    assert (record.seed, record.analysis_seed) == (20261019, 20261020)


def test_selection_is_deterministic_and_ignores_input_order():
    episodes = manifest()
    first = q.select(episodes)
    shuffled = list(reversed(episodes))
    assert q.select(shuffled) == first
    assert q.select(episodes).to_jsonable() == first.to_jsonable()
    assert q.select(episodes, seed=1).selections != first.selections


def test_shortfall_is_reported_and_never_topped_up():
    episodes = manifest(4)
    one = episode([job("N1", 5, 1, 9, flexible=False)], "EP-ONE")
    none = episode([job("X1", 4, 3, 6)], "EP-NONE")
    record = q.select([*episodes, one, none])
    assert record.target == 12
    assert record.shortfall == {"EP-NONE": 2, "EP-ONE": 1}
    assert record.achieved == 9  # 8 + 1; nothing borrowed from other episodes
    assert [x.slot for x in record.selections if x.episode_id == "EP-ONE"] == [5]


def test_manifest_must_be_consistent():
    episodes = manifest(2)
    with pytest.raises(ValueError, match="unique"):
        q.select([episodes[0], episodes[0]])
    held_out = episodes[1].model_copy(update={"split": "held_out"})
    with pytest.raises(ValueError, match="splits"):
        q.select([episodes[0], held_out])


# ----------------------------------------------------------------- after the run
def test_selected_pair_is_kept_when_one_or_both_queues_are_empty():
    # Slot 1 is eligible by timing whatever the systems did. One run started nothing (J1
    # and J2 still wait); the other started both at slot 0, so its queue is empty.
    episode_ = f.private_episode()
    waiting = r.replay_episode(episode_, {}, Q03_DRAFT).state_at(1)
    empty = r.replay_episode(episode_, starts(s0=["J1", "J2"]), Q03_DRAFT).state_at(1)
    assert 1 in q.eligible_slots(episode_)
    pick = q.Selection(episode_.episode_id, "hand", 1, 0)

    one = q.pair_record(pick, {"agent": waiting, "plain_llm": empty})
    assert one.queue_counts == {"agent": 2, "plain_llm": 0}
    assert one.not_applicable == ("plain_llm",) and not one.both_nonempty
    assert one.state_hashes == {
        "agent": waiting.canonical_hash(),
        "plain_llm": empty.canonical_hash(),
    }
    both = q.pair_record(pick, {"agent": empty, "plain_llm": empty})
    assert both.not_applicable == ("agent", "plain_llm")
    full = q.pair_record(pick, {"agent": waiting, "plain_llm": waiting})
    assert full.both_nonempty


def test_pair_states_must_match_the_selection():
    episode_ = f.private_episode()
    state = r.replay_episode(episode_, {}, Q03_DRAFT).state_at(2)
    pick = q.Selection(episode_.episode_id, "hand", 1, 0)
    with pytest.raises(ValueError, match="selected episode and slot"):
        q.pair_record(pick, {"agent": state, "plain_llm": state})
    with pytest.raises(ValueError, match="exactly"):
        q.pair_record(pick, {"agent": state})


def test_selection_never_imports_outputs_runtime_or_policies():
    tree = ast.parse(Path(q.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for forbidden in ("policies", "runtime", "llm", "agent", "simulator", "verification"):
        assert not any(forbidden in module for module in imported), forbidden


# ----------------------------------------------------------------- abstention boundary (#22)
def test_impossible_arrival_is_in_the_boundary_stratum_not_the_primary_frame():
    ep = episode([job("X1", 4, 3, 6), job("A1", 10, 1, 12)])  # X1: latest start 3 < 4
    assert q.boundary_slots(ep) == (4,)
    assert 4 not in q.eligible_slots(ep)
    assert q.eligible_slots(ep) == (10, 11)


def test_feasible_capacity_only_and_late_arrivals_are_not_boundary_slots():
    feasible = job("F1", 3, 2, 8)
    capacity_only = job("H1", 0, 1, 2, power=1000)  # timing is fine; capacity is not read
    after_decisions = job("Z1", 25, 3, 26)  # impossible, but arrives after slot 23
    assert q.boundary_slots(episode([feasible, capacity_only, after_decisions])) == ()
    # Nonflexible: only the arrival slot is a legal start.
    assert q.boundary_slots(episode([job("N1", 5, 2, 7, flexible=False)])) == ()
    assert q.boundary_slots(episode([job("N2", 5, 3, 7, flexible=False)])) == (5,)
    # Boundary 30 binds even with a later deadline; slot 23 is the last decision slot.
    assert q.boundary_slots(episode([job("L2", 23, 8, 40)])) == (23,)
    assert q.boundary_slots(episode([job("L3", 22, 8, 40)])) == ()


def test_a_slot_is_in_both_only_when_it_qualifies_for_both():
    ep = episode([job("X1", 4, 3, 6), job("A1", 2, 1, 10)])  # A1's window covers slot 4
    assert 4 in q.boundary_slots(ep) and 4 in q.eligible_slots(ep)


def boundary_manifest(n, impossible_per_episode=1):
    return [
        episode(
            [job(f"X{k}", 2 * k + 1, 5, 2 * k + 3) for k in range(impossible_per_episode)]
            + [job("A1", 0, 1, 30)],
            f"EP-B{i:02d}",
            scenario=("normal", "spike")[i % 2],
        )
        for i in range(n)
    ]


def test_boundary_is_a_census_up_to_thirty():
    record = q.select_boundary(boundary_manifest(12, impossible_per_episode=2))
    assert record.eligible_count == record.selected_count == 24
    assert {(x.episode_id, x.slot) for x in record.selections} == {
        (e, slot) for e, slots in record.eligible.items() for slot in slots
    }
    assert record.counts_by_trial == {0: 8, 1: 8, 2: 8}
    assert record.seed == q.BOUNDARY_SEED == 20261021
    assert record.seed not in (q.SAMPLING_SEED, q.ANALYSIS_SEED)


def test_boundary_draws_thirty_with_its_own_seed_when_more_qualify():
    episodes = boundary_manifest(20, impossible_per_episode=2)
    record = q.select_boundary(episodes)
    assert (record.eligible_count, record.selected_count) == (40, 30)
    assert len({(x.episode_id, x.slot) for x in record.selections}) == 30
    for x in record.selections:
        assert x.slot in record.eligible[x.episode_id]
    assert record.counts_by_trial == {0: 10, 1: 10, 2: 10}
    data = record.to_jsonable()
    assert (data["eligible_count"], data["selected_count"], data["cap"]) == (40, 30, 30)
    # Deterministic and independent of input order; another seed draws differently.
    again = q.select_boundary(list(reversed(episodes)))
    assert again.selections == record.selections
    other = q.select_boundary(episodes, seed=1)
    assert {(x.episode_id, x.slot) for x in other.selections} != {
        (x.episode_id, x.slot) for x in record.selections
    }


def test_boundary_never_changes_the_primary_sample():
    episodes = manifest()
    before = q.select(episodes)
    q.select_boundary(episodes)
    assert q.select(episodes) == before
    assert q.select_boundary(episodes).selected_count == 0  # no impossible arrivals here


def test_boundary_uses_the_same_manifest_checks():
    with pytest.raises(ValueError, match="unique episode IDs"):
        q.select_boundary([])
    with pytest.raises(ValueError, match="trials must be distinct"):
        q.select_boundary(boundary_manifest(2), trials=(0, 0))
