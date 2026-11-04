"""Synthetic executable specification CF60-v1; never a study adapter/default.

Only timestamp-keyed synthetic history enters this function. Values in private
realized episodes, future arrivals, seeds and outcomes are not arguments.
"""

from datetime import date, datetime, timedelta, timezone
from math import isfinite

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data.forecast_isolation import footprint
from dc_sustainability.verification.rules import assess_forecasts
from tests.contracts import fixtures as f

H = timedelta(hours=1)
ORIGIN = datetime(2022, 1, 1, tzinfo=timezone.utc)
STOP = datetime(2023, 1, 1, tzinfo=timezone.utc)


def utc_hour(value):
    if (
        not isinstance(value, datetime)
        or value.utcoffset() != timedelta(0)
        or value.minute
        or value.second
        or value.microsecond
    ):
        raise ValueError("explicit UTC hour required")


def labels(issue, convention):
    utc_hour(issue)
    if convention not in {"start", "end"}:
        raise ValueError("explicit interval hypothesis required")
    # Interval completion E, availability E+1h; equality with issue is excluded.
    return tuple(issue - k * H - (H if convention == "start" else 0 * H) for k in (2, 3, 4))


def proposal(history, anchor, slot, convention):
    """Read all present candidate values, latest timestamp wins, no other search.

    Reads include nonselected candidates. Missing candidate keys are recorded as
    attempted accesses. Invalid evidence fails rather than changing selection.
    """
    utc_hour(anchor)
    if type(slot) is not int or not 0 <= slot < 30:
        raise ValueError("slot 0..29 required")
    issue = anchor + slot * H
    attempts = labels(issue, convention)
    reads = tuple(label for label in attempts if ORIGIN <= label < STOP and label in history)
    values = tuple(history[label] for label in reads)
    if any(type(v) not in (float, int) or not isfinite(v) or v < 0 for v in values):
        raise ValueError("invalid source evidence")
    selected = reads[0] if reads else None
    latent = {} if selected is None else dict.fromkeys(range(slot, 30), values[0])
    visible = {v: x for v, x in latent.items() if v < min(slot + 24, 30)}
    return issue, attempts, reads, selected, latent, visible


def synthetic():
    return {ORIGIN + i * H: 10000 + i for i in range(8760)}


def sets(anchor, convention):
    history = synthetic()
    score = {anchor + t * H + (H if convention == "end" else 0 * H) for t in range(30)}
    reads = set().union(*(set(proposal(history, anchor, t, convention)[2]) for t in range(30)))
    return score, reads


@pytest.mark.parametrize("convention", ["start", "end"])
def test_all_issues_causal_deterministic_and_full_horizon(convention):
    anchor = ORIGIN + 100 * H
    history = synthetic()
    for t in range(30):

        class TrackedHistory(dict):
            def __getitem__(self, key):
                accesses.append(key)
                return super().__getitem__(key)

        accesses = []
        result = proposal(TrackedHistory(history), anchor, t, convention)
        assert tuple(accesses) == result[2]
        issue, _, reads, selected, latent, visible = result
        assert set(latent) == set(range(t, 30))
        assert set(visible) == set(range(t, min(t + 24, 30)))
        for label in reads:
            end = label + (H if convention == "start" else 0 * H)
            assert end + H < issue
            assert 2 * H <= issue - end <= 4 * H
        assert set(latent.values()) == {history[selected]}
        # Change every value not read, including all future/scoring outcomes.
        changed = {k: v if k in reads else 999999 for k, v in history.items()}
        assert proposal(changed, anchor, t, convention) == result
        assert proposal(dict(reversed(list(history.items()))), anchor, t, convention) == result
    assert (
        proposal(history, anchor, 0, convention)[4][29]
        == history[proposal(history, anchor, 0, convention)[3]]
    )


@pytest.mark.parametrize("convention", ["start", "end"])
def test_missing_history_and_no_unbounded_or_future_backfill(convention):
    anchor = ORIGIN + 100 * H
    expected = labels(anchor, convention)
    assert proposal({expected[1]: 222}, anchor, 0, convention)[3] == expected[1]
    for history in ({}, {expected[-1] - H: 111}, {anchor: 999}):
        result = proposal(history, anchor, 0, convention)
        assert result[3] is None and result[4] == result[5] == {}
    with pytest.raises(ValueError, match="invalid source"):
        proposal({expected[0]: float("nan")}, anchor, 0, convention)


@pytest.mark.parametrize("convention", ["start", "end"])
def test_year_edges_never_wrap(convention):
    history = synthetic()
    assert proposal(history, ORIGIN, 0, convention)[3] is None
    assert proposal(history, ORIGIN, 0, convention)[2] == ()
    # Dec 31 Phoenix midnight +29h = Jan 1 12Z: no previous-year wrapping.
    anchor = datetime(2022, 12, 31, 7, tzinfo=timezone.utc)
    assert proposal(history, anchor, 0, convention)[3] is not None
    assert proposal(history, anchor, 29, convention)[3] is None
    # A physical score row outside the pinned year fails full-window preflight.
    with pytest.raises(ValueError, match="never wrap"):
        footprint(date(2022, 12, 31), history_hours=5, convention=convention)


@pytest.mark.parametrize(
    "bad",
    [
        datetime(2022, 1, 1),
        ORIGIN + timedelta(minutes=1),
        ORIGIN.astimezone(timezone(timedelta(hours=1))),
    ],
)
def test_issue_requires_explicit_utc_hour(bad):
    with pytest.raises(ValueError, match="UTC hour"):
        proposal({}, bad, 0, "start")


