"""E02 command line.

    python -m dc_sustainability.experiments run --config RUN.json --out DIR
    python -m dc_sustainability.experiments status --config RUN.json --out DIR

RUN.json: {"name": ..., "systems": [...], "episodes": ["bundle.json", ...],
"model_trials": [0, 1, 2]}; bundle paths are relative to RUN.json. The code revision
and dependency-lock hash are recorded automatically in the run identity.
"""

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path

from dc_sustainability.experiments import runner
from dc_sustainability.experiments.config import config_from_file, lf_sha256

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "requirements" / "requirements-windows-py312.lock.txt"


def code_revision() -> str:
    """The checked-out commit, marked dirty when tracked files differ from it."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unrecorded"
    return f"{head}-dirty" if dirty else head


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m dc_sustainability.experiments")
    parser.add_argument("command", choices=("run", "status"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    config = config_from_file(
        args.config,
        code_revision=code_revision(),
        lock_sha256=lf_sha256(LOCK) if LOCK.exists() else None,
    )
    statuses = (runner.run if args.command == "run" else runner.status)(config, args.out)
    print(f"run {config.run_id} ({config.name}), config {config.config_hash[:12]}")
    for (system, state), n in sorted(Counter((u.unit.system, u.status) for u in statuses).items()):
        print(f"  {system:16} {state:22} {n}")
    for u in statuses:
        if u.detail:
            print(f"  {u.unit.system} {u.unit.episode_id} trial {u.unit.trial}: {u.detail}")
    return 0 if all(u.status == "completed" for u in statuses) else 1


if __name__ == "__main__":
    sys.exit(main())
