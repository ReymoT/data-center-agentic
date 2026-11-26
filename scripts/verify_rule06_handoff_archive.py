"""Verify the exact November26 handoff archives without extracting or executing them.

Integrity only: not independent accounting, policy replay or scientific reproduction.
"""

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

OUTER_SHA = "71b8c0a6e7e3781be49a6d81c5e1c75674ae54404eeaa9fb1a7394852fc041e1"
INNER_SHA = "9b14b587dbc5c7e1bc13e1074963e0b9c81aac2349034c72c22aa3b728c63aad"
PARENT_SHA = "ff9a4e2da2d7b7f81e2e93bdcd2cf3ea819c37e705504c2af4ef261ab24bf431"
INNER = "evidence/RULE04_NISHA_NEW_RECEIVING_2026-11-26.zip"
PARENT = "parent/accepted_parent_receiving.zip"
MAX_BYTES = 512 * 1024 * 1024
MAX_FILE = 96 * 1024 * 1024


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate manifest key")
            out[key] = value
        return out

    return json.loads(raw, object_pairs_hook=pairs)


def checked_zip(raw, expected_sha, *, markers=None):
    if len(raw) > MAX_FILE or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("archive differs from the exact retained package")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(infos) > 60000 or len(set(names)) != len(names):
            raise ValueError("duplicate or excessive ZIP members")
        if sum(i.file_size for i in infos) > MAX_BYTES:
            raise ValueError("excessive expanded size")
        for info in infos:
            p = PurePosixPath(info.filename)
            if (
                p.is_absolute()
                or ".." in p.parts
                or "\\" in info.filename
                or ":" in info.filename
                or str(p) != info.filename
                or info.is_dir()
                or info.file_size > MAX_FILE
                or info.flag_bits & 1
                or (info.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("unsafe, encrypted or oversized ZIP member")
        manifest = strict_json(archive.read("SHA256_MANIFEST.json"))
        if not isinstance(manifest, dict) or set(names) != set(manifest) | {"SHA256_MANIFEST.json"}:
            raise ValueError("exact manifest inventory required")
        for name, expected in manifest.items():
            if (
                not isinstance(expected, str)
                or hashlib.sha256(archive.read(name)).hexdigest() != expected
            ):
                raise ValueError("member hash differs")
        if markers is not None:
            for marker, count in markers.items():
                actual = sum(marker in PurePosixPath(n).parts for n in names)
                if actual != count:
                    raise ValueError(f"missing or excess {marker} records")
        return len(manifest), {n: archive.read(n) for n in (INNER, PARENT) if n in names}


def verify(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_FILE + 1)
    outer_count, nested = checked_zip(raw, OUTER_SHA)
    inner_count, parent = checked_zip(
        nested[INNER], INNER_SHA, markers={".completed": 5340, ".intents": 5340}
    )
    parent_count, _ = checked_zip(parent[PARENT], PARENT_SHA)
    return {
        "status": "PASS_ARCHIVE_INTEGRITY_ONLY",
        "outer_manifest_entries": outer_count,
        "new_receiving_manifest_entries": inner_count,
        "accepted_parent_manifest_entries": parent_count,
        "completed_markers": 5340,
        "intent_markers": 5340,
        "scientific_execution_performed": False,
        "independent_reproduction": "NOT_ESTABLISHED",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify(args.package), indent=2))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
