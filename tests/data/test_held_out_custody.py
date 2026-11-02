"""Synthetic metadata authorization only; no actual study selection or episode inputs."""

import copy
import json
import os
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from dc_sustainability.data import held_out_custody as custody
from dc_sustainability.data import materialize_development as development
from dc_sustainability.data import splits
from dc_sustainability.training.folds import refuse_held_out_episodes

REVISION = "a" * 40


@pytest.fixture
def authorization(tmp_path):
    return {
        "version": custody.VERSION,
        "parameters": {
            "candidate_dates": [
                date(2022, month, day).isoformat()
                for month in range(1, 13)
                for day in range(15, 29)
            ],
            "selection_seed": 812345678901,
            "job_seed_root": 912345678901,
            "algorithm": custody.ALGORITHM,
        },
        "destination": str(tmp_path / "synthetic-custody"),
        "reimo_decision": "SYNTHETIC TEST ONLY, no human approval",
        "nisha_decision": "SYNTHETIC TEST ONLY, no human approval",
        "storage": {
            "platform": "synthetic test host",
            "access_control": "synthetic assertion, not verified study storage",
            "authorized_principals": "synthetic evaluator",
            "verification_record": "synthetic test only",
        },
        "scope": "metadata_only_not_freeze_or_run",
    }


def build(auth):
    return custody.build_metadata(auth, authorization_sha256=splits.digest(auth), revision=REVISION)


def test_fixed_development_and_30_design(authorization, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("joint allocator/content generation is forbidden")

    monkeypatch.setattr(splits, "propose_allocation", forbidden)
    monkeypatch.setattr(development, "episodes", forbidden)
    monkeypatch.setattr(custody.carbon, "load_source", forbidden)
    manifest = build(authorization)
    original, folds = development.allocation()
    dev = [r for r in manifest["records"] if r["partition"] == "development"]
    held = [r for r in manifest["records"] if r["partition"] == "held_out"]
    assert dev == original["records"]
    assert len(held) == 30
    assert len({r["window"]["date"] for r in held}) == 6
    assert len({r["window"]["date"][5:7] for r in held}) == 6
    assert all(15 <= date.fromisoformat(r["window"]["date"]).day <= 28 for r in held)
    assert len({r["episode_id"] for r in manifest["records"]}) == 70
    assert set(folds).isdisjoint(r["episode_id"] for r in held)
    by_id = {r["episode_id"]: r for r in held}
    for day in {r["window"]["date"] for r in held}:
        rows = [r for r in held if r["window"]["date"] == day]
        assert sorted(r["scenario"] for r in rows if not r["withheld"]) == sorted(splits.SCENARIOS)
        variants = [r for r in rows if r["withheld"]]
        assert len(variants) == 1
        variant = variants[0]
        parent = by_id[variant["parent_id"]]
        for field in ("seed", "window", "related_group", "scenario", "fold"):
            assert variant[field] == parent[field]
        assert parent["scenario"] == "normal" and not parent["withheld"]
    for r in held:
        assert r["episode_content_sha256"] is None
        assert r["fold"] is None
        assert not set(r["window"]["proposed_physical_indices"]) & {
            i for d in dev for i in d["window"]["proposed_physical_indices"]
        }
    assert {r["related_group"] for r in dev}.isdisjoint(r["related_group"] for r in held)
    with pytest.raises(ValueError):
        refuse_held_out_episodes([held[0]["episode_id"]], by_id)
    assert capsys.readouterr() == ("", "")


def test_deterministic_regeneration_and_external_custody(authorization, capsys):
    assert build(authorization) == build(copy.deepcopy(authorization))
    checksum = custody.prepare(
        authorization, authorization_sha256=splits.digest(authorization), revision=REVISION
    )
    custody.verify(
        authorization,
        authorization_sha256=splits.digest(authorization),
        revision=REVISION,
        external_sha256=checksum,
    )
    with pytest.raises(FileExistsError):
        custody.prepare(
            authorization, authorization_sha256=splits.digest(authorization), revision=REVISION
        )
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "empty",
        "bool",
        "negative",
        "too_large",
        "demo",
        "dev",
        "equal",
        "algorithm",
        "duplicate",
        "unsorted",
        "date",
        "pool",
    ],
)
def test_bad_parameters_fail_before_output(authorization, mutation):
    p = authorization["parameters"]
    if mutation == "missing":
        del p["job_seed_root"]
    elif mutation == "empty":
        p["candidate_dates"] = []
    elif mutation in ("bool", "negative", "too_large", "demo", "dev"):
        p["selection_seed"] = {
            "bool": True,
            "negative": -1,
            "too_large": 2**128,
            "demo": 42,
            "dev": 2026102801,
        }[mutation]
    elif mutation == "equal":
        p["job_seed_root"] = p["selection_seed"]
    elif mutation == "algorithm":
        p["algorithm"] = "invented"
    elif mutation == "duplicate":
        p["candidate_dates"].append(p["candidate_dates"][0])
    elif mutation == "unsorted":
        p["candidate_dates"].reverse()
    elif mutation == "date":
        p["candidate_dates"][0] = "2022-01-14"
    else:
        p["candidate_dates"] = ["2022-01-15"]
    with pytest.raises(ValueError):
        build(authorization)
    assert not Path(authorization["destination"]).exists()


