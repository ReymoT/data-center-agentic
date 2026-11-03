"""Recompute development-only candidate metrics from a trusted local labeled corpus.

No source download, reference solving, model requests or held-out access. Joblib
is executable input: use only the manager-produced corpus with its expected hash.
Outputs are new fold refits, not replacements for frozen C/D policy artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib  # noqa: E402

from dc_sustainability.data.materialize_development import allocation  # noqa: E402
from dc_sustainability.training.dataset import rows_for_episodes  # noqa: E402
from dc_sustainability.training.folds import blocked_fold_splits  # noqa: E402
from dc_sustainability.training.metrics import score_fitted_rows, sum_candidate_scores  # noqa: E402
from dc_sustainability.training.pipeline import LabeledCorpus  # noqa: E402
from dc_sustainability.training.train import (  # noqa: E402
    DEVELOPMENT_SEED,
    fit_model,
    grid_specs,
    save_artifact,
)


def cells(score):
    return {
        name: getattr(score, name)
        for name in (
            "true_positive",
            "false_positive",
            "true_negative",
            "false_negative",
            "support_positive",
            "support_negative",
            "scored",
            "excluded",
            "precision",
            "recall",
            "f1",
        )
    }


def evaluate(corpus, output, *, seed=DEVELOPMENT_SEED):
    """Fit each grid cell on training folds only; score its disjoint validation rows."""
    if not isinstance(corpus, LabeledCorpus) or not corpus.rows:
        raise ValueError("a nonempty labeled development corpus is required")
    keys = set()
    for row in corpus.rows:
        key = (row.episode_id, row.slot, row.job_id, row.start_slot)
        if row.episode_id not in corpus.fold_of_episode or key in keys:
            raise ValueError("unknown episode or duplicate candidate in development rows")
        if type(row.label) is not bool or any(not math.isfinite(v) for v in row.features):
            raise ValueError("definite boolean labels and finite features are required")
        keys.add(key)
    splits = blocked_fold_splits(corpus.fold_of_episode)
    output.mkdir(parents=True, exist_ok=False)
    records = []
    aggregates = []
    for spec in grid_specs():
        parts = []
        for split in splits:
            training = rows_for_episodes(corpus.rows, split.train_episode_ids)
            validation = rows_for_episodes(corpus.rows, split.eval_episode_ids)
            if not training or not validation:
                raise ValueError("every fold requires training and validation rows")
            started = time.perf_counter()
            fitted = fit_model(spec, training, seed=seed)
            fit_seconds = time.perf_counter() - started
            started = time.perf_counter()
            score = score_fitted_rows(fitted, validation)
            score_seconds = time.perf_counter() - started
            path = output / f"{spec.system}-depth{spec.max_depth}-fold{split.fold}.joblib"
            digest = save_artifact(
                fitted,
                path,
                manifest={
                    "scope": "new_development_fold_classification_only",
                    "fold": split.fold,
                    "seed": seed,
                },
            )
            parts.append(score)
            records.append(
                {
                    "spec": spec.key,
                    "fold": split.fold,
                    "training_positive": fitted.n_positives,
                    "training_negative": fitted.n_negatives,
                    "fit_seconds": fit_seconds,
                    "score_seconds": score_seconds,
                    "refit_sha256": digest,
                    **cells(score),
                }
            )
        aggregate = sum_candidate_scores(parts)
        if aggregate.scored != len(corpus.rows):
            raise ValueError("validation folds must cover each definite row exactly once")
        aggregates.append({"spec": spec.key, **cells(aggregate)})
    return {
        "scope": "new_development_blocked_fold_classification_not_final_study",
        "seed": seed,
        "threshold": 0.5,
        "definite_rows": len(corpus.rows),
        "episode_count": len(corpus.fold_of_episode),
        "folds": records,
        "pooled_by_spec": aggregates,
        "aggregation": "sum confusion cells over three disjoint validation folds, then derive rates",
        "excluded_before_saved_corpus": None,
        "exclusion_note": "Input contains definite rows only; original excluded-candidate counts are unavailable here.",
        "held_out_access": False,
        "model_requests": 0,
        "selection_changed": False,
        "limitations": "Post-selection descriptive development scores; no model selection by these metrics. Not unbiased final performance or scheduling outcomes. Frozen policy binaries unchanged.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = args.corpus.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != args.expected_sha256:
        raise ValueError("trusted development corpus digest mismatch")
    import io

    corpus = joblib.load(io.BytesIO(raw))
    _, expected_folds = allocation()
    if not isinstance(corpus, LabeledCorpus) or dict(corpus.fold_of_episode) != dict(
        expected_folds
    ):
        raise ValueError("corpus must use the exact published 40-episode development allocation")
    report = evaluate(corpus, args.out)
    report.update(
        corpus_sha256=digest,
        code_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        scorer_sha256=hashlib.sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
    )
    with (args.out / "metrics.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"folds": len(report["folds"]), "definite_rows": report["definite_rows"]}))


if __name__ == "__main__":
    main()
