"""E03 paired statistics tests, with hand values and exact enumeration of small resamples."""

import ast
import itertools
import math
import statistics
from dataclasses import replace
from pathlib import Path

import pytest

from dc_sustainability.evaluation import paired as p
from dc_sustainability.evaluation.comparison import SavingsComparison

TRIALS = {"plain_llm": (0, 1, 2), "agent": (0, 1, 2), "greedy_a": (None,)}
FAST = p.Resampling(resamples=2_000)


def obs(system, episode, trial, value, scenario="normal", date="2022-01-15"):
    return p.Observation(system, episode, trial, scenario, date, value)


def llm_pair(episode, plain, agent, **labels):
    """Three trials each; ``plain`` and ``agent`` are per-trial values."""
    return [
        *(obs("plain_llm", episode, t, v, **labels) for t, v in enumerate(plain)),
        *(obs("agent", episode, t, v, **labels) for t, v in enumerate(agent)),
    ]


def sample(differences):
    """A paired sample with one date per episode."""
    return p.PairedSample(
        "plain_llm",
        "agent",
        tuple(
            p.EpisodeDifference(f"E{i}", "normal", f"D{i}", value)
            for i, value in enumerate(differences)
        ),
        {},
    )


def planned(observations):
    return {o.episode_id: (o.scenario, o.date) for o in observations}


def pair(observations, labels=None):
    observations = list(observations)
    labels = planned(observations) if labels is None else labels
    return p.paired_sample(observations, "plain_llm", "agent", TRIALS, labels)


def test_trials_are_averaged_inside_their_episode_before_differencing():
    result = pair(llm_pair("E1", (1, 2, 3), (4, 6, 8)))
    assert [d.difference for d in result.differences] == [4.0]  # mean 6 minus mean 2


def test_systems_with_different_trial_counts_pair_on_episode_means():
    observations = [
        obs("greedy_a", "E1", None, 10.0),
        *(obs("agent", "E1", t, v) for t, v in enumerate((4.0, 6.0, 8.0))),
    ]
    result = p.paired_sample(observations, "greedy_a", "agent", TRIALS, planned(observations))
    assert result.differences[0].difference == -4.0


def test_a_missing_trial_excludes_the_episode_and_is_counted():
    observations = llm_pair("E1", (1, 2, 3), (4, 6, 8))[:-1] + llm_pair("E2", (1, 1, 1), (2, 2, 2))
    result = pair(observations)
    assert [d.episode_id for d in result.differences] == ["E2"]
    assert result.excluded == {"E1": "run_missing"}


def test_an_unavailable_value_excludes_the_episode_and_is_not_zero():
    result = pair(llm_pair("E1", (1, None, 3), (4, 6, 8)))
    assert result.differences == ()
    assert result.excluded_by_reason == {"value_unavailable": 1}


def test_an_episode_only_one_system_reached_is_excluded_not_dropped():
    result = pair([obs("agent", "E1", t, 1.0) for t in range(3)])
    assert result.excluded == {"E1": "run_missing"}


def test_a_planned_episode_with_no_runs_at_all_is_still_counted():
    observations = llm_pair("E1", (1, 1, 1), (2, 2, 2))
    labels = {**planned(observations), "E2": ("spike", "2022-02-15")}
    result = pair(observations, labels)
    assert [d.episode_id for d in result.differences] == ["E1"]
    assert result.excluded == {"E2": "run_missing"}


def test_other_systems_do_not_add_episodes_to_a_pair():
    observations = llm_pair("E1", (1, 1, 1), (2, 2, 2))
    result = pair([*observations, obs("greedy_a", "E9", None, 5.0)], planned(observations))
    assert [d.episode_id for d in result.differences] == ["E1"]
    assert not result.excluded


def test_an_unplanned_episode_or_wrong_label_is_refused():
    observations = llm_pair("E1", (1, 1, 1), (2, 2, 2))
    with pytest.raises(ValueError, match="not a planned episode"):
        pair(observations, {})
    with pytest.raises(ValueError, match="not a planned episode"):
        pair(observations, {"E1": ("spike", "2022-01-15")})


@pytest.mark.parametrize(
    "observations, message",
    [
        ([obs("agent", "E1", 0, 1.0), obs("agent", "E1", 0, 2.0)], "more than one"),
        ([obs("agent", "E1", 7, 1.0)], "unexpected trial"),
        (
            [obs("agent", "E1", 0, 1.0), obs("plain_llm", "E1", 0, 1.0, date="2022-02-15")],
            "conflicting",
        ),
    ],
)
def test_defective_observations_are_refused(observations, message):
    with pytest.raises(ValueError, match=message):
        pair(observations)


@pytest.mark.parametrize("value", [math.nan, math.inf])
def test_nonfinite_values_are_refused(value):
    with pytest.raises(ValueError, match="finite"):
        obs("agent", "E1", 0, value)


