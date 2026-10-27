"""D04 tests use date metadata only; no held-out inputs/labels are generated or read."""

import json
import random
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from dc_sustainability.data import carbon_source, scenarios, splits
from dc_sustainability.data.splits import (
    Allocation,
    Window,
    blocked_folds,
    digest,
    overlap_report,
    propose_allocation,
    validate_isolation,
    write_private_manifest,
)
from dc_sustainability.schemas import VisibleState
from tests.contracts import fixtures as f

REVISION = "a" * 40  # synthetic revision marker, never a scientific artifact
DEV = tuple(date(2022, month, day) for month in range(1, 13) for day in range(1, 15))
HELD = tuple(date(2022, month, day) for month in range(1, 13) for day in range(15, 29))


def proposal(**kwargs):
    return propose_allocation(
        **(
            dict(development_candidates=DEV, held_out_candidates=HELD, date_seed=42, job_seed=19)
            | kwargs
        )
    )


def record(name, day, *, partition="development", group=None, fold=None):
    return Allocation(name, partition, "normal", 1, Window(day), group or name, fold=fold)


def test_counts_determinism_candidate_order_and_rng_isolation():
    random.seed(53)
    before = random.getstate()
    first = proposal()
    assert random.getstate() == before
    assert first == proposal(development_candidates=DEV[::-1], held_out_candidates=HELD[::-1])
    assert first != proposal(date_seed=43)
    assert first != proposal(job_seed=20)
    dev = first.development_records()
    held = [r for r in first.records if r.partition == "held_out"]
    assert len(dev) == 40 and len(held) == 30
    assert Counter(r.scenario for r in dev) == dict.fromkeys(splits.SCENARIOS, 10)
    assert len({r.window.day for r in dev}) == 10
    assert len({r.window.day for r in held}) == len({r.window.day.month for r in held}) == 6
    assert all(1 <= r.window.day.day <= 14 for r in dev)
    assert all(15 <= r.window.day.day <= 28 for r in held)
    assert len({r.episode_id for r in first.records}) == 70
    assert len({r.seed for r in first.records}) == 64  # six intentionally paired variants
    assert Counter(r.fold for r in dev) == {0: 16, 1: 12, 2: 12}
    for variant in (r for r in held if r.withheld):
        parent = next(r for r in held if r.episode_id == variant.parent_id)
        assert parent.scenario == "normal" and not parent.withheld
        assert parent.seed == variant.seed and parent.window == variant.window


@pytest.mark.parametrize("seed", range(12))
def test_many_metadata_seeds_are_isolated(seed):
    plan = proposal(date_seed=seed)
    validate_isolation(plan.records)
    by_id = {r.episode_id: r for r in plan.records}
    for left, right in overlap_report(plan.records):
        a, b = by_id[left], by_id[right]
        assert a.partition == b.partition and a.fold == b.fold
    # Three contiguous chronological blocks, with no later fold before an earlier one.
    dev = sorted(plan.development_records(), key=lambda r: r.window.start)
    assert [r.fold for r in dev] == sorted(r.fold for r in dev)


def test_30_hour_boundaries_and_next_day_tail():
    window = Window(date(2022, 1, 1))
    assert window.indices == tuple(range(7, 37))
    assert window.start.isoformat() == "2022-01-01T07:00:00+00:00"
    assert window.end.isoformat() == "2022-01-02T13:00:00+00:00"
    assert window.overlaps(Window(date(2022, 1, 2)))
    assert not window.overlaps(Window(date(2022, 1, 3)))
    assert Window(date(2022, 12, 30)).indices[-1] == 8748
    for day in (date(2021, 12, 31), date(2022, 12, 31), date(2023, 1, 1)):
        with pytest.raises(ValueError, match="no wrapping"):
            Window(day)
    assert window.metadata()["source_interval_semantics"] == "unverified"
    assert "proposed" in window.metadata()["mapping"]


def test_day_14_to_15_cross_partition_rejected():
    # Disjoint date-number sets still share six completion/source hours.
    a = record("A", date(2022, 1, 14), fold=0)
    b = record("B", date(2022, 1, 15), partition="held_out")
    assert set(a.window.indices) & set(b.window.indices) == set(range(343, 349))
    assert overlap_report((b, a)) == (("A", "B"),)
    with pytest.raises(ValueError, match="cross-partition"):
        validate_isolation((a, b))


