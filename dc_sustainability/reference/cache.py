"""O02 deterministic reference-label cache.

This module provides a deterministic, input-sensitive cache key and a persistent
store for certified reference solver results.  Cached results are immutable: once
written, a cache entry is never replaced.  Corrupted or schema-outdated entries are
treated as misses so the caller can re-run the reference solver safely.

The cache key covers every input that can change the reference label set:

* visible state fingerprint (``VisibleState.canonical_hash``)
* decision slot / state version / episode id
* context content hash (constraints, forecasts, sources, evidence ids)
* candidate set (job_id, start_slot) derived from the feature rows
* solver configuration (backend, backend_version, tolerance, time_limit_s)
* reference solver implementation version
* label schema version

Only ``certified_optimal`` results are cached as usable label sources.  Other
solver statuses may be stored for audit but will never produce training labels.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from dc_sustainability import schemas as s
from dc_sustainability.reference import solver as solver_module
from dc_sustainability.reference.labels import CandidateLabel
from dc_sustainability.training.features import FeatureRow

_LABEL_SCHEMA_VERSION = s.SCHEMA_VERSION
_REFERENCE_SOLVER_VERSION = "1.0.0"
_CACHE_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class CacheKey:
    """Deterministic fingerprint of every input that can change reference labels."""

    state_hash: str
    context_hash: str
    candidate_hash: str
    backend: str
    backend_version: str
    tolerance: Optional[float]
    time_limit_s: Optional[float]
    reference_solver_version: str
    label_schema_version: str

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "state_hash": self.state_hash,
            "context_hash": self.context_hash,
            "candidate_hash": self.candidate_hash,
            "backend": self.backend,
            "backend_version": self.backend_version,
            "tolerance": self.tolerance,
            "time_limit_s": self.time_limit_s,
            "reference_solver_version": self.reference_solver_version,
            "label_schema_version": self.label_schema_version,
        }

    def digest(self) -> str:
        return s.sha256_hex(self.canonical_dict())


def _candidate_set_hash(rows: tuple[FeatureRow, ...]) -> str:
    """Hash the ordered candidate keys that the solver labels."""
    keys = tuple((row.job_id, row.start_slot) for row in rows)
    return s.sha256_hex({"candidates": keys})


def make_cache_key(
    state: s.VisibleState,
    context: s.Context,
    rows: tuple[FeatureRow, ...],
    *,
    backend: str,
    backend_version: str,
    tolerance: Optional[float],
    time_limit_s: Optional[float],
) -> CacheKey:
    """Build a deterministic cache key from all label-relevant inputs."""
    return CacheKey(
        state_hash=state.canonical_hash(),
        context_hash=context.content_hash,
        candidate_hash=_candidate_set_hash(rows),
        backend=backend,
        backend_version=backend_version,
        tolerance=tolerance,
        time_limit_s=time_limit_s,
        reference_solver_version=_REFERENCE_SOLVER_VERSION,
        label_schema_version=_LABEL_SCHEMA_VERSION,
    )


def _publish(path: Path, text: str) -> None:
    """Publish fully written bytes exclusively; never replace an existing artifact."""
    temp = path.parent / f".{uuid4().hex}.tmp"
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class LabelCache:
    """Persistent immutable cache of certified reference solver results and labels."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: CacheKey) -> Path:
        return self.directory / f"{key.digest()}.json"

    def _entry_path(self, key: CacheKey) -> Path:
        return self.directory / f"{key.digest()}.entry.json"

    def _load_entry(self, path: Path) -> Optional[dict[str, Any]]:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        if data.get("cache_schema_version") != _CACHE_SCHEMA_VERSION:
            return None
        if data.get("label_schema_version") != _LABEL_SCHEMA_VERSION:
            return None
        return data

    def get(self, key: CacheKey) -> Optional[s.SolverResult]:
        """Return a cached certified result, or None on miss/invalidation."""
        entry = self._load_entry(self._entry_path(key))
        if entry is None:
            return None
        result_path = Path(entry["result_path"])
        if not result_path.exists():
            return None
        try:
            result = s.SolverResult.from_json(result_path.read_text(encoding="utf-8"))
        except (s.ContractError, OSError, ValueError):
            return None
        if result.status != "certified_optimal":
            return None
        if result.input_hash != key.context_hash:
            return None
        return result

    def put(
        self,
        key: CacheKey,
        result: s.SolverResult,
        labels: tuple[CandidateLabel, ...],
    ) -> Path:
        """Atomically store a certified result and its labels.

        Raises FileExistsError if an entry already exists for this key with different
        content.  Returns the path of the stored result file.
        """
        result_path = self._path(key)
        entry_path = self._entry_path(key)

        result_text = result.to_json() + "\n"
        entry = {
            "cache_schema_version": _CACHE_SCHEMA_VERSION,
            "label_schema_version": _LABEL_SCHEMA_VERSION,
            "reference_solver_version": _REFERENCE_SOLVER_VERSION,
            "key": key.canonical_dict(),
            "result_path": str(result_path),
            "labels": [
                {
                    "episode_id": label.episode_id,
                    "slot": label.slot,
                    "state_version": label.state_version,
                    "job_id": label.job_id,
                    "start_slot": label.start_slot,
                    "label": label.label,
                    "source_solver_result_id": label.source_solver_result_id,
                    "state_hash": label.state_hash,
                    "candidate_hash": label.candidate_hash,
                }
                for label in labels
            ],
        }
        entry_text = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"

        if result_path.exists():
            existing = result_path.read_text(encoding="utf-8")
            if existing != result_text:
                raise FileExistsError(
                    f"cache collision: result file exists with different content for key {key.digest()}"
                )
        else:
            _publish(result_path, result_text)

        if entry_path.exists():
            existing_entry = entry_path.read_text(encoding="utf-8")
            if existing_entry != entry_text:
                raise FileExistsError(
                    f"cache collision: entry file exists with different content for key {key.digest()}"
                )
        else:
            _publish(entry_path, entry_text)

        return result_path

    def labels_for(self, key: CacheKey) -> Optional[tuple[CandidateLabel, ...]]:
        """Return cached labels for a key, or None on miss/invalidation."""
        entry = self._load_entry(self._entry_path(key))
        if entry is None:
            return None
        label_dicts = entry.get("labels")
        if not isinstance(label_dicts, list):
            return None
        out: list[CandidateLabel] = []
        for d in label_dicts:
            if not isinstance(d, dict):
                return None
            try:
                out.append(
                    CandidateLabel(
                        episode_id=d["episode_id"],
                        slot=d["slot"],
                        state_version=d["state_version"],
                        job_id=d["job_id"],
                        start_slot=d["start_slot"],
                        label=d["label"],
                        source_solver_result_id=d["source_solver_result_id"],
                        state_hash=d["state_hash"],
                        candidate_hash=d["candidate_hash"],
                    )
                )
            except (KeyError, TypeError, ValueError):
                return None
        return tuple(out)


def _solver_backend_info() -> tuple[str, str]:
    """Return the canonical backend name and version for cache keys."""
    return (solver_module._BACKENDS[0], solver_module._BACKEND_VERSION)