def test_a_system_cannot_be_compared_with_itself_or_without_expected_trials():
    with pytest.raises(ValueError, match="two systems"):
        p.paired_sample([], "agent", "agent", TRIALS, {})
    with pytest.raises(ValueError, match="expected trials"):
        p.paired_sample([], "agent", "unknown", TRIALS, {})


def test_the_estimate_is_the_mean_of_episode_differences():
    assert p.interval(sample([1.0, 2.0, 6.0]), FAST).estimate == pytest.approx(3.0)


def test_interval_matches_exact_enumeration_of_every_resample():
    values = [1.0, 2.0, 6.0, 9.0]
    exact = sorted(
        sum(draw) / len(values) for draw in itertools.product(values, repeat=len(values))
    )
    result = p.interval(sample(values), p.Resampling(resamples=100_000))
    low = exact[round(0.025 * (len(exact) - 1))]
    high = exact[round(0.975 * (len(exact) - 1))]
    assert result.lower == pytest.approx(low, abs=0.2)
    assert result.upper == pytest.approx(high, abs=0.2)


def test_the_same_settings_give_the_same_interval_in_any_input_order():
    forward = sample([1.0, 2.0, 6.0, 9.0])
    backward = replace(forward, differences=tuple(reversed(forward.differences)))
    assert p.interval(forward, FAST) == p.interval(backward, FAST)


def test_a_different_seed_is_a_different_draw():
    seeded = p.Resampling(resamples=2_000, seed=1)
    assert p.interval(sample([1.0, 2.0, 6.0, 9.0]), seeded) != p.interval(
        sample([1.0, 2.0, 6.0, 9.0]), FAST
    )


def test_more_confidence_gives_a_wider_interval():
    values = sample([1.0, 2.0, 6.0, 9.0, 3.0, 5.0])
    narrow = p.interval(values, p.Resampling(resamples=2_000, confidence=0.5))
    wide = p.interval(values, p.Resampling(resamples=2_000, confidence=0.95))
    assert wide.lower < narrow.lower < narrow.upper < wide.upper


def test_tripling_identical_trials_does_not_narrow_the_interval():
    def episodes(trial_count):
        trials = {"plain_llm": tuple(range(trial_count)), "agent": tuple(range(trial_count))}
        observations = []
        for index, value in enumerate((1.0, 2.0, 6.0, 9.0)):
            for trial in range(trial_count):
                observations += [
                    obs("plain_llm", f"E{index}", trial, 0.0),
                    obs("agent", f"E{index}", trial, value),
                ]
        return p.paired_sample(observations, "plain_llm", "agent", trials, planned(observations))

    one, three = p.interval(episodes(1), FAST), p.interval(episodes(3), FAST)
    assert (one.lower, one.upper, one.units) == (three.lower, three.upper, three.units)


def test_one_episode_has_an_estimate_but_no_interval():
    result = p.interval(sample([2.0]), FAST)
    assert (result.estimate, result.lower, result.upper) == (2.0, None, None)


def test_no_episodes_give_no_estimate_rather_than_zero():
    result = p.interval(sample([]), FAST)
    assert (result.estimate, result.lower, result.episodes) == (None, None, 0)


def test_equal_differences_give_a_real_zero_width_interval():
    result = p.interval(sample([2.0, 2.0, 2.0]), FAST)
    assert (result.lower, result.upper) == (2.0, 2.0)


def test_exclusions_are_reported_with_the_interval():
    observations = [
        *llm_pair("E1", (1, 1, 1), (2, 2, 2)),
        *llm_pair("E2", (1, 1, 1), (3, 3, 3)),
        *llm_pair("E3", (1, None, 1), (3, 3, 3)),
    ]
    result = p.interval(pair(observations), FAST)
    assert (result.episodes, result.excluded) == (2, 1)


def by_date(groups):
    return p.PairedSample(
        "plain_llm",
        "agent",
        tuple(
            p.EpisodeDifference(f"{date}-{i}", "normal", date, value)
            for date, values in groups.items()
            for i, value in enumerate(values)
        ),
        {},
    )


def test_date_resampling_keeps_a_dates_episodes_together():
    # Four scenarios move together within a date, so dates hold the real sample size.
    groups = {"D1": [0.0] * 4, "D2": [10.0] * 4}
    by_episode = p.interval(by_date(groups), FAST)
    dates = p.interval(by_date(groups), FAST, by="date")
    assert (by_episode.units, dates.units) == (8, 2)
    assert dates.estimate == by_episode.estimate == 5.0
    assert (dates.lower, dates.upper) == (0.0, 10.0)
    assert dates.upper - dates.lower > by_episode.upper - by_episode.lower


