"""Observable greedy_b plans and greedy_a fallbacks from shared contract fixtures."""

from datetime import timedelta

from dc_sustainability import schemas as s
from dc_sustainability.policies import propose
from tests.contracts import fixtures as f


def _job(**fields):
    return f.jobs()["J2"].model_copy(update=fields)


def _carbon_fact(slot, value, *, fact_id, issued_at=f.SLOT0_UTC):
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


def _state(waiting, carbon_facts=(), **snap_kwargs):
    snap = f.snapshot(**snap_kwargs)
    return s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=tuple(waiting),
        carbon_facts=tuple(carbon_facts),
    )


def _run_b(waiting, carbon_facts=(), **snap_kwargs):
    state = _state(waiting, carbon_facts, **snap_kwargs)
    context = s.Context.build(state, f.snapshot(**snap_kwargs), "flat")
    return propose(state, context, system="greedy_b", decision_time_utc=f.SLOT0_UTC)


def _flex_job():
    return _job(duration_slots=2, deadline_slot=4, power_kw=30)


def _carbon_series(values, *, issued_at=f.SLOT0_UTC, id_prefix="GB"):
    return tuple(
        _carbon_fact(i, v, fact_id=f"FACT-{id_prefix}-s{i:02d}", issued_at=issued_at)
        for i, v in enumerate(values)
    )


def test_lowest_forecast_emissions():
    job = _flex_job()
    facts = _carbon_series((900, 900, 100, 100), id_prefix="LOW")
    output = _run_b((job,), facts)
    assert output.plan.starts[0].start_slot == 2, "lowest forecast emissions"


def test_earlier_start_on_equal_emissions():
    job = _flex_job()
    facts = _carbon_series((400, 400, 400, 400), id_prefix="FLAT")
    output = _run_b((job,), facts)
    assert output.plan.starts[0].start_slot == 0


def test_complete_fresh_stays_greedy_b():
    job = _flex_job()
    facts = _carbon_series((400, 400, 400, 400), id_prefix="FRESH")
    output = _run_b((job,), facts)
    assert output.system == "greedy_b"
    assert output.explanation is None


def test_missing_coverage_uses_greedy_a():
    job = _flex_job()
    state = _state((job,))
    context = s.Context.build(state, f.snapshot(), "flat")
    greedy_a = propose(state, context)
    output = propose(state, context, system="greedy_b", decision_time_utc=f.SLOT0_UTC)
    assert output.system == "greedy_a"
    assert output.explanation is not None
    assert output.explanation.summary == "missing"
    assert output.plan.starts == greedy_a.plan.starts


def test_stale_forecast_uses_greedy_a():
    job = _flex_job()
    stale_issued = f.SLOT0_UTC - timedelta(hours=3)
    facts = _carbon_series((400, 400, 400, 400), issued_at=stale_issued, id_prefix="STALE")
    output = _run_b((job,), facts)
    assert output.system == "greedy_a"
    assert output.explanation.summary == "stale", "stale forecast uses greedy_a"


def test_future_coverage_uses_greedy_a():
    job = _flex_job()
    future_issued = f.SLOT0_UTC + timedelta(hours=1)
    facts = _carbon_series((400, 400, 400, 400), issued_at=future_issued, id_prefix="FUT")
    output = _run_b((job,), facts)
    assert output.system == "greedy_a"
    assert output.explanation.summary == "future"


def test_partial_coverage_uses_greedy_a():
    job = _flex_job()
    facts = (_carbon_fact(0, 400, fact_id="FACT-PART-s00"),)
    output = _run_b((job,), facts)
    assert output.system == "greedy_a"
    assert output.explanation.summary == "partial"


def test_beyond_horizon_uses_greedy_a():
    job = _job(duration_slots=3, deadline_slot=25, power_kw=30)
    facts = _carbon_series((400,) * 24, id_prefix="BH")
    output = _run_b((job,), facts)
    assert output.system == "greedy_a"
    assert output.explanation.summary == "beyond-horizon"
