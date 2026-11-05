"""Build E06 study tables from saved run units, reading saved files only.

Run with explicit bundles and unit folders. A unit without a final result is reported as
missing rather than scored from partial traces. The output file must not exist, and it may
hold private values, so write it to private storage until its contents are reviewed.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.evaluation import study_tables  # noqa: E402
from dc_sustainability.evaluation.validator import Q03_OPTION_B  # noqa: E402
from dc_sustainability.experiments.config import load_bundle  # noqa: E402

CLASSICAL = ("greedy_a", "greedy_b", "decision_tree_c", "random_forest_d")


def load_unit(folder: Path) -> tuple[s.DecisionRecord, ...] | None:
    """A completed unit's decision records; None when it has no final result."""
    if not (folder / "result.json").is_file():
        return None
    return tuple(
        s.DecisionRecord.from_json(path.read_text(encoding="utf-8"))
        for path in sorted((folder / "traces").glob("*.json"))
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, action="append", required=True)
    parser.add_argument("--unit-dir", type=Path, action="append", required=True)
    parser.add_argument("--model-trials", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    planned = {}
    for path in args.bundle:
        bundle = load_bundle(path)
        planned[bundle.episode.episode_id] = study_tables.planned_episode(
            bundle.episode, bundle.slot0_utc, bundle.forecasts_by_slot
        )
    loaded = [load_unit(folder) for folder in args.unit_dir]
    trials = {system: (None,) for system in CLASSICAL}
    trials |= {system: tuple(args.model_trials) for system in ("plain_llm", "agent")}
    report = study_tables.study_report(
        [run for run in loaded if run is not None], planned, trials, Q03_OPTION_B
    )
    report["units_without_result"] = sum(run is None for run in loaded)
    with args.out.open("x", encoding="utf-8") as handle:  # never overwrite a report
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"{report['split']}: {report['scored_runs']} scored, wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