def test_date_resampling_weights_unequal_dates_by_their_episodes():
    groups = {"D1": [0.0], "D2": [10.0, 10.0, 10.0]}
    result = p.interval(by_date(groups), p.Resampling(resamples=100_000), by="date")
    exact = sorted(
        sum(sum(groups[d]) for d in draw) / sum(len(groups[d]) for d in draw)
        for draw in itertools.product(groups, repeat=2)
    )
    assert exact == [0.0, 2.5 * 3, 2.5 * 3, 10.0]
    assert (result.estimate, result.lower, result.upper) == (7.5, 0.0, 10.0)
    # The middle of the distribution is the mixed draw: 7.5 over episodes, not 5 over dates.
    middle = p.interval(by_date(groups), p.Resampling(resamples=100_000, confidence=0.2), by="date")
    assert (middle.lower, middle.upper) == (7.5, 7.5)


def test_one_date_has_no_date_interval():
    result = p.interval(by_date({"D1": [1.0, 2.0]}), FAST, by="date")
    assert (result.lower, result.upper, result.units) == (None, None, 1)


def test_an_unknown_resampling_unit_is_refused():
    with pytest.raises(ValueError, match="episode or date"):
        p.interval(sample([1.0, 2.0]), FAST, by="scenario")


@pytest.mark.parametrize(
    "settings",
    [{"resamples": 0}, {"confidence": 1.0}, {"confidence": 0.0}, {"seed": "1"}],
)
def test_invalid_settings_are_refused(settings):
    with pytest.raises(ValueError):
        p.Resampling(**settings)


def comparison(episode, trial, savings, status="comparable"):
    return SavingsComparison(
        episode_id=episode,
        baseline="plain_llm",
        candidate="agent",
        trial=trial,
        status=status,
        reasons=() if status == "comparable" else ("completed_set_differs",),
        baseline_kg=None,
        candidate_kg=None,
        savings_kg=savings,
        counts={},
        findings={},
        invalidating_findings={},
    )


LABELS = {"E1": ("normal", "D1"), "E2": ("spike", "D1"), "E3": ("normal", "D2")}


def test_savings_need_every_trial_comparable():
    items = [
        *(comparison("E1", t, 3.0 + t) for t in range(3)),
        comparison("E2", 0, 5.0),
        comparison("E2", 1, None, "blocked"),
        comparison("E2", 2, 5.0),
    ]
    result = p.savings_sample(items, LABELS, (0, 1, 2))
    assert [(d.episode_id, d.difference) for d in result.differences] == [("E1", 4.0)]
    assert result.excluded == {"E2": "comparison_blocked", "E3": "run_missing"}
    assert (result.baseline, result.candidate) == ("plain_llm", "agent")


def test_all_blocked_savings_give_no_estimate_rather_than_zero():
    items = [comparison(e, t, None, "blocked") for e in LABELS for t in range(3)]
    result = p.interval(p.savings_sample(items, LABELS, (0, 1, 2)), FAST)
    assert (result.estimate, result.episodes, result.excluded) == (None, 0, 3)


@pytest.mark.parametrize(
    "items, message",
    [
        ([], "at least one"),
        ([comparison("E9", 0, 1.0)], "no scenario"),
        ([comparison("E1", 7, 1.0)], "unexpected trial"),
        ([comparison("E1", 0, 1.0), comparison("E1", 0, 2.0)], "more than one"),
        (
            [comparison("E1", 0, 1.0), replace(comparison("E2", 0, 1.0), baseline="greedy_a")],
            "mix system pairs",
        ),
    ],
)
def test_defective_comparisons_are_refused(items, message):
    with pytest.raises(ValueError, match=message):
        p.savings_sample(items, LABELS, (0, 1, 2))


def test_scenario_summary_matches_hand_values_with_counts():
    rows = p.scenario_summary(
        [
            obs("agent", "E1", 0, 2.0),
            obs("agent", "E1", 1, 4.0),
            obs("agent", "E2", 0, 9.0),
            obs("agent", "E3", 0, None),
            obs("agent", "E4", 0, 7.0, scenario="spike"),
            obs("greedy_a", "E5", None, None, scenario="spike"),
        ]
    )
    normal, spike, empty = rows
    assert (normal.system, normal.scenario, normal.runs, normal.missing) == (
        "agent",
        "normal",
        4,
        1,
    )
    assert normal.mean == pytest.approx(5.0)
    assert normal.std == pytest.approx(statistics.stdev([2.0, 4.0, 9.0]))
    assert (normal.minimum, normal.maximum) == (2.0, 9.0)
    assert (spike.mean, spike.std, spike.minimum) == (7.0, None, 7.0)
    assert (empty.runs, empty.missing, empty.mean, empty.minimum) == (1, 1, None, None)


def test_the_module_stays_apart_from_policies_runs_and_production_checks():
    tree = ast.parse(Path(p.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported <= {
        "collections",
        "collections.abc",
        "dataclasses",
        "typing",
        "dc_sustainability.evaluation.comparison",
    }
