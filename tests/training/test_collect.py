"""Observable unlabeled decision samples from the S01 simulator."""

from datetime import timedelta

from dc_sustainability import schemas as s
from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.training.collect import CollectedDecision, collect_decisions
from dc_sustainability.training.features import candidate_features
from tests.contracts import fixtures as f
from tests.simulator.test_core import episode


def _empty_approve(state: s.VisibleState, _context: s.Context) -> s.ApprovedActions:
    return s.ApprovedActions(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        plan_hash="a" * 64,
        check_id="CHK-COLLECT",
        starts=(),
    )


def _decision_time(slot: int):
    return f.SLOT0_UTC + timedelta(hours=slot)


def _forecast_map():
    return {
        slot: tuple(fact for fact in f.forecasts(issued_slot=slot) if fact.valid_slot >= slot)
        for slot in range(30)
    }


def test_collects_thirty_unlabeled_decisions_with_feature_rows():
    samples = collect_decisions(
        episode(hand_jobs()),
        decision_time_utc=_decision_time,
        approve=_empty_approve,
        forecasts_by_slot=_forecast_map(),
    )
    assert len(samples) == 30
    first = samples[0]
    assert isinstance(first, CollectedDecision)
    assert first.episode_id == "EP-S01"
    assert first.slot == first.state_version == 0
    assert not hasattr(first, "label")
    assert "label" not in first.__dataclass_fields__
    assert first.candidate_keys == tuple((row.job_id, row.start_slot) for row in first.rows)
    assert first.rows
    direct = candidate_features(
        first.state, first.context, decision_time_utc=first.decision_time_utc
    )
    assert [(row.job_id, row.start_slot, row.values()) for row in first.rows] == [
        (row.job_id, row.start_slot, row.values()) for row in direct
    ]
    assert samples[-1].slot == 29
    assert {job.job_id for job in samples[0].state.waiting_jobs} == {"J1", "J2"}


def test_withheld_forecasts_yield_no_carbon_rows():
    samples = collect_decisions(
        episode(hand_jobs(), withheld=True),
        decision_time_utc=_decision_time,
        approve=_empty_approve,
        forecasts_by_slot={},
    )
    assert all(sample.rows == () for sample in samples)


def test_approve_must_return_approved_actions():
    try:
        collect_decisions(
            episode(hand_jobs()),
            decision_time_utc=_decision_time,
            approve=lambda state, context: {},
            forecasts_by_slot=_forecast_map(),
        )
    except TypeError as error:
        assert "ApprovedActions" in str(error)
    else:
        raise AssertionError("non-ApprovedActions approve was accepted")


def test_decision_time_must_be_utc():
    try:
        collect_decisions(
            episode(hand_jobs()),
            decision_time_utc=lambda _slot: f.SLOT0_UTC.replace(tzinfo=None),
            approve=_empty_approve,
            forecasts_by_slot=_forecast_map(),
        )
    except ValueError as error:
        assert str(error) == "an explicit trusted UTC decision time is required"
    else:
        raise AssertionError("naive decision time was accepted")
