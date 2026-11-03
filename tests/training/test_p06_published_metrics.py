"""Check public measured-table arithmetic without reading private data."""

import json
from pathlib import Path

import pytest

from dc_sustainability.training.metrics import CandidateScore, sum_candidate_scores


def test_actual_development_report_has_complete_folds_and_reproducible_rates():
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / "models/development_fold_metrics_2026-11-02.json").read_text())
    assert report["definite_rows"] == 6046 and report["episode_count"] == 40
    assert report["held_out_access"] is report["selection_changed"] is False
    assert report["model_requests"] == 0
    assert report["excluded_before_saved_corpus"] is None
    assert len(report["folds"]) == 15 and len(report["pooled_by_spec"]) == 5
    for aggregate in report["pooled_by_spec"]:
        parts = [row for row in report["folds"] if row["spec"] == aggregate["spec"]]
        assert {row["fold"] for row in parts} == {0, 1, 2}
        scores = []
        for row in parts:
            score = CandidateScore(
                *(
                    row[key]
                    for key in (
                        "true_positive",
                        "false_positive",
                        "true_negative",
                        "false_negative",
                        "excluded",
                    )
                )
            )
            assert row["fit_seconds"] >= 0 and row["score_seconds"] >= 0
            assert len(row["refit_sha256"]) == 64
            for key in ("precision", "recall", "f1"):
                assert row[key] == pytest.approx(getattr(score, key))
            scores.append(score)
        pooled = sum_candidate_scores(scores)
        assert pooled.support_positive == 1411 and pooled.support_negative == 4635
        for key in (
            "precision",
            "recall",
            "f1",
            "true_positive",
            "false_positive",
            "true_negative",
            "false_negative",
        ):
            assert aggregate[key] == pytest.approx(getattr(pooled, key))
