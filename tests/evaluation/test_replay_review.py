"""Hand-derived review cases; no production checker/simulator truth is used."""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_DRAFT
from tests.contracts import fixtures as f
from tests.evaluation.test_replay import hand_result, starts


@pytest.mark.parametrize(
    "change,field",
    [
        ({"constraint_snapshot_id": "SNAP-OTHER"}, "constraint_snapshot_id"),
        ({"site": f.site(pue=1.2)}, "site"),
        ({"constraint_ids": ()}, "constraint_ids"),
    ],
)
def test_state_comparison_catches_altered_authoritative_metadata(change, field):
    replay = r.replay_episode(f.private_episode(), {}, Q03_DRAFT)
    changed = replay.state_at(0).model_copy(update=change)
    assert field in {item.field for item in r.compare_state(replay, changed)}


@pytest.mark.parametrize(
    "kind,job_id,limit",
    [
        ("deadline", "J1", 5),
        ("arrival", "J1", 1),
        ("nonflexible", "J1", 0),
        ("deadline", "J9", 6),
    ],
)
def test_replay_refuses_contradictory_or_unknown_private_job_constraints(kind, job_id, limit):
    episode = f.private_episode()
    constraint = s.Constraint(
        constraint_id="CON-REVIEW",
        constraint_type=kind,
        limit_value=limit,
        unit="slot",
        applies_to_jobs=(job_id,),
        source_id=f.SOURCE_ID,
    )
    snapshot = episode.snapshot.model_copy(
        update={"constraints": (*episode.snapshot.constraints, constraint)}
    )
    with pytest.raises(ValueError, match="constraint"):
        r.replay_episode(episode.model_copy(update={"snapshot": snapshot}), {}, Q03_DRAFT)


def test_nonhourly_episode_is_not_reinterpreted_as_hourly_replay():
    episode = f.private_episode()
    site = episode.snapshot.site.model_copy(update={"slot_hours": 2.0})
    snapshot = episode.snapshot.model_copy(update={"site": site})
    with pytest.raises(ValueError, match="hour"):
        r.replay_episode(episode.model_copy(update={"snapshot": snapshot}), {}, Q03_DRAFT)


def test_unagreed_completed_work_mapping_cannot_get_a_clean_comparison():
    replay = r.replay_episode(f.private_episode(), starts(s0=["J1"], s2=["J2"]), Q03_DRAFT)
    record = hand_result(
        completed_work=s.CompletedWork(value=99, unit="jobs", definition="Completed jobs")
    )
    [mismatch] = r.compare_result(replay, record)
    assert mismatch.field == "completed_work"
    assert (mismatch.expected.status, mismatch.expected.reason) == (
        "not_comparable",
        "mapping_differs",
    )
