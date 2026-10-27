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
