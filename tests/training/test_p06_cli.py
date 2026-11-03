"""Synthetic scorer input and CLI regressions; not development-fold evidence."""

import json
import sys
from types import SimpleNamespace

import pytest

from dc_sustainability.training.features import FEATURE_NAMES
from dc_sustainability.training.train import ModelSpec, fit_model
from scripts import score_p06_development as cli


def row():
    return {
        "episode_id": "EP-SYNTHETIC",
        "job_id": "J1",
        "slot": 0,
        "start_slot": 0,
        "features": [0.0] * len(FEATURE_NAMES),
        "label": True,
    }


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_features_rejected(value):
    item = row()
    item["features"][0] = value
    with pytest.raises(ValueError, match="finite"):
        cli._labeled_rows([item])


@pytest.mark.parametrize(
    ("field", "value"),
    [("episode_id", " "), ("job_id", ""), ("slot", -1), ("start_slot", -1)],
)
def test_invalid_identity_or_slot_rejected(field, value):
    item = row()
    item[field] = value
    with pytest.raises(ValueError):
        cli._labeled_rows([item])


def test_cli_scoring_labels_caller_basis_and_uses_verified_loader(tmp_path, monkeypatch, capsys):
    positive = row()
    negative = row()
    negative.update(job_id="J2", label=False, features=[1.0] * len(FEATURE_NAMES))
    items = [positive, negative]
    fitted = fit_model(ModelSpec("decision_tree_c", 3), cli._labeled_rows(items), seed=7)
    rows_path = tmp_path / "synthetic.json"
    rows_path.write_text(json.dumps(items), encoding="utf-8")
    artifact_path = tmp_path / "synthetic.joblib"
    calls = []

    def loader(path, *, system):
        calls.append((path, system))
        return SimpleNamespace(fitted=fitted, artifact_sha256="synthetic-test-only", system=system)

    monkeypatch.setattr(cli, "load_published_development", loader)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scorer",
            "--artifact",
            str(artifact_path),
            "--rows",
            str(rows_path),
            "--system",
            "decision_tree_c",
            "--excluded",
            "2",
        ],
    )
    cli.main()
    result = json.loads(capsys.readouterr().out)
    assert calls == [(artifact_path, "decision_tree_c")]
    assert result["basis"] == "caller_rows"
    assert result["excluded"] == 2
    assert result["scored"] == 2
    assert result["true_positive"] == result["true_negative"] == 1
    assert result["f1"] == 1.0
    assert "not published development-fold" in result["note"]


def test_bad_artifact_is_not_scored(tmp_path, monkeypatch):
    rows_path = tmp_path / "synthetic.json"
    rows_path.write_text("[]", encoding="utf-8")
    artifact = tmp_path / "untrusted.joblib"
    artifact.write_bytes(b"not a published artifact")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scorer",
            "--artifact",
            str(artifact),
            "--rows",
            str(rows_path),
            "--system",
            "decision_tree_c",
        ],
    )
    with pytest.raises(ValueError):
        cli.main()
