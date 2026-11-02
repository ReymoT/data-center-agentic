"""Evaluator-only metadata preparation. No PrivateEpisodes, carbon or jobs are loaded.

Selection requires an externally approved receipt; receipt hashes establish integrity,
not identity or approval. The receiving human must authenticate its decision locators.
No CLI or public metadata projection is provided. Q05 remains conditional.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from dc_sustainability.data import carbon_source as carbon
from dc_sustainability.data import materialize_development as development
from dc_sustainability.data import splits

VERSION = "d04-held-custody-v1"
ALGORITHM = "sha256-rank-greedy-fixed-development-v1"
DEVELOPMENT_CONTENT_RECEIPT = "data/manifests/d04-development-content-112-v2/receipt.json"
DEVELOPMENT_CONTENT_SHA256 = "33c8dce514cdbcba53f9ed03399219be8a511d628ab61def694eedaac894b319"


def interval_comparison(day: date) -> tuple[dict, ...]:
    """Conditional labels for every physical Phoenix slot; never changes D01 mapping.

    Out-of-range rows are None, including year tails. No source values are read.
    """
    if type(day) is not date or day.year != 2022:
        raise ValueError("2022 date required")
    start = datetime(day.year, day.month, day.day, 7, tzinfo=timezone.utc)
    result = []
    for slot in range(30):
        physical = start + slot * carbon.HOUR
        index = int((physical - carbon.START) / carbon.HOUR)
        result.append(
            {
                "slot": slot,
                "physical_start_utc": physical.isoformat(),
                "physical_end_utc": (physical + carbon.HOUR).isoformat(),
                "start_label_utc": physical.isoformat(),
                "end_label_utc": (physical + carbon.HOUR).isoformat(),
                "start_row": index if 0 <= index < 8760 else None,
                "end_row": index + 1 if 0 <= index + 1 < 8760 else None,
            }
        )
    return tuple(result)


def _hash_string(value: str, length: int = 64) -> None:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("invalid commitment")


def _private_path(path: Path) -> Path:
    # Refuse aliases before resolution, including symlinked parent components.
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("custody path rejected")
    resolved = path.resolve()
    if any(
        ((p / ".git").exists() or (p / ".git").is_symlink())
        or ((p / "HEAD").exists() and (p / "objects").is_dir() and (p / "refs").is_dir())
        for p in (resolved, *resolved.parents)
    ):
        raise ValueError("custody path rejected")
    return resolved


def _development() -> tuple[splits.Allocation, ...]:
    manifest, _ = development.allocation()  # immutable artifact/checksum allowlist
    return tuple(
        splits.Allocation(
            episode_id=r["episode_id"],
            partition="development",
            scenario=r["scenario"],
            seed=r["seed"],
            window=splits.Window(date.fromisoformat(r["window"]["date"])),
            related_group=r["related_group"],
            fold=r["fold"],
        )
        for r in manifest["records"]
    )


def _parameters(parameters: dict) -> tuple[tuple[date, ...], int, int]:
    if set(parameters) != {"candidate_dates", "selection_seed", "job_seed_root", "algorithm"}:
        raise ValueError("explicit complete selection parameters required")
    if parameters["algorithm"] != ALGORITHM:
        raise ValueError("unrecognized algorithm")
    for key in ("selection_seed", "job_seed_root"):
        seed = parameters[key]
        if type(seed) is not int or not 0 <= seed < 2**128:
            raise ValueError("invalid seed")
        if seed in (42, 19, 2026102801, 2026102802):
            raise ValueError("demonstration/development root prohibited")
    if parameters["selection_seed"] == parameters["job_seed_root"]:
        raise ValueError("separate roots required")
    raw = parameters["candidate_dates"]
    if not isinstance(raw, list) or any(type(d) is not str for d in raw):
        raise ValueError("explicit candidate pool required")
    pool = splits._dates(tuple(date.fromisoformat(d) for d in raw), 15, 28)
    if raw != [d.isoformat() for d in pool]:
        raise ValueError("canonical sorted unique candidate pool required")
    return pool, parameters["selection_seed"], parameters["job_seed_root"]


def _authorization(receipt: dict, expected_sha256: str, destination: Path) -> None:
    _hash_string(expected_sha256)
    if splits.digest(receipt) != expected_sha256:
        raise ValueError("authorization commitment mismatch")
    required = {
        "version",
        "parameters",
        "destination",
        "reimo_decision",
        "nisha_decision",
        "storage",
        "scope",
    }
    if set(receipt) != required or receipt["version"] != VERSION:
        raise ValueError("incomplete authorization receipt")
    if receipt["scope"] != "metadata_only_not_freeze_or_run":
        raise ValueError("metadata-only authorization required")
    for key in ("reimo_decision", "nisha_decision"):
        if not isinstance(receipt[key], str) or not receipt[key].strip():
            raise ValueError("affected-owner decision locators required")
    storage = receipt["storage"]
    fields = {"platform", "access_control", "authorized_principals", "verification_record"}
    if (
        not isinstance(storage, dict)
        or set(storage) != fields
        or any(not isinstance(v, str) or not v.strip() for v in storage.values())
    ):
        raise ValueError("actual storage capability evidence required")
    if str(destination) != receipt["destination"]:
        raise ValueError("unauthorized destination")
    _parameters(receipt["parameters"])


def _records(parameters: dict) -> tuple[splits.Allocation, ...]:
    pool, selection_seed, job_root = _parameters(parameters)
    dev = _development()  # never invoke the joint allocator or regenerate dev contents
    chosen: list[splits.Window] = []
    for day in sorted(
        pool, key=lambda d: (splits.digest([VERSION, selection_seed, d.isoformat()]), d)
    ):
        window = splits.Window(day)
        if any(w.day.month == day.month for w in chosen):
            continue
        if any(window.overlaps(w) for w in (*chosen, *(r.window for r in dev))):
            continue
        chosen.append(window)
        if len(chosen) == 6:
            break
    if len(chosen) != 6:
        raise ValueError("insufficient isolated dates; no retry")
    held = []
    for window in sorted(chosen, key=lambda w: w.day):
        for scenario in splits.SCENARIOS:
            identity = splits.digest([VERSION, window.day.isoformat(), scenario])
            row = splits.Allocation(
                episode_id="EP-" + identity[:24],
                partition="held_out",
                scenario=scenario,
                seed=int(splits.digest([VERSION, job_root, identity])[:16], 16),
                window=window,
                related_group=splits.digest([carbon.SHA256, window.day.isoformat()]),
            )
            held.append(row)
            if scenario == "normal":
                held.append(
                    replace(
                        row,
                        episode_id="EP-" + splits.digest([VERSION, identity, "withheld"])[:24],
                        withheld=True,
                        parent_id=row.episode_id,
                    )
                )
    records = dev + tuple(held)
    splits.validate_isolation(records)
    if len(held) != 30 or len({r.window.day.month for r in held}) != 6:
        raise ValueError("invalid held-out design")
    return records


def build_metadata(receipt: dict, *, authorization_sha256: str, revision: str) -> dict:
    """Restricted in-memory metadata; authenticate authorization before selection.

    Synthetic receipt use is allowed only in tests, never as study approval.
    """
    destination = _private_path(Path(receipt.get("destination", "")))
    _authorization(receipt, authorization_sha256, destination)
    _hash_string(revision, 40)
    records = _records(receipt["parameters"])
    root = Path(__file__).resolve().parents[2]
    if (
        development.canonical_lf_sha256(root / DEVELOPMENT_CONTENT_RECEIPT)
        != DEVELOPMENT_CONTENT_SHA256
    ):
        raise ValueError("development content commitments changed")
    paths = (
        "dc_sustainability/data/held_out_custody.py",
        "dc_sustainability/data/splits.py",
        "dc_sustainability/data/carbon_source.py",
        "dc_sustainability/data/scenarios.py",
        "dc_sustainability/data/materialize_development.py",
        "dc_sustainability/schemas.py",
        DEVELOPMENT_CONTENT_RECEIPT,
    )
    result = {
        "version": VERSION,
        "authorization": receipt,
        "authorization_sha256": authorization_sha256,
        "code_revision": revision,
        "code_sha256": {p: development.canonical_lf_sha256(root / p) for p in paths},
        "environment": development.environment(),
        "source": development.allocation()[0]["source"],
        "development_allocation_pins": development.PINS,
        "development_content_receipt_sha256": DEVELOPMENT_CONTENT_SHA256,
        "records": [r.metadata() for r in records],
        "scientific_acceptance": False,
        "held_out_contents_generated": False,
        "isolation_status": "conditional_interval_start_Q05_unresolved",
        "variant_contract": "same private jobs and realized carbon; only forecast visibility differs",
        "seed_derivation": "first16hex SHA256([version,job_root,SHA256([version,date,scenario])])",
    }
    result["manifest_sha256"] = splits.digest(result)
    return result


def prepare(receipt: dict, *, authorization_sha256: str, revision: str) -> str:
    """Create a NEW restricted directory; return only a checksum, never allocation.

    Failure leaves evidence of partial output. Never resume. No stdout/logging.
    Caller must hold the parent directory against concurrent hostile modification.
    """
    metadata = build_metadata(receipt, authorization_sha256=authorization_sha256, revision=revision)
    destination = _private_path(Path(receipt["destination"]))
    if not destination.parent.is_dir():
        raise ValueError("existing authorized parent required")
    destination.mkdir(mode=0o700, exist_ok=False)
    payload = development.serialize(metadata)
    with (destination / "metadata.json").open("xb") as stream:
        os.chmod(destination / "metadata.json", 0o600)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    checksum = hashlib.sha256(payload).hexdigest()
    with (destination / "complete.sha256").open("x", encoding="ascii", newline="\n") as stream:
        os.chmod(destination / "complete.sha256", 0o600)
        stream.write(checksum + "\n")
    return checksum


def verify(
    receipt: dict, *, authorization_sha256: str, revision: str, external_sha256: str
) -> None:
    """Require external checksum and exact deterministic regeneration, no public output.

    Same-environment reproduction is strict; cross-environment differences require
    a separate receiving record, never silently suppress code or environment evidence.
    """
    _hash_string(external_sha256)
    expected = build_metadata(receipt, authorization_sha256=authorization_sha256, revision=revision)
    destination = _private_path(Path(receipt["destination"]))
    if {p.name for p in destination.iterdir()} != {"metadata.json", "complete.sha256"}:
        raise ValueError("incomplete or unexpected custody files")
    if any(p.is_symlink() or not p.is_file() for p in destination.iterdir()):
        raise ValueError("custody files rejected")
    payload = (destination / "metadata.json").read_bytes()
    if (
        hashlib.sha256(payload).hexdigest() != external_sha256
        or (destination / "complete.sha256").read_bytes() != (external_sha256 + "\n").encode()
        or payload != development.serialize(expected)
    ):
        raise ValueError("custody verification failed")