def test_source_identity_and_cross_month_intersection():
    a = record("A", date(2022, 1, 31), fold=0)
    b = record("B", date(2022, 2, 1), fold=1)
    with pytest.raises(ValueError, match="cross-fold"):
        validate_isolation((a, b))
    different_bytes = replace(b, window=Window(b.window.day, "b" * 64))
    assert overlap_report((a, different_bytes)) == ()
    validate_isolation((a, different_bytes))
    # Explicit related identity still groups different byte sources.
    with pytest.raises(ValueError, match="cross-fold"):
        validate_isolation((a, replace(different_bytes, related_group=a.related_group)))


def test_transitive_components_and_related_nonadjacent_dates():
    rows = (
        record("A", date(2022, 1, 1)),
        record("B", date(2022, 1, 2)),
        record("C", date(2022, 1, 3)),
        record("D", date(2022, 2, 1), group="A"),
        record("E", date(2022, 3, 1)),
        record("F", date(2022, 4, 1)),
    )
    folded = blocked_folds(rows)
    assert [r.fold for r in folded] == [0, 0, 0, 0, 1, 2]
    assert blocked_folds(rows[::-1]) == folded[::-1]
    with pytest.raises(ValueError, match="three blocked folds"):
        blocked_folds(rows[:3])
    with pytest.raises(ValueError, match="development metadata only"):
        blocked_folds((replace(rows[0], partition="held_out"),))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"date_seed": True},
        {"job_seed": 1.1},
        {"development_candidates": ()},
        {"development_candidates": DEV + (DEV[0],)},
        {"development_candidates": (date(2022, 1, 15),)},
        {"held_out_candidates": (date(2022, 1, 14),)},
        {"held_out_candidates": tuple(date(2022, 1, d) for d in range(15, 29))},
        {"development_candidates": (date(2022, 1, 1),)},
    ],
)
def test_invalid_or_insufficient_candidates_fail_without_relaxation(kwargs):
    with pytest.raises(ValueError):
        proposal(**kwargs)


def test_selection_rejects_boundary_overlap_without_resampling():
    dev = tuple(date(2022, month, 14) for month in range(1, 11))
    held = tuple(date(2022, month, 15) for month in range(1, 7))
    with pytest.raises(ValueError, match="insufficient isolated.*held_out"):
        proposal(development_candidates=dev, held_out_candidates=held)


def test_manifest_provenance_hashes_and_no_content():
    plan = proposal()
    manifest = plan.private_manifest(code_revision=REVISION)
    assert manifest == plan.private_manifest(code_revision=REVISION)
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    assert digest(body) == manifest["manifest_sha256"]
    assert digest(json.loads(json.dumps(body))) == manifest["manifest_sha256"]
    assert manifest["scientific_acceptance"] is False
    assert manifest["held_out_contents_generated"] is False
    assert manifest["source"]["sha256"] == carbon_source.SHA256
    assert manifest["generator_version"] == scenarios.GENERATOR_VERSION
    assert manifest["runtime"]["python"]
    assert len(manifest["code_file_sha256"]) == 4
    for row in manifest["records"]:
        assert row["episode_content_sha256"] is None
        assert len(row["window"]["proposed_physical_indices"]) == 30
        assert (
            digest({k: v for k, v in row.items() if k != "allocation_sha256"})
            == row["allocation_sha256"]
        )
    changed = dict(body, date_seed=100)
    assert digest(changed) != manifest["manifest_sha256"]
    with pytest.raises(ValueError, match="exact code revision"):
        plan.private_manifest(code_revision="main")


