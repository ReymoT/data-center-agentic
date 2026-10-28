"""Issue #102 concrete development proposal; isolated from policy/runtime loading."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from dc_sustainability.data import carbon_source, scenarios, splits
from dc_sustainability.training.folds import blocked_fold_splits, refuse_held_out_episodes

PROPOSAL_ID = "d04-development-20261028-v1"
BASE_REVISION = "06060b6dd1d69e5af6556102aa5a7d8e5dd48e23"
# New proposed DEVELOPMENT-ONLY roots: date of this request, domain-separated by 01/02.
DATE_SEED = 2026102801
JOB_SEED = 2026102802
CANDIDATES = tuple(date(2022, month, day) for month in range(1, 13) for day in range(1, 15))


def canonical_lf_sha256(path: Path) -> str:
    """Hash text bytes with CRLF replaced by LF; preserve every other byte.

    No JSON reserialization, whitespace stripping, encoding conversion or final
    newline insertion: source edits and artifact formatting changes remain visible.
    Lone CR bytes are preserved too. Applies only to this proposal's text files.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def proposed_records():
    return splits.propose_development_allocation(
        development_candidates=CANDIDATES, date_seed=DATE_SEED, job_seed=JOB_SEED
    )


def build_manifest() -> dict:
    records = proposed_records()
    root = Path(__file__).resolve().parents[2]
    files = (
        "dc_sustainability/data/splits.py",
        "dc_sustainability/data/development_folds.py",
        "dc_sustainability/data/scenarios.py",
        "dc_sustainability/data/carbon_source.py",
        "dc_sustainability/schemas.py",
    )
    manifest = {
        "proposal_id": PROPOSAL_ID,
        "status": "proposed_development_only_awaiting_affected_owner_agreement",
        "scientific_acceptance": False,
        "policy_visible": False,
        "code_revision": BASE_REVISION,
        "code_revision_note": "base revision plus working-file SHA256 of canonical LF bytes (CRLF to LF only)",
        "code_file_sha256": {p: canonical_lf_sha256(root / p) for p in files},
        "allocator_version": splits.VERSION,
        "generator_version": scenarios.GENERATOR_VERSION,
        "source": {
            "commit": carbon_source.COMMIT,
            "path": carbon_source.SOURCE_PATH,
            "sha256": carbon_source.SHA256,
            "url": carbon_source.SOURCE_URL,
        },
        "development_candidates": [d.isoformat() for d in CANDIDATES],
        "development_date_seed": DATE_SEED,
        "development_job_seed": JOB_SEED,
        "seed_scope": "development only; no evaluator seed/pool/selection used",
        "selection_algorithm": "existing D04 SHA256 rank; greedy nonoverlap; no seed retry",
        "fold_algorithm": "existing D04 chronological connected components; balanced group counts",
        "distribution_status": "proposed D03 synthetic discrete uniforms; not calibrated or accepted",
        "distribution_specification": scenarios.generate_jobs.__doc__,
        "job_runtime_requirement": "CPython 3.12; random.Random MT19937; record runtime at materialization",
        "records": [r.metadata() for r in records],
        "fold_of_episode": {r.episode_id: r.fold for r in records},
        "overlaps": splits.overlap_report(records),
        "held_out_allocation_generated": False,
        "episode_contents_generated": False,
        "held_out_exclusion_scope": "development allowlist only; global custody check remains pending",
    }
    manifest["manifest_sha256"] = splits.digest(manifest)
    return manifest


def load_fold_map(manifest: dict, projection: dict, *, held_out_episode_ids=()) -> dict[str, int]:
    """Validate this exact proposal, failing closed on changed/missing/extra entries.

    This is a technical review loader, not scientific approval or a policy adapter.
    Custodian may supply restricted held-out IDs locally; they are never returned.
    """
    if manifest != json.loads(json.dumps(build_manifest())):
        raise ValueError("manifest differs from reproducible development proposal")
    expected = manifest["fold_of_episode"]
    if projection != expected or any(type(v) is not int for v in projection.values()):
        raise ValueError("fold projection differs from exact development allowlist")
    if len(projection) != 40:
        raise ValueError("exactly 40 development assignments required")
    refuse_held_out_episodes(projection, held_out_episode_ids)
    blocked_fold_splits(projection)
    return dict(projection)


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for proposal artifacts")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = build_manifest()
    for name, value in (
        ("manifest.json", manifest),
        ("fold-map.json", manifest["fold_of_episode"]),
    ):
        with (args.output / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
