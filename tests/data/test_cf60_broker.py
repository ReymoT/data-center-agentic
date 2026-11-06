"""Production boundary tests with synthetic values only."""

import json
from datetime import timedelta

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data import cf60_broker as b
from dc_sustainability.data.cf60_receiving import development_footprints, receive
from dc_sustainability.data.materialize_development import allocation
from dc_sustainability.verification.rules import assess_forecasts
from tests.contracts import fixtures as f

A = b.ORIGIN + 100 * b.H
SOURCE = s.SourceRef(
    source_id="SRC-HAND",
    path="synthetic://test",
    sha256="a" * 64,
    redistribution_status="unresolved",
)


def cap(rows=(), issue=A, interpretation="start"):
    return b.RestrictedHistory(
        rows,
        issue=issue,
        interpretation=interpretation,
        source=SOURCE,
        authorization="synthetic-only",
    )


@pytest.mark.parametrize("interpretation", ["start", "end"])
def test_every_issue_projection_receipt_and_replay(interpretation):
    for slot in range(30):
        issue = A + slot * b.H
        labels = b.candidates(issue, interpretation)
        # Largest value belongs to oldest row: selection must use time.
        rows = list(zip(labels, (1, 500, 999)))
        result = b.issue_forecast(
            cap(rows, issue, interpretation), anchor=A, slot=slot, trusted_issue=issue
        )
        assert result == b.issue_forecast(
            cap(reversed(rows), issue, interpretation), anchor=A, slot=slot, trusted_issue=issue
        )
        assert {f.value for f in result.forecasts} == {1}
        assert [f.valid_slot for f in result.forecasts] == list(range(slot, min(slot + 24, 30)))
        receipt = json.loads(result.receipt_json)
        assert len(receipt["attempts"]) == 3
        assert all(e["status"] == "read" for e in receipt["attempts"])
        assert "value" not in result.receipt_json
        for fact in result.forecasts:
            assert s.CarbonForecast.from_jsonable(fact.to_jsonable()) == fact


@pytest.mark.parametrize("interpretation", ["start", "end"])
def test_missing_and_boundaries(interpretation):
    labels = b.candidates(A, interpretation)
    for rows, expected in (([], None), ([(labels[1], 222)], 222)):
        result = b.issue_forecast(
            cap(rows, interpretation=interpretation), anchor=A, slot=0, trusted_issue=A
        )
        assert (result.forecasts[0].value if result.forecasts else None) == expected
        assert result.missing_slots == (tuple(range(24)) if expected is None else ())
    for issue in (b.ORIGIN, b.STOP + 12 * b.H):
        result = b.issue_forecast(
            cap(issue=issue, interpretation=interpretation),
            anchor=issue,
            slot=0,
            trusted_issue=issue,
        )
        assert result.missing_slots == tuple(range(24))
        assert {e["status"] for e in json.loads(result.receipt_json)["attempts"]} == {"missing"}


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "12", None])
def test_bad_evidence(value):
    with pytest.raises(ValueError, match="malformed"):
        cap([(A - 3 * b.H, value)])


def test_access_faults_and_input_rejections():
    history = cap([(A - 3 * b.H, 1)])
    for label in (A, A + b.H, A - 6 * b.H, b.ORIGIN - b.H):
        with pytest.raises(PermissionError):
            history.read(label)
    assert len(history.footprint()) == 4
    assert all(e["status"] == "rejected" for e in history.footprint())
    with pytest.raises(ValueError, match="fresh"):
        b.issue_forecast(history, anchor=A, slot=0, trusted_issue=A)
    with pytest.raises(PermissionError):
        cap([(A, 999)])
    with pytest.raises(ValueError, match="duplicate"):
        cap([(A - 3 * b.H, 1), (A - 3 * b.H, 2)])
    with pytest.raises(TypeError):
        b.issue_forecast({}, anchor=A, slot=0, trusted_issue=A)
    with pytest.raises(ValueError, match="clock"):
        b.issue_forecast(cap(), anchor=A, slot=0, trusted_issue=A + b.H)
    with pytest.raises(ValueError, match="UTC"):
        cap(issue=A.replace(tzinfo=None))
    with pytest.raises(ValueError, match="UTC"):
        cap(issue=A + timedelta(minutes=1))


def test_receiving_and_fixed_development_metadata():
    report = receive()
    assert len(report["checks"]) == 60
    assert all(c["denied_reads"] == 8757 for c in report["checks"])
    manifest, _ = allocation()
    rows = development_footprints(manifest["records"])
    assert len(rows) == 40
    assert all(len(r["start_cf60_reads"]) == 32 for r in rows)
    assert all(len(r["end_cf60_reads"]) == 32 for r in rows)