@pytest.mark.parametrize(
    "mutation", ["digest", "decision", "scope", "storage", "revision", "destination"]
)
def test_authorization_fail_closed(authorization, mutation):
    kwargs = {"authorization_sha256": splits.digest(authorization), "revision": REVISION}
    if mutation == "digest":
        authorization["parameters"]["selection_seed"] += 1
    elif mutation == "revision":
        kwargs["revision"] = "not-a-sha"
    else:
        key = {
            "decision": "nisha_decision",
            "scope": "scope",
            "storage": "storage",
            "destination": "destination",
        }[mutation]
        authorization[key] = {} if mutation == "storage" else ""
        kwargs["authorization_sha256"] = splits.digest(authorization)
    with pytest.raises(ValueError):
        custody.build_metadata(authorization, **kwargs)


@pytest.mark.parametrize(
    "mutation", ["content", "receipt", "missing", "extra", "symlink", "external"]
)
def test_tampering_and_partial_fail_closed(authorization, mutation):
    checksum = custody.prepare(
        authorization, authorization_sha256=splits.digest(authorization), revision=REVISION
    )
    directory = Path(authorization["destination"])
    path = directory / "metadata.json"
    if mutation == "content":
        value = json.loads(path.read_bytes())
        value["records"][0]["seed"] += 1
        path.write_bytes(development.serialize(value))
    elif mutation == "receipt":
        (directory / "complete.sha256").write_text("0" * 64 + "\n")
    elif mutation == "missing":
        path.unlink()
    elif mutation == "extra":
        (directory / "unexpected").touch()
    elif mutation == "external":
        checksum = "0" * 64
    else:
        path.unlink()
        target = directory.parent / "target.json"
        target.write_text("{}")
        try:
            path.symlink_to(target)
        except OSError:
            pytest.skip("host cannot create symlink")
    with pytest.raises(ValueError):
        custody.verify(
            authorization,
            authorization_sha256=splits.digest(authorization),
            revision=REVISION,
            external_sha256=checksum,
        )


@pytest.mark.parametrize("kind", ["checkout", "worktree", "bare", "symlink"])
def test_outside_all_git_and_no_aliases(authorization, tmp_path, kind):
    root = tmp_path / "other"
    root.mkdir()
    if kind == "checkout":
        (root / ".git").mkdir()
    elif kind == "worktree":
        (root / ".git").write_text("gitdir: /unavailable/worktree")
    elif kind == "bare":
        for name in ("objects", "refs"):
            (root / name).mkdir()
        (root / "HEAD").touch()
    else:
        alias = tmp_path / "alias"
        try:
            alias.symlink_to(root, target_is_directory=True)
        except OSError:
            pytest.skip("host cannot create symlink")
        root = alias
    authorization["destination"] = str(root / "new")
    with pytest.raises(ValueError):
        build(authorization)


def test_corrupt_development_receipt_rejected(authorization, tmp_path, monkeypatch):
    original = development.allocation
    directory = tmp_path / "corrupt-dev"
    directory.mkdir()
    for path in development.ALLOCATION.iterdir():
        if path.is_file():
            (directory / path.name).write_bytes(path.read_bytes())
    (directory / "checksums.json").write_text("{}")
    monkeypatch.setattr(development, "allocation", lambda: original(directory))
    with pytest.raises(ValueError):
        build(authorization)


def test_parent_and_related_group_faults(authorization):
    records = custody._records(authorization["parameters"])
    variant = next(r for r in records if r.withheld)
    with pytest.raises(ValueError):
        splits.validate_isolation(
            tuple(replace(r, seed=r.seed + 1) if r == variant else r for r in records)
        )
    held = next(r for r in records if r.partition == "held_out")
    with pytest.raises(ValueError):
        splits.validate_isolation(
            tuple(
                replace(r, related_group=records[0].related_group) if r == held else r
                for r in records
            )
        )


@pytest.mark.parametrize(
    "day", [date(2022, 1, 1), date(2022, 1, 31), date(2022, 12, 30), date(2022, 12, 31)]
)
def test_all_30_conditional_slots_and_year_tails(day):
    rows = custody.interval_comparison(day)
    assert len(rows) == 30
    assert rows[0]["physical_start_utc"].endswith("07:00:00+00:00")
    assert rows[0]["start_label_utc"].endswith("07:00:00+00:00")
    assert rows[0]["end_label_utc"].endswith("08:00:00+00:00")
    for r in rows:
        if r["start_row"] is not None and r["end_row"] is not None:
            assert r["end_row"] == r["start_row"] + 1
    if day == date(2022, 1, 1):
        assert [r["start_row"] for r in rows] == list(range(7, 37))
        assert [r["end_row"] for r in rows] == list(range(8, 38))
    if day == date(2022, 1, 31):
        assert rows[-1]["physical_end_utc"] == "2022-02-01T13:00:00+00:00"
    if day == date(2022, 12, 31):
        assert rows[-1]["start_row"] is None and rows[-1]["end_row"] is None


