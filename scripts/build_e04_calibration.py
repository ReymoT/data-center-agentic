"""Build the E04 rule §11.8 calibration packet: two new practice outputs.

Before any held-out output is opened, both raters extract assertions from these
outputs independently and compare extraction only (#22). The outputs are hand-written
on the hand-example fixture, like the development cases, and are neither development
nor held-out cases; they never enter either evaluation set.

This file contains the intended answers' design notes. Raters should extract from
docs/e04/calibration/CALIBRATION_PACKET.md before opening this script.

    python scripts/build_e04_calibration.py          # write docs/e04/calibration/*
    python scripts/build_e04_calibration.py --check  # fail if the committed files are stale
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import review  # noqa: E402
from scripts.build_e04_cases import CI, J1_BEST, J2_BEST, output, state  # noqa: E402
from tests.contracts import fixtures as f  # noqa: E402

OUT = ROOT / "docs" / "e04" / "calibration"
ORDER_SEED = 20261030  # fixes which output is shown as X
HEADER = (
    "# E04 calibration: practice packet (rule §11.8)\n"
    "\n"
    f"Rubric `{review.RUBRIC_VERSION}` with the draft 1 clarifications in section 11. Two "
    "hand-written practice outputs, not model outputs, and neither development nor held-out "
    "cases. Each rater **extracts independently** from both outputs into "
    "`annotation_template.json`, following [EXTRACTION_RULE.md](../EXTRACTION_RULE.md) "
    "section 11, before discussing with the other rater or opening the generator script. "
    "Labels and completeness may be filled in, but only extraction is compared.\n"
)

# Slot 1, J1 and J2 waiting. Forecasts from slot 1: 450/300/250/400/480/520 g/kWh for
# slots 1-6. Design notes, for after calibration:
# - structured output: summary sentences mix a plan intention, a repeat of claim C1
#   (same value), new facts (80 kWh energy, the 30.0 kg alternative, 80 kW peak) and a
#   goal statement; limitation 2 is a checkable deadline fact; numeric facts span
#   several reference kinds (energy, job emissions, intensity, load).
# - malformed output: its raw text states a 110 kW load (40 + 40 + 30, correct) and
#   that it is under the 100 kW limit (false), before the JSON is cut off (§11.7).
CASE = (
    "CAL01",
    state(1, ("J1", "J2")),
    output(
        1,
        starts=[("J1", 2), ("J2", 4)],
        summary="Wait one more slot and start J1 at slot 2, then J2 at slot 4. J1 uses 80 kWh "
        "over slots 2-3 and emits 22.0 kg. Starting J1 now at slot 1 would emit 30.0 kg "
        "instead, because slot 1 is 450 g/kWh. Peak site load stays at 80 kW. The goal is to "
        "keep emissions as low as possible.",
        claims=[
            ("C1", "J1 at slots 2-3 emits 22.0 kg.", J1_BEST, 22.0, "kg"),
            ("C2", "J2 at slots 4-5 emits 26.4 kg.", J2_BEST, 26.4, "kg"),
            ("C3", "The slot 3 forecast is 250 g/kWh.", (CI(3),), 250.0, "g/kWh"),
        ],
        limitations=(
            "Forecasts are perfect-foresight development values.",
            "J2 must finish by slot 6, so starting it after slot 4 would miss its deadline.",
        ),
    ),
    output(
        1,
        status="malformed",
        raw="Start J1 and J2 now at slot 1. Load would be 110 kW, under the 100 kW limit. "
        '{"output_status": "ok", "plan": {"starts": [{"job_id": "J1", "start_slot": 1}, '
        '{"job_id": "J2", "start_',
    ),
)


def build() -> dict[str, str]:
    """Every generated file's text, keyed by its path relative to docs/e04/calibration."""
    case_id, st, structured, malformed = CASE
    pair = [structured, malformed]
    random.Random(ORDER_SEED).shuffle(pair)
    data = {
        "rubric_version": review.RUBRIC_VERSION,
        "synthetic": True,
        "purpose": "rule 11.8 extraction-only calibration; not a development or held-out case",
        "note": "Hand-written practice outputs on the hand-example fixture; not model outputs.",
        "cases": [
            {
                "case_id": case_id,
                "snapshot": f.snapshot().to_jsonable(),
                "state": st.to_jsonable(),
                "outputs": dict(zip(review.OUTPUT_KEYS, pair)),
            }
        ],
    }
    loaded = review.load_cases(data)
    template = {
        "rubric_version": review.RUBRIC_VERSION,
        "rater": "",
        "outputs": [review.blank_annotation(c, k) for c in loaded for k in review.OUTPUT_KEYS],
    }
    packet = review.render_packet(loaded)
    packet = HEADER + packet[packet.index("\n## ") :]
    dump = lambda d: json.dumps(d, indent=2, ensure_ascii=False) + "\n"  # noqa: E731
    return {
        "calibration_cases.json": dump(data),
        "annotation_template.json": dump(template),
        "CALIBRATION_PACKET.md": packet,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if committed files differ")
    args = parser.parse_args()
    stale = []
    for name, text in build().items():
        path = OUT / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    if stale:
        print("stale:", ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