def test_q04_issue_age_is_separate_from_history_age():
    snap = f.snapshot()
    state = f.visible_state(snap)
    for age, expected in ((0, ()), (2, ()), (3, ("stale",)), (-1, ("future_issued",))):
        facts = tuple(
            fact.model_copy(update={"issued_at_utc": f.SLOT0_UTC - age * H})
            for fact in state.carbon_facts
        )
        view = state.model_copy(update={"carbon_facts": facts})
        result = assess_forecasts(view, snap, decision_time_utc=f.SLOT0_UTC)
        assert result.reasons == expected
    missing = state.model_copy(update={"carbon_facts": ()})
    assert assess_forecasts(missing, snap, decision_time_utc=f.SLOT0_UTC).missing_slots


@pytest.mark.parametrize("convention", ["start", "end"])
def test_projection_uses_existing_f02_without_private_fields(convention):
    snap = f.snapshot()
    template = f.forecasts()[0]
    for t in range(30):
        issue, _, _, _, _, visible = proposal(synthetic(), f.SLOT0_UTC, t, convention)
        facts = tuple(
            s.CarbonForecast.from_jsonable(
                template.model_copy(
                    update={
                        "fact_id": f"FACT-CF60-{t}-{v}",
                        "value": value,
                        "issued_at_utc": issue,
                        "valid_slot": v,
                        "forecast_kind": "persistence",
                    }
                ).to_jsonable()
            )
            for v, value in visible.items()
        )
        state = f.visible_state(snap, current_slot=t).model_copy(update={"carbon_facts": facts})
        parsed = s.VisibleState.from_jsonable(state.to_jsonable())
        context = s.Context.build(parsed, snap, representation="flat")
        assert context
        assert {fact.valid_slot for fact in parsed.carbon_facts} == set(visible)
        assert "realized_carbon" not in parsed.to_jsonable()
        assert "future_arrivals" not in parsed.to_jsonable()


@pytest.mark.parametrize("convention", ["start", "end"])
@pytest.mark.parametrize("reverse", [False, True])
def test_bidirectional_history_overlap_and_conservative_envelope(convention, reverse):
    a = datetime(2022, 6, 14, 7, tzinfo=timezone.utc)
    b = a + 33 * H  # disjoint score windows but history enters the earlier score
    dev, held = (b, a) if reverse else (a, b)
    ds, dr = sets(dev, convention)
    hs, hr = sets(held, convention)
    assert not ds & hs
    assert (dr & hs) if reverse else (hr & ds)
    assert (dr & hs) | (hr & ds)
    for anchor in (a,):
        score, reads = sets(anchor, convention)
        env_score, env_reads = footprint(anchor.date(), history_hours=5, convention=convention)

        def to_rows(xs):
            return {int((x - ORIGIN) / H) for x in xs}

        assert to_rows(score) == env_score
        assert to_rows(reads) < env_reads  # strict superset, not exact dependencies
    distant_score, distant_reads = sets(a + 40 * H, convention)
    early_score, early_reads = sets(a, convention)
    assert not (distant_reads & early_score) | (early_reads & distant_score)


def test_same_hour_yesterday_counterexample():
    issue = ORIGIN + 100 * H
    valid = issue + 29 * H
    label = valid - 24 * H
    assert label == issue + 5 * H > issue


@pytest.mark.parametrize("convention", ["start", "end"])
def test_independent_completion_availability_and_exact_footprint(convention):
    history = synthetic()
    anchor = datetime(2022, 6, 1, 7, tzinfo=timezone.utc)
    union = set()
    for t in range(30):
        issue, attempts, reads, selected, latent, _ = proposal(history, anchor, t, convention)
        # Independent oracle: derive physical intervals from every synthetic label,
        # then filter by availability and evidence age, without calling labels().
        expected = []
        for label in history:
            physical_start = label if convention == "start" else label - H
            completion = physical_start + H
            availability = completion + H
            if availability < issue and timedelta(0) <= issue - completion <= 4 * H:
                expected.append(label)
        expected.sort(reverse=True)
        assert tuple(expected) == attempts == reads
        assert selected == expected[0]
        assert all(value == history[selected] for value in latent.values())
        # Candidate magnitudes cannot rerank the selected timestamp.
        changed = dict(history)
        changed.update({label: n for n, label in enumerate(expected)})
        assert proposal(changed, anchor, t, convention)[3] == selected
        union.update(reads)
    first = anchor - (5 if convention == "start" else 4) * H
    assert union == {first + i * H for i in range(32)}


@pytest.mark.parametrize("convention", ["start", "end"])
def test_explicit_f02_missing_slots_and_january_history(convention):
    snap = f.snapshot()
    for t in (0, 23, 29):
        _, _, reads, selected, latent, visible = proposal({}, f.SLOT0_UTC, t, convention)
        assert reads == () and selected is None and latent == visible == {}
        expected = tuple(range(t, min(t + 24, 30)))
        state = f.visible_state(snap, current_slot=t).model_copy(
            update={"carbon_facts": (), "missing_carbon_slots": expected}
        )
        parsed = s.VisibleState.from_jsonable(state.to_jsonable())
        assert parsed.missing_carbon_slots == expected
        assert not parsed.carbon_facts
        assert s.Context.build(parsed, snap, representation="flat")
    # January 1 Phoenix midnight has prior rows within the pinned year.
    assert proposal(synthetic(), f.SLOT0_UTC, 0, convention)[3] is not None
