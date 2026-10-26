"""Observable candidate feature rows from the agreed Q07 formulas."""

from datetime import timedelta, timezone

from dc_sustainability import schemas as s
from dc_sustainability.training.features import FEATURE_NAMES, candidate_features
from tests.contracts import fixtures as f


def _job(**fields):
    return f.jobs()["J2"].model_copy(update=fields)


def _fact(slot, value, *, fact_id, issued_at=f.SLOT0_UTC):
    return s.CarbonForecast(
        fact_id=fact_id,
        value=value,
        unit="g/kWh",
        source_id=f.SOURCE_ID,
        valid_slot=slot,
        issued_at_utc=issued_at,
        forecast_kind="perfect_foresight",
        semantics=f.semantics(),
        quality_status="unvalidated",
    )


def _series(values, *, issued_at=f.SLOT0_UTC):
    return tuple(
        _fact(i, value, fact_id=f"FACT-FT-s{i:02d}", issued_at=issued_at)
        for i, value in enumerate(values)
    )


def _rows(
    waiting,
    facts,
    *,
    decision_time=f.SLOT0_UTC,
    capacity_kw=100.0,
    include_capacity=True,
    running=(),
    background_kw=None,
    current_slot=0,
    construct_waiting=False,
):
    snap = f.snapshot(capacity_kw=capacity_kw, include_capacity=include_capacity)
    if background_kw is not None:
        snap = snap.model_copy(
            update={"site": snap.site.model_copy(update={"background_kw": background_kw})}
        )
    present = tuple(job for job in waiting if job.arrival_slot <= current_slot)
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=current_slot,
        state_version=0,
        waiting_jobs=present,
        running_jobs=tuple(running),
        carbon_facts=tuple(facts),
    )
    context = s.Context.build(state, snap, "flat")
    if construct_waiting:
        state = s.VisibleState.model_construct(
            episode_id=state.episode_id,
            current_slot=state.current_slot,
            state_version=state.state_version,
            site=state.site,
            constraint_snapshot_id=state.constraint_snapshot_id,
            constraint_ids=state.constraint_ids,
            waiting_jobs=tuple(waiting),
            running_jobs=state.running_jobs,
            completed_jobs=state.completed_jobs,
            missed_job_ids=state.missed_job_ids,
            carbon_facts=state.carbon_facts,
            missing_carbon_slots=state.missing_carbon_slots,
        )
    return candidate_features(state, context, decision_time_utc=decision_time)


def test_feature_names_and_deadline_margin():
    job = _job(duration_slots=2, deadline_slot=6, arrival_slot=0, power_kw=30)
    rows = _rows((job,), _series((500, 450, 300, 250, 400, 480)))
    assert FEATURE_NAMES[1] == "deadline_margin_slots"
    first = rows[0]
    assert (first.job_id, first.start_slot) == ("J2", 0)
    assert first.delay_slots == 0
    assert first.deadline_margin_slots == 4, "finish slack, not start-to-deadline"
    assert first.duration_slots == 2
    assert first.power_kw == 30
    assert first.available_capacity_kw == 60
    assert first.queue_load_count == 1
    assert first.carbon_mean_g_per_kwh == 475
    assert first.carbon_min_g_per_kwh == 450
    assert first.values() == (0, 4, 2, 30, 60, 1, 475, 450)


def test_later_start_uses_its_own_carbon_and_margin():
    job = _job(duration_slots=2, deadline_slot=6)
    rows = _rows((job,), _series((500, 450, 300, 250, 400, 480)))
    second = rows[1]
    assert second.start_slot == 1
    assert second.deadline_margin_slots == 3
    assert second.carbon_mean_g_per_kwh == 375
    assert second.carbon_min_g_per_kwh == 300


def test_both_starts_keep_the_same_free_capacity():
    job = _job(duration_slots=1, deadline_slot=4, power_kw=30)
    rows = _rows((job,), _series((100, 200, 300, 400)))
    assert [row.start_slot for row in rows] == [0, 1, 2, 3]
    assert {row.available_capacity_kw for row in rows} == {60}


def test_running_load_reduces_available_capacity():
    waiting = _job(job_id="J2", duration_slots=1, deadline_slot=4, power_kw=10)
    running_job = _job(job_id="J1", duration_slots=2, power_kw=20)
    running = (s.RunningJobView(job=running_job, start_slot=0),)
    rows = _rows((waiting,), _series((100, 100, 100, 100)), running=running)
    assert rows[0].available_capacity_kw == 40
    assert rows[0].start_slot == 0


def test_missing_carbon_drops_only_that_start():
    job = _job(duration_slots=1, deadline_slot=3)
    facts = (_fact(0, 100, fact_id="FACT-FT-s00"),)
    rows = _rows((job,), facts)
    assert [row.start_slot for row in rows] == [0]


def test_stale_carbon_drops_the_start():
    job = _job(duration_slots=1, deadline_slot=2)
    issued = f.SLOT0_UTC - timedelta(hours=3)
    rows = _rows((job,), _series((100, 100), issued_at=issued))
    assert rows == ()


def test_future_issued_carbon_drops_the_start():
    job = _job(duration_slots=1, deadline_slot=2)
    issued = f.SLOT0_UTC + timedelta(hours=1)
    rows = _rows((job,), _series((100, 100), issued_at=issued))
    assert rows == ()


def test_missing_capacity_returns_no_rows():
    job = _job(duration_slots=1, deadline_slot=2)
    rows = _rows((job,), _series((100, 100)), include_capacity=False)
    assert rows == ()


def test_oversized_job_is_omitted_and_queue_still_counts_it():
    huge = _job(job_id="JH", power_kw=150, duration_slots=1, deadline_slot=4)
    small = _job(job_id="JS", power_kw=30, duration_slots=1, deadline_slot=4)
    rows = _rows((huge, small), _series((100, 100, 100, 100)))
    assert [row.job_id for row in rows] == ["JS", "JS", "JS", "JS"]
    assert rows[0].queue_load_count == 2


def test_future_arrival_is_absent_from_rows_and_queue():
    present = _job(job_id="JP", duration_slots=1, deadline_slot=1)
    future = _job(job_id="JF", arrival_slot=3, duration_slots=1, deadline_slot=6)
    rows = _rows((present, future), _series((100,)), construct_waiting=True)
    assert [row.job_id for row in rows] == ["JP"]
    assert rows[0].queue_load_count == 1


def test_nonflexible_row_precedes_flexible_row():
    flexible = _job(job_id="JF", flexible=True, duration_slots=1, deadline_slot=1)
    fixed = _job(job_id="JN", flexible=False, duration_slots=1, deadline_slot=1)
    rows = _rows((flexible, fixed), _series((100, 100)))
    assert [(row.job_id, row.start_slot) for row in rows] == [("JN", 0), ("JF", 0)]


def test_decision_time_must_be_utc():
    job = _job(duration_slots=1, deadline_slot=2)
    try:
        _rows((job,), _series((100,)), decision_time=f.SLOT0_UTC.replace(tzinfo=None))
    except ValueError as error:
        assert str(error) == "an explicit trusted UTC decision time is required"
    else:
        raise AssertionError("naive decision time was accepted")
    aware = f.SLOT0_UTC.astimezone(timezone(timedelta(hours=-7)))
    try:
        _rows((job,), _series((100,)), decision_time=aware)
    except ValueError as error:
        assert str(error) == "an explicit trusted UTC decision time is required"
    else:
        raise AssertionError("non-utc decision time was accepted")