def test_actual_f02_context_and_q04():
    # Use the fixture clock/snapshot with resolvable synthetic SRC-HAND provenance.
    issue = f.SLOT0_UTC
    result = b.issue_forecast(
        cap([(issue - 3 * b.H, 500)], issue=issue), anchor=issue, slot=0, trusted_issue=issue
    )
    snap = f.snapshot()
    assert "SRC-HAND" in {source.source_id for source in snap.sources}
    state = f.visible_state(snap).model_copy(update={"carbon_facts": result.forecasts})
    s.Context.build(s.VisibleState.from_jsonable(state.to_jsonable()), snap, representation="flat")
    for age, reason in ((0, ()), (2, ()), (3, ("stale",)), (-1, ("future_issued",))):
        facts = tuple(
            x.model_copy(update={"issued_at_utc": issue - age * b.H}) for x in result.forecasts
        )
        view = state.model_copy(update={"carbon_facts": facts})
        assert assess_forecasts(view, snap, decision_time_utc=issue).reasons == reason


def test_privileged_acquisition_copies_only_allowed_rows(monkeypatch):
    from dc_sustainability.data import cf60_acquisition as acquisition

    calls = []
    rows = [(b.ORIGIN + i * b.H, i + 1000) for i in range(8760)]

    def fake_load(path):
        calls.append(path)
        return tuple(rows), {"synthetic": True}

    monkeypatch.setattr(acquisition.carbon_source, "load_source", fake_load)
    history = acquisition.acquire(
        "SYNTHETIC-NOT-A-SOURCE", issue=A, interpretation="start", authorization="synthetic-only"
    )
    assert calls == ["SYNTHETIC-NOT-A-SOURCE"]
    rows.clear()  # Capability does not retain the full array/loader.
    with pytest.raises(AttributeError, match="immutable"):
        history.issue = A + b.H
    assert not hasattr(history, "__dict__")
    with pytest.raises(PermissionError):
        history.read(A)
    assert history.read(A - 3 * b.H) == 1097


def test_faulty_acquisition_and_missing_reissue(monkeypatch):
    from dc_sustainability.data import cf60_acquisition as acquisition

    def fail(_):
        raise ValueError("synthetic checksum failure")

    monkeypatch.setattr(acquisition.carbon_source, "load_source", fail)
    with pytest.raises(ValueError, match="checksum"):
        acquisition.acquire("SYNTHETIC", issue=A, interpretation="start", authorization="synthetic")
    first = b.issue_forecast(cap(), anchor=A, slot=0, trusted_issue=A)
    later = A + b.H
    second = b.issue_forecast(
        cap([(later - 3 * b.H, 4)], issue=later), anchor=A, slot=1, trusted_issue=later
    )
    assert first.missing_slots == tuple(range(24))
    assert second.forecasts and not second.missing_slots
    assert first.forecasts == ()  # Later evidence never backfills an earlier issue.


def test_receiving_detects_forged_log_with_unrestricted_reads(monkeypatch):
    # Fault injection: even a plausible three-ID receipt cannot hide accessible
    # unapproved rows from the independent active probes.
    original = b.RestrictedHistory.read

    def broken(self, label):
        try:
            return original(self, label)
        except PermissionError:
            return 888888

    monkeypatch.setattr(b.RestrictedHistory, "read", broken)
    with pytest.raises(ValueError, match="unauthorized row accessible"):
        receive()


def test_capability_metadata_cannot_be_deleted_and_reassigned():
    history = cap([(A - 3 * b.H, 1)])
    for name in ("issue", "interpretation", "source", "authorization"):
        with pytest.raises(AttributeError, match="immutable"):
            delattr(history, name)
    assert history.issue == A
    assert history.read(A - 3 * b.H) == 1


def test_privileged_source_objects_cannot_cross_boundary():
    class PrivilegedSource:
        sha256 = "a" * 64
        full_series = list(range(8760))

    class ExtendedSource(s.SourceRef):
        def unrestricted_loader(self):
            return list(range(8760))

    for source in (PrivilegedSource(), ExtendedSource(**SOURCE.to_jsonable())):
        with pytest.raises(TypeError, match="plain F02 SourceRef"):
            b.RestrictedHistory(
                (), issue=A, interpretation="start", source=source, authorization="synthetic-only"
            )