def test_cross_month_tail_and_cross_partition_overlap():
    assert splits.Window(date(2022, 1, 31)).overlaps(splits.Window(date(2022, 2, 1)))
    dev = splits.Allocation(
        "dev", "development", "normal", 1, splits.Window(date(2022, 1, 14)), "dev", fold=0
    )
    held = splits.Allocation(
        "held", "held_out", "normal", 2, splits.Window(date(2022, 1, 15)), "held"
    )
    with pytest.raises(ValueError):
        splits.validate_isolation((dev, held))


def test_held_out_rows_excluded_from_preprocessing_and_training(authorization):
    from dc_sustainability.training.dataset import LabeledRow, rows_for_episodes
    from dc_sustainability.training.features import FEATURE_NAMES
    from dc_sustainability.training.folds import TrainOnlyScaler, blocked_fold_splits

    records = build(authorization)["records"]
    dev = [r for r in records if r["partition"] == "development"]
    held = [r for r in records if r["partition"] == "held_out"]
    width = len(FEATURE_NAMES)
    # Synthetic sentinel features, not generated jobs/carbon or evaluation labels.
    rows = tuple(
        LabeledRow(r["episode_id"], 0, "synthetic", 0, (0.0,) * width, False) for r in dev
    ) + tuple(LabeledRow(r["episode_id"], 0, "synthetic", 0, (1e9,) * width, False) for r in held)
    folds = {r["episode_id"]: r["fold"] for r in dev}
    for fold in blocked_fold_splits(folds):
        training = rows_for_episodes(rows, fold.train_episode_ids)
        assert all(row.episode_id in folds for row in training)
        scaler = TrainOnlyScaler.fit([r.features for r in training])
        assert scaler.means == (0.0,) * width
    assert len(rows_for_episodes(rows, folds)) == 40


def test_existing_partial_destination_not_resumed(authorization):
    path = Path(authorization["destination"])
    path.mkdir()
    (path / "partial").write_text("retained")
    with pytest.raises(FileExistsError):
        custody.prepare(
            authorization, authorization_sha256=splits.digest(authorization), revision=REVISION
        )
    assert (path / "partial").read_text() == "retained"


def test_changed_content_receipt_commitment_fails(authorization, monkeypatch):
    monkeypatch.setattr(custody, "DEVELOPMENT_CONTENT_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="development content commitments changed"):
        build(authorization)


def test_rehashed_tampering_still_fails_regeneration(authorization):
    import hashlib

    custody.prepare(
        authorization, authorization_sha256=splits.digest(authorization), revision=REVISION
    )
    path = Path(authorization["destination"])
    value = json.loads((path / "metadata.json").read_bytes())
    value["records"][-1]["seed"] += 1
    payload = development.serialize(value)
    checksum = hashlib.sha256(payload).hexdigest()
    (path / "metadata.json").write_bytes(payload)
    (path / "complete.sha256").write_text(checksum + "\n")
    with pytest.raises(ValueError, match="custody verification failed"):
        custody.verify(
            authorization,
            authorization_sha256=splits.digest(authorization),
            revision=REVISION,
            external_sha256=checksum,
        )


def test_year_boundary_has_no_end_label_for_final_source_hour():
    boundary = custody.interval_comparison(date(2022, 12, 31))
    assert boundary[16]["start_row"] == 8759
    assert boundary[16]["end_row"] is None
    assert boundary[17]["start_row"] is None


def test_junction_parent_rejected_before_output(authorization, monkeypatch):
    parent = Path(authorization["destination"]).parent
    monkeypatch.setattr(Path, "is_junction", lambda p: p == parent)
    with pytest.raises(ValueError, match="custody path rejected"):
        build(authorization)
    assert not Path(authorization["destination"]).exists()


def test_hardlinked_custody_file_rejected(authorization):
    checksum = custody.prepare(
        authorization, authorization_sha256=splits.digest(authorization), revision=REVISION
    )
    root = Path(authorization["destination"])
    os.link(root / "metadata.json", root.parent / "other-name.json")
    with pytest.raises(ValueError, match="custody files rejected"):
        custody.verify(
            authorization,
            authorization_sha256=splits.digest(authorization),
            revision=REVISION,
            external_sha256=checksum,
        )


def test_committed_generic_interval_comparison_matches_all_rows():
    artifact = (
        Path(__file__).resolve().parents[2] / "docs/handoffs/ISSUE60_INTERVAL_COMPARISON.json"
    )
    data = json.loads(artifact.read_text())
    assert data["source_values_read"] is False
    assert set(data["dates"]) == {"2022-01-01", "2022-01-31", "2022-12-30", "2022-12-31"}
    for day, rows in data["dates"].items():
        assert rows == list(custody.interval_comparison(date.fromisoformat(day)))
