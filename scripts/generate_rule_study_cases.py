"""Generate a RULE-04 synthetic case set and its evaluator-only accounting file (#242).

This is development preparation. Final generation is disabled pending the actual
frozen-code dispatcher and authenticated bounded authorization; a URL cannot enable it.
Output files are reserved exclusively before generation and never overwritten.

    python scripts/generate_rule_study_cases.py --domain development \
        --out-cases development.json --out-accounting development.accounting.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import ExitStack
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dc_sustainability.evaluation import rule_study_generator as g  # noqa: E402


def write_pair(paths, produce):
    """Reserve both destinations before work; roll back only files created by us.

    The pair is not filesystem-atomic. Consumers must wait for successful return.
    On error preexisting/replaced paths remain untouched; partial owned files are removed.
    """
    paths = tuple(Path(p).absolute() for p in paths)
    if paths[0].resolve() == paths[1].resolve():
        raise ValueError("case and accounting outputs must be different files")
    for path in paths:
        if not path.parent.is_dir():
            raise FileNotFoundError("both output parents must already exist")
    owned = []
    try:
        with ExitStack() as stack:
            handles = []
            for path in paths:
                handle = stack.enter_context(path.open("x", encoding="utf-8", newline="\n"))
                owned.append((path, os.fstat(handle.fileno())))
                handles.append(handle)
            pair = produce()
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError("generator must produce exactly two artifacts")
            texts = [g.dumps(value) for value in pair]
            for handle, text in zip(handles, texts):
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
        return pair
    except BaseException:
        for path, identity in owned:
            try:
                current = path.lstat()
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    path.unlink()
            except FileNotFoundError:
                pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--domain", choices=sorted(g.SEED_DOMAINS), required=True)
    parser.add_argument("--out-cases", type=Path, required=True)
    parser.add_argument("--out-accounting", type=Path, required=True)
    parser.add_argument("--authorization", help="reserved; a URL cannot enable final generation")
    args = parser.parse_args(argv)

    if args.out_cases.resolve() == args.out_accounting.resolve():
        parser.error("case and accounting outputs must be different files")
    for path in (args.out_cases, args.out_accounting):
        if path.exists():
            parser.error(f"{path} already exists; outputs are never overwritten")
    try:
        case_set, accounting = write_pair(
            (args.out_cases, args.out_accounting),
            lambda: g.generate(args.domain, authorization=args.authorization),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"set_id": case_set["set_id"], "report": case_set["metadata"]["report"]}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
