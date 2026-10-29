"""Concrete #102 proposal: no actual source values or held-out allocation required."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from dc_sustainability.data import carbon_source, scenarios, splits
from dc_sustainability.data import development_folds as d
from dc_sustainability.schemas import VisibleState
from dc_sustainability.training.folds import blocked_fold_splits
from tests.contracts import fixtures

ARTIFACT = Path(__file__).resolve().parents[2] / "data/manifests/d04-development-20261028-v1"


def artifacts():
    return (
        json.loads((ARTIFACT / "manifest.json").read_text()),
        json.loads((ARTIFACT / "fold-map.json").read_text()),
    )


def test_actual_artifacts_regenerate_and_hash():
    manifest, projection = artifacts()
    assert manifest == json.loads(json.dumps(d.build_manifest()))
    assert (
        splits.digest({k: v for k, v in manifest.items() if k != "manifest_sha256"})
        == manifest["manifest_sha256"]
    )
    assert projection == manifest["fold_of_episode"]
    assert d.load_fold_map(manifest, projection) == projection
    for row in manifest["records"]:
        assert (
            splits.digest({k: v for k, v in row.items() if k != "allocation_sha256"})
            == row["allocation_sha256"]
        )
    checksums = json.loads((ARTIFACT / "checksums.json").read_text())
    assert set(checksums) == {"manifest.json", "fold-map.json"}
    for name, value in checksums.items():
        assert d.canonical_lf_sha256(ARTIFACT / name) == value


def test_source_checkout_line_endings_and_content_changes(monkeypatch):
    manifest, projection = artifacts()
    original = Path.read_bytes
    paths = set(manifest["code_file_sha256"])
    modified = False

    def checkout_bytes(path):
        value = original(path)
        if any(path.as_posix().endswith(p) for p in paths):
            value = value.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            if modified and path.name == "scenarios.py":
                value += b"# actual source modification\r\n"
        return value

    monkeypatch.setattr(Path, "read_bytes", checkout_bytes)
    assert json.loads(json.dumps(d.build_manifest())) == manifest
    assert d.load_fold_map(manifest, projection) == projection
    modified = True
    assert d.build_manifest()["code_file_sha256"] != manifest["code_file_sha256"]
    with pytest.raises(ValueError, match="manifest differs"):
        d.load_fold_map(manifest, projection)


@pytest.mark.parametrize("name", ["manifest.json", "fold-map.json", "checksums.json"])
def test_json_checkout_line_endings_preserve_integrity(tmp_path, name):
    original = (ARTIFACT / name).read_bytes().replace(b"\r\n", b"\n")
    path = tmp_path / name
    path.write_bytes(original.replace(b"\n", b"\r\n"))
    expected = hashlib.sha256(original).hexdigest()
    assert d.canonical_lf_sha256(path) == expected
    assert json.loads(path.read_bytes()) == json.loads(original)
    for changed in (original + b" ", original.rstrip(b"\n"), original.replace(b" ", b"  ", 1)):
        path.write_bytes(changed)
        assert d.canonical_lf_sha256(path) != expected


def test_canonical_lf_preserves_other_source_bytes(tmp_path):
    path = tmp_path / "source.py"
    value = b"# UTF-8: \xc3\xa9\nx = 1\n# lone CR: \r"
    path.write_bytes(value)
    expected = hashlib.sha256(value).hexdigest()
    assert d.canonical_lf_sha256(path) == expected
    path.write_bytes(value.replace(b"\n", b"\r\n"))
    assert d.canonical_lf_sha256(path) == expected
    path.write_bytes(value.replace(b"1", b"2"))
    assert d.canonical_lf_sha256(path) != expected


def test_actual_counts_coverage_and_p03_consumer():
    manifest, projection = artifacts()
    rows = d.proposed_records()
    assert len(rows) == len({r.episode_id for r in rows}) == len(projection) == 40
    assert Counter(r.scenario for r in rows) == dict.fromkeys(splits.SCENARIOS, 10)
    assert len({r.window.day for r in rows}) == 10
    assert all(r.window.day in d.CANDIDATES and r.partition == "development" for r in rows)
    assert Counter(projection.values()) == {0: 16, 1: 12, 2: 12}
    for fold in blocked_fold_splits(d.load_fold_map(manifest, projection)):
        assert fold.train_episode_ids.isdisjoint(fold.eval_episode_ids)
        assert fold.train_episode_ids | fold.eval_episode_ids == set(projection)
    splits.validate_isolation(rows)
    for left in rows:
        for right in rows:
            if left.related_group == right.related_group or left.window.overlaps(right.window):
                assert left.fold == right.fold


@pytest.mark.parametrize("mutation", ["missing", "extra", "held", "mismatch", "bool", "empty"])
def test_projection_fails_closed(mutation):
    manifest, projection = artifacts()
    first = next(iter(projection))
    if mutation == "missing":
        projection.pop(first)
    elif mutation in ("extra", "held"):
        projection["EP-restricted-test-sentinel"] = 0
    elif mutation == "mismatch":
        projection[first] = (projection[first] + 1) % 3
    elif mutation == "bool":
        projection[first] = bool(projection[first])
    else:
        projection = {}
    with pytest.raises(ValueError):
        d.load_fold_map(manifest, projection)


def test_manifest_corruption_and_custody_overlap_fail_closed():
    manifest, projection = artifacts()
    with pytest.raises(ValueError, match="held-out"):
        d.load_fold_map(manifest, projection, held_out_episode_ids=[next(iter(projection))])
    manifest["records"][0]["partition"] = "held_out"
    manifest["manifest_sha256"] = splits.digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    with pytest.raises(ValueError, match="manifest differs"):
        d.load_fold_map(manifest, projection)


def test_next_day_cross_month_tail_and_duplicate_rejection():
    row = d.proposed_records()[0]
    with pytest.raises(ValueError, match="duplicate"):
        splits.validate_isolation((row, row))
    window = splits.Window(date(2022, 1, 31))
    assert len(window.indices) == 30
    assert window.end.isoformat() == "2022-02-01T13:00:00+00:00"
    assert window.overlaps(splits.Window(date(2022, 2, 1)))
    assert not window.overlaps(splits.Window(date(2022, 2, 2)))
    assert splits.Window(date(2022, 1, 14)).overlaps(splits.Window(date(2022, 1, 15)))


def test_no_content_access_or_held_selection_and_no_policy_metadata(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("content access forbidden")

    for module, name in (
        (carbon_source, "load_source"),
        (carbon_source, "retrieve_source"),
        (scenarios, "generate_episode"),
        (scenarios, "generate_jobs"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    manifest = d.build_manifest()
    assert not manifest["held_out_allocation_generated"]
    assert not manifest["scientific_acceptance"]
    assert all(r["episode_content_sha256"] is None for r in manifest["records"])
    assert "held_out_candidates" not in manifest and "date_seed" not in manifest
    visible = fixtures.visible_state().to_jsonable()
    for key, value in (
        ("fold_of_episode", manifest["fold_of_episode"]),
        ("d04_allocation", manifest["records"][0]),
        ("realized_carbon", [1.0]),
    ):
        with pytest.raises(ValidationError):
            VisibleState.model_validate(visible | {key: value})
