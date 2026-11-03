"""Validate receiving pins and measured models offline, writing a new readiness record."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dc_sustainability.experiments.readiness import prepare  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--forest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = prepare(
        json.loads(args.candidate.read_text()),
        {"decision_tree_c": args.tree, "random_forest_d": args.forest},
        ROOT,
    )
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(result["status"])


if __name__ == "__main__":
    main()
