"""Draw the Q10 review sample (main and boundary) from the frozen episode bundles.

Reads job timing only, through ``sampling.select`` and ``sampling.select_boundary`` with
their recorded seeds. Both records may name held-out episodes and slots, so write them to
private evaluator storage. Output files must not exist. Prints only counts and hashes.

    python scripts/build_review_sample.py --bundle B1.json --bundle B2.json ...
        --main-out PRIVATE/review-sample-main.json --boundary-out PRIVATE/review-sample-boundary.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dc_sustainability.evaluation import sampling  # noqa: E402
from dc_sustainability.experiments.config import load_bundle  # noqa: E402


def write_new(path: Path, data: dict) -> str:
    payload = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
    return hashlib.sha256(payload).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, action="append", required=True)
    parser.add_argument("--main-out", type=Path, required=True)
    parser.add_argument("--boundary-out", type=Path, required=True)
    args = parser.parse_args(argv)
    for path in (args.main_out, args.boundary_out):
        if path.exists():
            parser.error("sample output already exists; the sample is drawn once")
    episodes = [load_bundle(path).episode for path in args.bundle]
    main_record = sampling.select(episodes)
    boundary = sampling.select_boundary(episodes)
    main_hash = write_new(args.main_out, main_record.to_jsonable())
    boundary_hash = write_new(args.boundary_out, boundary.to_jsonable())
    print(
        f"split {main_record.split}: {len(episodes)} episodes; main {main_record.achieved} of "
        f"{main_record.target} (shortfall {sum(main_record.shortfall.values())}); "
        f"boundary {len(boundary.selections)} (cap {boundary.cap})"
    )
    print("manifest_hash      ", main_record.manifest_hash)
    print("main_sha256        ", main_hash)
    print("boundary_sha256    ", boundary_hash)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Review sample stopped: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
