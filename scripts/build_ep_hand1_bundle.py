"""Build the frozen public EP-HAND1 episode bundle for the paired Plain/Agent exercise.

The A02 preparation (#126) asks for one EP-HAND1 input shared by both systems, with
its path and SHA-256. This writes the E02 runner's ``EpisodeBundle`` from the public
hand-example fixture: the private episode from ``tests.contracts.fixtures`` (J1, J2
and the intentionally impossible J3) and, for each slot, the perfect-foresight
forecasts issued at that slot for slots it has not passed. It is synthetic,
development-only and public; it is not a D04 study episode and holds no held-out data.

    python scripts/build_ep_hand1_bundle.py          # write the bundle
    python scripts/build_ep_hand1_bundle.py --check  # fail if the committed file is stale
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.experiments.config import EpisodeBundle, bundle_to_json  # noqa: E402
from tests.contracts import fixtures as f  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "ep-hand1-episode-bundle.json"


def build() -> str:
    forecasts = {
        slot: tuple(x for x in f.forecasts(issued_slot=slot) if x.valid_slot >= slot)
        for slot in range(30)
    }
    return bundle_to_json(EpisodeBundle(f.private_episode(), f.SLOT0_UTC, forecasts))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the committed file differs")
    args = parser.parse_args()
    text = build()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"stale: {OUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