def test_no_carbon_or_job_access_and_development_boundary(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("allocation touched episode contents or source values")

    monkeypatch.setattr(scenarios, "generate_episode", forbidden)
    monkeypatch.setattr(scenarios, "generate_jobs", forbidden)
    monkeypatch.setattr(carbon_source, "load_source", forbidden)
    monkeypatch.setattr(carbon_source, "retrieve_source", forbidden)
    plan = proposal()
    dev = plan.development_records()
    held_id = next(r.episode_id for r in plan.records if r.partition == "held_out")
    assert all(r.partition == "development" for r in dev)
    with pytest.raises(ValueError, match="held-out access is unavailable"):
        plan.development_record(held_id)
    assert plan.development_record(dev[0].episode_id) == dev[0]
    visible = f.visible_state().to_jsonable()
    assert "realized_carbon" not in visible
    with pytest.raises(ValidationError):
        VisibleState.model_validate(visible | {"d04_allocation": dev[0].metadata()})
    assert not hasattr(plan, "held_out_episode")


def test_private_writes_exclusive_outside_checkout(tmp_path):
    plan = proposal()
    output = write_private_manifest(plan, tmp_path, code_revision=REVISION)
    original = output.read_bytes()
    assert json.loads(original)["held_out_contents_generated"] is False
    with pytest.raises(FileExistsError):
        write_private_manifest(plan, tmp_path, code_revision=REVISION)
    assert output.read_bytes() == original
    with pytest.raises(ValueError, match="outside Git"):
        write_private_manifest(plan, Path(__file__).resolve().parents[2], code_revision=REVISION)


def test_corrupted_counts_parents_and_fold_labels_rejected():
    plan = proposal()
    with pytest.raises(ValueError, match="40 development"):
        replace(plan, records=plan.records[:-1]).validate()
    first = plan.records[0]
    with pytest.raises(ValueError, match="duplicate episode"):
        validate_isolation((first, first))
    same_day = next(r for r in plan.records[1:] if r.window == first.window)
    with pytest.raises(ValueError, match="cross-fold"):
        validate_isolation((first, replace(same_day, fold=(first.fold + 1) % 3)))
    variant = next(r for r in plan.records if r.withheld)
    with pytest.raises(ValueError, match="variant must retain"):
        validate_isolation(
            tuple(replace(r, seed=r.seed + 1) if r == variant else r for r in plan.records)
        )
    with pytest.raises(ValueError, match="development fold missing"):
        validate_isolation((replace(first, fold=None),))


def test_window_validation():
    with pytest.raises(ValueError, match="must be a date"):
        Window("2022-01-01")
    with pytest.raises(ValueError, match="SHA-256"):
        Window(date(2022, 1, 1), "alias")


def test_development_export_omits_held_metadata_and_root_seeds():
    plan = proposal()
    dev = plan.development_manifest(code_revision=REVISION)
    assert len(dev["records"]) == 40
    assert all(r["partition"] == "development" for r in dev["records"])
    assert {r["episode_id"] for r in dev["records"]}.isdisjoint(
        r.episode_id for r in plan.records if r.partition == "held_out"
    )
    for forbidden in ("job_seed", "date_seed", "held_out_candidates", "development_candidates"):
        assert forbidden not in dev
    assert dev["manifest_sha256"] == digest(
        {k: v for k, v in dev.items() if k != "manifest_sha256"}
    )


def test_related_groups_absorb_intervening_dates_for_chronological_folds():
    rows = (
        record("A", date(2022, 1, 1), group="G"),
        record("B", date(2022, 1, 15)),
        record("C", date(2022, 2, 1), group="G"),
        record("D", date(2022, 3, 1)),
        record("E", date(2022, 4, 1)),
    )
    assert [r.fold for r in blocked_folds(rows)] == [0, 0, 0, 1, 2]


def test_provenance_uses_actual_code_bytes_and_runtime():
    import hashlib
    import platform

    manifest = proposal().private_manifest(code_revision=REVISION)
    root = Path(splits.__file__).resolve().parents[1]
    for name, sha in manifest["code_file_sha256"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha
    assert manifest["runtime"]["python"] == platform.python_version()
    assert "pydantic" in manifest["runtime"]


def test_recorded_seed_and_chronological_fold_proposal_cannot_be_silently_changed():
    plan = proposal()
    first = plan.records[0]
    with pytest.raises(ValueError, match="seed differs"):
        replace(plan, records=(replace(first, seed=first.seed + 1),) + plan.records[1:]).validate()
    swapped = tuple(
        replace(r, fold={0: 1, 1: 0, 2: 2}[r.fold]) if r.partition == "development" else r
        for r in plan.records
    )
    with pytest.raises(ValueError, match="chronological block"):
        replace(plan, records=swapped).validate()


def test_date_seed_and_ids_must_match_recorded_selection():
    plan = proposal()
    with pytest.raises(ValueError, match="selected dates differ"):
        replace(plan, date_seed=43).validate()
    with pytest.raises(ValueError, match="ID/group differs"):
        replace(
            plan, records=(replace(plan.records[0], episode_id="EP-forged"),) + plan.records[1:]
        ).validate()
