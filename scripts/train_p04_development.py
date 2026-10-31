"""Train/select/refit development C/D from the published D04 corpus and O02 labels.

Requires an authorized local carbon source path. Does not download data. Writes
joblib artifacts under models/artifacts/ (gitignored) plus JSON manifests.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.training.pipeline import (  # noqa: E402
    build_labeled_corpus,
    freeze_selection,
    run_selection,
)

DEFAULT_SEED = 20261031


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="authorized pinned D01 carbon CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "models" / "artifacts" / "p04-development",
        help="directory for frozen C/D artifacts",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--label-time-limit",
        type=float,
        default=5.0,
        help="O02 solver time limit per labeled decision (seconds)",
    )
    args = parser.parse_args()
    corpus = build_labeled_corpus(args.source, label_time_limit_s=args.label_time_limit)
    selection = run_selection(corpus, seed=args.seed, source=args.source)
    digests = freeze_selection(
        selection,
        args.output,
        extra_manifest={
            "proposal_id": "d04-development-20261028-v1",
            "content_receipt": "d04-development-content-112-v2",
            "n_labeled_rows": len(corpus.rows),
            "n_episodes": len(corpus.episodes),
        },
    )
    print(
        json.dumps(
            {
                "status": "P04_DEVELOPMENT_FROZEN",
                "seed": args.seed,
                "n_labeled_rows": len(corpus.rows),
                "selected": {k: v.key for k, v in selection.selected.items()},
                "artifacts": digests,
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
