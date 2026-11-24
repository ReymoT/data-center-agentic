"""Build the RULE-07 two-scenario demo page from retained evidence (#246).

Reads published evidence only; runs no policy, checker, simulator or model. The output
file is created exclusively. Defaults point at the retained files on main.

    python scripts/build_rule_demo_page.py --out ui/rule_demo.html [--metrics PATH | --no-metrics]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rule_demo_page_core as core  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, default=core.DEFAULT_METRICS)
    parser.add_argument(
        "--no-metrics", action="store_true", help="show the metrics panel as pending"
    )
    for key in core.DEFAULTS:
        parser.add_argument(f"--{key.replace('_', '-')}", type=Path, dest=key)
    args = parser.parse_args(argv)
    paths = {k: getattr(args, k) for k in core.DEFAULTS if getattr(args, k) is not None}
    try:
        page = core.render(
            core.load_inputs(paths, metrics=None if args.no_metrics else args.metrics)
        )
    except (OSError, ValueError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    with open(args.out, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(page)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
