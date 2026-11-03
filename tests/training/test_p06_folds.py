"""Synthetic fold-scoring tests; never load the actual private corpus."""

from dataclasses import replace

import pytest

from dc_sustainability.training.dataset import LabeledRow
from dc_sustainability.training.pipeline import LabeledCorpus
from scripts import score_p06_folds as scorer


def corpus():
    rows = tuple(
        LabeledRow(f"EP-SYNTHETIC-{fold}", i, f"J{i}", i, (float(i),) * 8, bool(i % 2))
        for fold in range(3)
        for i in range(4)
    )
    return LabeledCorpus((), {f"EP-SYNTHETIC-{i}": i for i in range(3)}, rows, {})


def test_fits_only_training_folds_and_scores_each_row_once(tmp_path, monkeypatch):
    original = scorer.fit_model
    calls = []

    def record(spec, rows, *, seed):
        calls.append({row.episode_id for row in rows})
        assert len(calls[-1]) == 2
        return original(spec, rows, seed=seed)

    monkeypatch.setattr(scorer, "fit_model", record)
    report = scorer.evaluate(corpus(), tmp_path / "new")
    assert len(report["folds"]) == len(calls) == 15
    assert len(list((tmp_path / "new").glob("*.joblib"))) == 15
    for index, item in enumerate(report["folds"]):
        assert f"EP-SYNTHETIC-{item['fold']}" not in calls[index]
        assert item["scored"] == 4
        assert item["support_positive"] == item["support_negative"] == 2
    for item in report["pooled_by_spec"]:
        assert item["scored"] == 12
    assert report["excluded_before_saved_corpus"] is None
    assert report["held_out_access"] is report["selection_changed"] is False
    with pytest.raises(FileExistsError):
        scorer.evaluate(corpus(), tmp_path / "new")


@pytest.mark.parametrize("problem", ["unknown", "duplicate", "invalid_label", "nan"])
def test_invalid_development_rows_rejected(tmp_path, problem):
    data = corpus()
    row = data.rows[0]
    if problem == "unknown":
        row = replace(row, episode_id="EP-NOT-IN-DEVELOPMENT")
    elif problem == "invalid_label":
        row = replace(row, label=1)
    elif problem == "nan":
        row = replace(row, features=(float("nan"),) * 8)
    rows = (*data.rows, row) if problem == "duplicate" else (row, *data.rows[1:])
    with pytest.raises(ValueError):
        scorer.evaluate(replace(data, rows=rows), tmp_path / "new")
    assert not (tmp_path / "new").exists()
