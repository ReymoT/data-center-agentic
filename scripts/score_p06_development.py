"""Score caller-supplied rows with a published-digest artifact.

Required: --artifact PATH, --rows PATH, --system {decision_tree_c,random_forest_d}.
Optional: --excluded NONNEGATIVE, default 0.
No default path. Load with load_published_development. Print one JSON
object to stdout: cells, derived rates (null when None), basis, system,
artifact_sha256, and CALLER_ROWS_NOTE. Write no file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.policies.learned import load_published_development  # noqa: E402
from dc_sustainability.training.dataset import LabeledRow  # noqa: E402
from dc_sustainability.training.metrics import CALLER_ROWS_NOTE, score_fitted_rows  # noqa: E402
from dc_sustainability.training.train import SystemKind  # noqa: E402

_SYSTEMS: tuple[SystemKind, ...] = ("decision_tree_c", "random_forest_d")


def main() -> None:
    """Score caller-supplied rows with a published-digest artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--system", required=True, choices=_SYSTEMS)
    parser.add_argument("--excluded", type=int, default=0)
    args = parser.parse_args()
    rows = _labeled_rows(json.loads(args.rows.read_text(encoding="utf-8")))
    artifact = load_published_development(args.artifact, system=args.system)
    score = score_fitted_rows(artifact.fitted, rows, excluded=args.excluded)
    payload = {
        "artifact_sha256": artifact.artifact_sha256,
        "basis": score.basis,
        "excluded": score.excluded,
        "f1": score.f1,
        "false_negative": score.false_negative,
        "false_positive": score.false_positive,
        "note": CALLER_ROWS_NOTE,
        "precision": score.precision,
        "predicted_negative": score.predicted_negative,
        "predicted_positive": score.predicted_positive,
        "recall": score.recall,
        "scored": score.scored,
        "support_negative": score.support_negative,
        "support_positive": score.support_positive,
        "system": artifact.system,
        "true_negative": score.true_negative,
        "true_positive": score.true_positive,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def _labeled_rows(payload: object) -> tuple[LabeledRow, ...]:
    """Parse Edison-local row JSON into LabeledRow. Metrics never sees a dict."""
    if not isinstance(payload, list):
        raise ValueError("rows JSON must be a list")
    rows: list[LabeledRow] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"row {index} must be an object")
        try:
            episode_id = item["episode_id"]
            job_id = item["job_id"]
            slot = item["slot"]
            start_slot = item["start_slot"]
            features = item["features"]
            label = item["label"]
        except KeyError as exc:
            raise ValueError(f"row {index} is missing {exc.args[0]}") from exc
        if type(episode_id) is not str or type(job_id) is not str:
            raise ValueError(f"row {index} episode_id and job_id must be strings")
        if type(slot) is not int or type(start_slot) is not int:
            raise ValueError(f"row {index} slot and start_slot must be ints")
        if type(label) is not bool:
            raise ValueError(f"row {index} label must be bool")
        if not isinstance(features, list) or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) for value in features
        ):
            raise ValueError(f"row {index} features must be numbers")
        rows.append(
            LabeledRow(
                episode_id=episode_id,
                slot=slot,
                job_id=job_id,
                start_slot=start_slot,
                features=tuple(float(value) for value in features),
                label=label,
            )
        )
    return tuple(rows)


if __name__ == "__main__":
    main()
