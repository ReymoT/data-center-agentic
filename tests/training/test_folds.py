"""Observable blocked-fold partitions and train-only preprocessing."""

import pytest

from dc_sustainability.training.folds import (
    FOLD_COUNT,
    TrainOnlyScaler,
    balanced_class_weights,
    blocked_fold_splits,
    refuse_held_out_episodes,
)


def _map():
    return {
        "EP-A": 0,
        "EP-B": 0,
        "EP-C": 1,
        "EP-D": 1,
        "EP-E": 2,
        "EP-F": 2,
    }


def test_three_folds_keep_each_episode_in_one_eval_partition():
    splits = blocked_fold_splits(_map())
    assert FOLD_COUNT == 3
    assert len(splits) == 3
    assert [split.fold for split in splits] == [0, 1, 2]
    for split in splits:
        assert split.eval_episode_ids.isdisjoint(split.train_episode_ids)
        assert split.eval_episode_ids | split.train_episode_ids == frozenset(_map())
    assert splits[0].eval_episode_ids == frozenset({"EP-A", "EP-B"})
    assert splits[0].train_episode_ids == frozenset({"EP-C", "EP-D", "EP-E", "EP-F"})


def test_held_out_episodes_are_refused_from_the_fold_map():
    with pytest.raises(ValueError, match="held-out episodes cannot enter development folds"):
        refuse_held_out_episodes(_map(), {"EP-HELD", "EP-A"})


def test_unknown_or_missing_fold_ids_are_refused():
    with pytest.raises(ValueError, match="fold id must be one of"):
        blocked_fold_splits({"EP-A": 0, "EP-B": 1, "EP-C": 3})
    with pytest.raises(ValueError, match="must use all three development folds"):
        blocked_fold_splits({"EP-A": 0, "EP-B": 0, "EP-C": 1})


def test_scaler_fits_training_partition_only():
    train = ((0.0, 10.0), (2.0, 30.0))
    eval_rows = ((4.0, 50.0),)
    scaler = TrainOnlyScaler.fit(train)
    assert scaler.means == (1.0, 20.0)
    assert scaler.scales == (1.0, 10.0)
    assert scaler.transform(eval_rows) == ((3.0, 3.0),)
    assert scaler.transform(train) == ((-1.0, -1.0), (1.0, 1.0))


def test_zero_variance_feature_uses_unit_scale():
    scaler = TrainOnlyScaler.fit(((5.0, 1.0), (5.0, 3.0)))
    assert scaler.means == (5.0, 2.0)
    assert scaler.scales == (1.0, 1.0)
    assert scaler.transform(((5.0, 4.0),)) == ((0.0, 2.0),)


def test_balanced_class_weights_use_training_counts():
    assert balanced_class_weights((0, 0, 0, 1)) == (4 / 6, 4 / 2)


def test_empty_class_gets_no_invented_weight():
    with pytest.raises(ValueError, match="no invented class weight"):
        balanced_class_weights((0, 0, 0))
    with pytest.raises(ValueError, match="no invented class weight"):
        balanced_class_weights((1, 1))
