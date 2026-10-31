"""D04 #112: exact development-only materialization into authorized private custody.

No allocation, scientific freeze or held-out policy export is performed. The
historical #102 files remain immutable. A separate receipt binds actual content.
The development-only persistence forecast adapter is causal: every forecast is
derived only from the immediately preceding source row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.data import carbon_source as carbon
from dc_sustainability.data import scenarios
from dc_sustainability.data.development_folds import PROPOSAL_ID, canonical_lf_sha256
from dc_sustainability.data.splits import digest

VERSION = "d04-content-v1"
ROOT = Path(__file__).resolve().parents[2]
ALLOCATION = ROOT / "data/manifests" / PROPOSAL_ID
PINS = {
    "manifest.json": "2af72d8ed49801d64bd707cb1a9adc9e8b216ea7cd653dbb65c8ca3cf965cbb5",
    "fold-map.json": "c54ef1c35dd39628bcc6c4f18fb3cc241a70f8cf94b1b9445d9ea02234531fac",
}
SEMANTICS = s.CarbonSemantics(
    pollutant_basis="unresolved",
    interval_convention="unresolved",
    emissions_factor_type="average",
    slot_mapping_status="provisional",
)
LIMITATIONS = (
    "Q05 pollutant/system boundary, physical intervals, exporter lineage, rights, "
    "historical regeneration and site suitability remain unresolved.",
    "Q06 scientific freeze, calibration and private held-out union isolation are not certified.",
    "The development persistence adapter is provisional and not a Q05/Q06 scientific freeze.",
)
CODE_PATHS = (
    "dc_sustainability/data/materialize_development.py",
    "dc_sustainability/data/development_folds.py",
    "dc_sustainability/data/splits.py",
    "dc_sustainability/data/scenarios.py",
    "dc_sustainability/data/carbon_source.py",
    "dc_sustainability/schemas.py",
    "dc_sustainability/simulator/core.py",
    "dc_sustainability/training/collect.py",
    "dc_sustainability/training/features.py",
    "dc_sustainability/reference/labels.py",
    "dc_sustainability/reference/solver.py",
    "docs/team/MASTER_REIMO.md",
    "docs/decisions/Q01_Q04_AGREEMENT_STATUS.md",
)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def serialize(value: dict) -> bytes:
    """Canonical sorted UTF-8 JSON with explicit LF, independent of native EOL."""
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def allocation(directory: Path = ALLOCATION) -> tuple[dict, dict]:
    """Trust only the pinned merged artifact, never newly sampled allocations."""
    if json.loads((directory / "checksums.json").read_bytes()) != PINS:
        raise ValueError("allocation checksum receipt changed")
    for name, expected in PINS.items():
        if canonical_lf_sha256(directory / name) != expected:
            raise ValueError(f"pinned allocation changed: {name}")
    manifest = json.loads((directory / "manifest.json").read_bytes())
    folds = json.loads((directory / "fold-map.json").read_bytes())
    original = dict(manifest)
    if original.pop("manifest_sha256") != digest(original):
        raise ValueError("allocation canonical checksum mismatch")
    records = manifest["records"]
    if len(records) != 40 or len(folds) != 40 or manifest["proposal_id"] != PROPOSAL_ID:
        raise ValueError("expected exact 40-development allocation")
    if {r["episode_id"]: r["fold"] for r in records} != folds:
        raise ValueError("unexpected IDs/fold assignments")
    if [list(folds.values()).count(i) for i in range(3)] != [16, 12, 12]:
        raise ValueError("changed fold counts")
    for record in records:
        original = dict(record)
        if original.pop("allocation_sha256") != digest(original):
            raise ValueError("allocation record hash mismatch")
        if record["partition"] != "development" or record["withheld"]:
            raise ValueError("only the approved base development records are supported")
    return manifest, folds


def snapshot() -> s.ConstraintSnapshot:
    """Documented 100/40 kW, PUE 1.2, hourly site; agreed Q04 two-slot age.

    Job timing/nonflexibility are authoritative in each generated Job. No hand
    fixture's job-specific constraints are copied into this site snapshot.
    """
    return s.ConstraintSnapshot(
        snapshot_id="SNAP-D04-112",
        site=s.SiteConfig(site_id="SITE1", background_kw=40, pue=1.2, slot_hours=1),
        constraints=(
            s.Constraint(
                constraint_id="CON-CAP-100",
                constraint_type="capacity",
                limit_value=100,
                unit="kW",
                applies_to_site="SITE1",
                source_id="SRC-SITE",
            ),
            s.Constraint(
                constraint_id="CON-FRESH-2",
                constraint_type="freshness",
                limit_value=2,
                unit="slot",
                applies_to_site="SITE1",
                source_id="SRC-Q04",
            ),
        ),
        sources=(
            s.SourceRef(
                source_id="SRC-SITE",
                path="docs/team/MASTER_REIMO.md",
                sha256=canonical_lf_sha256(ROOT / "docs/team/MASTER_REIMO.md"),
                redistribution_status="permitted",
            ),
            s.SourceRef(
                source_id="SRC-Q04",
                path="docs/decisions/Q01_Q04_AGREEMENT_STATUS.md",
                sha256=canonical_lf_sha256(ROOT / "docs/decisions/Q01_Q04_AGREEMENT_STATUS.md"),
                redistribution_status="permitted",
            ),
            s.SourceRef(
                source_id="SRC-D01",
                path=carbon.SOURCE_URL,
                commit=carbon.COMMIT,
                sha256=carbon.SHA256,
                redistribution_status="unresolved",
            ),
        ),
    )


def episodes(source: Path, *, directory: Path = ALLOCATION) -> tuple[s.PrivateEpisode, ...]:
    """Validate all required inputs before returning any actual corpus content."""
    manifest, _ = allocation(directory)
    observations, _ = carbon.load_source(source)
    site = snapshot()
    result = []
    for record in manifest["records"]:
        indices = record["window"]["proposed_physical_indices"]
        if len(indices) != 30 or len(set(indices)) != 30:
            raise ValueError("allocation needs 30 unique recorded source indices")
        actuals = tuple(
            s.CarbonObservation(
                fact_id=f"FACT-D01-{index}",
                value=observations[index][1],
                unit="g/kWh",
                source_id="SRC-D01",
                source_sha256=carbon.SHA256,
                observed_at_utc=observations[index][0],
                valid_slot=slot,
                semantics=SEMANTICS,
                quality_status="unvalidated",
            )
            for slot, index in enumerate(indices)
        )
        episode = scenarios.generate_episode(
            record["scenario"],
            seed=record["seed"],
            split="development",
            episode_id=record["episode_id"],
            snapshot=site,
            realized_carbon=actuals,
        ).model_copy(update={"forecast_visibility": "persistence"})
        # Exercise the actual F02 JSON boundary independently for every episode.
        if s.PrivateEpisode.from_jsonable(episode.to_jsonable()) != episode:
            raise ValueError("F02 round trip mismatch")
        result.append(episode)
    return tuple(result)


def persistence_forecasts(
    source: Path, episode_id: str, *, directory: Path = ALLOCATION
) -> dict[int, tuple[s.CarbonForecast, ...]]:
    """Build a causal development-only persistence forecast schedule.

    At decision slot ``t``, the value is the source row immediately preceding
    the row associated with slot ``t``. The issue time is the timestamp label of
    the current row, so the input row is strictly earlier. The prior value is
    projected across the current visible horizon. Realized values for slot ``t``
    or later are never read to construct that decision's policy view.

    This is a provisional development adapter, not evidence about the source's
    interval semantics and not authorization for held-out or final study use.
    """
    manifest, _ = allocation(directory)
    record = next((r for r in manifest["records"] if r["episode_id"] == episode_id), None)
    if record is None:
        raise ValueError("episode is not in the approved development allocation")
    rows, _ = carbon.load_source(source)
    indices = record["window"]["proposed_physical_indices"]
    if len(indices) != 30 or any(index <= 0 for index in indices):
        raise ValueError("persistence forecasts require a preceding source row")
    result: dict[int, tuple[s.CarbonForecast, ...]] = {}
    for issue_slot, current_index in enumerate(indices):
        issued_at = rows[current_index][0]
        prior_time, prior_value = rows[current_index - 1]
        if not prior_time < issued_at:
            raise ValueError("persistence source row must precede forecast issue time")
        result[issue_slot] = tuple(
            s.CarbonForecast(
                fact_id=f"FACT-D01-PERSIST-{issue_slot}-{valid_slot}",
                value=prior_value,
                unit="g/kWh",
                source_id="SRC-D01",
                source_sha256=carbon.SHA256,
                valid_slot=valid_slot,
                issued_at_utc=issued_at,
                forecast_kind="persistence",
                semantics=SEMANTICS,
                quality_status="unvalidated",
            )
            for valid_slot in range(issue_slot, min(issue_slot + s.PROPOSED_DECISION_SLOTS, 30))
        )
    return result


def environment() -> dict:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "dependencies": dict(sorted((d.metadata["Name"], d.version) for d in distributions())),
    }


def receipt(corpus: tuple[s.PrivateEpisode, ...], *, revision: str) -> dict:
    manifest, _ = allocation()
    if len(corpus) != 40 or {e.episode_id for e in corpus} != set(manifest["fold_of_episode"]):
        raise ValueError("receipt requires the complete approved development corpus")
    records = {r["episode_id"]: r for r in manifest["records"]}
    entries = []
    for episode in sorted(corpus, key=lambda e: e.episode_id):
        record = records[episode.episode_id]
        if (episode.scenario_id, episode.seed, episode.split) != (
            record["scenario"],
            record["seed"],
            "development",
        ) or episode.jobs != scenarios.generate_jobs(
            record["scenario"], seed=record["seed"], split="development"
        ):
            raise ValueError("episode metadata/jobs do not match original allocation")
        entries.append(
            {
                "episode_id": episode.episode_id,
                "scenario": episode.scenario_id,
                "seed": episode.seed,
                "fold": record["fold"],
                "allocation": record,
                "allocation_sha256": record["allocation_sha256"],
                "source_date": record["window"]["date"],
                "source_indices": record["window"]["proposed_physical_indices"],
                "source_id": "SRC-D01",
                "source_timestamps": [
                    o.to_jsonable()["observed_at_utc"] for o in episode.realized_carbon
                ],
                "constraint_snapshot_sha256": episode.snapshot.canonical_hash(),
                "episode_canonical_sha256": episode.canonical_hash(),
                "file_sha256": sha(serialize(episode.to_jsonable())),
                "content_path": f"{episode.episode_id}.json",
                "status": "materialized_development_only",
            }
        )
    return {
        "version": VERSION,
        "parent_proposal_id": PROPOSAL_ID,
        "allocation_file_sha256": PINS,
        "allocation_canonical_sha256": manifest["manifest_sha256"],
        "schema_version": s.SCHEMA_VERSION,
        "generator_version": scenarios.GENERATOR_VERSION,
        "distribution_specification": scenarios.generate_jobs.__doc__,
        "code_revision": revision,
        "code_revision_note": "revision plus canonical LF working-code hashes",
        "code_sha256": {p: canonical_lf_sha256(ROOT / p) for p in CODE_PATHS},
        "environment": environment(),
        "source": manifest["source"],
        "carbon_semantics": SEMANTICS.to_jsonable(),
        "scientific_acceptance": False,
        "transformations": [
            "D01 pinned UTF-8 CSV/UTC/float parsing",
            "recorded indices to slots 0..29",
        ],
        "limitations": LIMITATIONS,
        "policy_visible": False,
        "entries": entries,
    }


def materialize(source: Path, destination: Path, *, revision: str) -> dict:
    """New private directory only; receipt is written last as a completion marker.

    Failed/interrupted directories are never resumed or overwritten. Verification
    rejects them. Reproduce into a new directory instead of deleting evidence.
    """
    if sys.version_info[:2] != (3, 12) or platform.python_implementation() != "CPython":
        raise ValueError("approved generator requires CPython 3.12")
    if destination.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("source-derived corpus must remain outside the repository")
    corpus = episodes(source)
    evidence = receipt(corpus, revision=revision)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    for episode in corpus:
        _write(destination / f"{episode.episode_id}.json", serialize(episode.to_jsonable()))
    _write(destination / "content-receipt.json", serialize(evidence))
    return evidence


def _write(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def public_receipt(evidence: dict, *, custody_id: str) -> dict:
    """Checksum-only pointer: no realized values or derived hourly timestamp series."""
    keys = (
        "episode_id",
        "scenario",
        "seed",
        "fold",
        "allocation_sha256",
        "constraint_snapshot_sha256",
        "episode_canonical_sha256",
        "file_sha256",
        "content_path",
        "status",
    )
    return {key: value for key, value in evidence.items() if key != "entries"} | {
        "private_receipt_sha256": sha(serialize(evidence)),
        "custody_id": custody_id,
        "entries": [{key: entry[key] for key in keys} for entry in evidence["entries"]],
    }


def verify(source: Path, destination: Path, *, revision: str) -> tuple[s.PrivateEpisode, ...]:
    """Reject changed content while reporting, not failing on, environment drift."""
    corpus = episodes(source)
    expected = receipt(corpus, revision=revision)
    names = {f"{e.episode_id}.json" for e in corpus} | {"content-receipt.json"}
    if {p.name for p in destination.iterdir()} != names:
        raise ValueError("partial corpus or unexpected files/IDs")
    loaded = []
    for episode in corpus:
        path = destination / f"{episode.episode_id}.json"
        if path.is_symlink() or path.read_bytes() != serialize(episode.to_jsonable()):
            raise ValueError(f"episode content mismatch: {episode.episode_id}")
        loaded.append(s.PrivateEpisode.from_jsonable(json.loads(path.read_bytes())))
    path = destination / "content-receipt.json"
    if path.is_symlink():
        raise ValueError("content receipt must not be a symlink")
    recorded = json.loads(path.read_bytes())
    recorded_environment = recorded.pop("environment", None)
    expected_without_environment = json.loads(serialize(expected))
    expected_without_environment.pop("environment", None)
    if recorded != expected_without_environment:
        raise ValueError("content receipt mismatch (excluding environment)")
    if not isinstance(recorded_environment, dict):
        raise ValueError("content receipt environment record is missing")
    return tuple(loaded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--code-revision", help="recorded base revision for exact receipt replay")
    parser.add_argument(
        "--public-receipt",
        type=Path,
        help="exclusive checksum-only receipt output; valid only while materializing",
    )
    parser.add_argument("--custody-id", help="non-secret custody label for --public-receipt")
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if args.code_revision:
        recorded = subprocess.check_output(
            ["git", "rev-parse", "--verify", args.code_revision + "^{commit}"], cwd=ROOT, text=True
        ).strip()
        if recorded != args.code_revision:
            raise ValueError("code revision must be a full existing commit SHA")
        revision = recorded
    operation = verify if args.verify else materialize
    evidence = operation(args.source, args.destination, revision=revision)
    if args.public_receipt:
        if args.verify or not args.custody_id:
            raise ValueError("--public-receipt requires materialization and --custody-id")
        _write(
            args.public_receipt,
            serialize(public_receipt(evidence, custody_id=args.custody_id)),
        )
    print(f"PASS: 40 development episodes {'verified' if args.verify else 'materialized'}")


if __name__ == "__main__":
    main()
