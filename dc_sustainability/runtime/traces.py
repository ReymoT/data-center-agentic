"""Durable immutable F02 traces and private execution-intent reservations.

The directory is an explicit caller input. No experiment checkpoint/resume,
storage permission or external service is configured by this module.
"""

import json
import os
import re
from pathlib import Path
from uuid import uuid4

from dc_sustainability import schemas as s


class IndeterminateExecution(RuntimeError):
    """Reserved effect has no final trace: reconcile actual state, never auto-retry."""


def _publish(path, text):
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


class TraceStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._intents = self.directory / ".execution-intents"
        self._intents.mkdir(exist_ok=True)

    def _path(self, decision_id):
        # Use the real F02 identifier boundary before constructing any path.
        if not isinstance(decision_id, str) or not decision_id.startswith("DEC-"):
            raise ValueError("invalid decision ID")
        if not re.fullmatch(r"DEC-[A-Za-z0-9][A-Za-z0-9_.:-]{0,59}", decision_id):
            raise ValueError("invalid decision ID")
        # Colon is legal in F02 IDs but not a Windows filename; hash all IDs.
        return self.directory / f"{s.sha256_hex(decision_id)}.json"

    def read(self, decision_id):
        record = s.DecisionRecord.from_json(self._path(decision_id).read_text(encoding="utf-8"))
        if record.decision_id != decision_id:
            raise ValueError("trace identity does not match requested ID")
        return record

    def write(self, record):
        record = s.DecisionRecord.model_validate(record.model_dump(mode="python"), strict=True)
        path = self._path(record.decision_id)
        try:
            _publish(path, record.to_json() + "\n")
        except FileExistsError:
            if self.read(record.decision_id) != record:
                raise ValueError(
                    "a different immutable trace already uses this decision ID"
                ) from None
        return path

    def _intent(self, record, stage, expected_state_version):
        key = s.sha256_hex((record.run_id, record.system, record.episode_id, record.slot))
        path = self._intents / f"{key}.json"
        intent = {
            "decision_id": record.decision_id,
            "fingerprint": s.sha256_hex((record.to_json(), stage, expected_state_version)),
        }
        return path, intent

    def replay(self, record, stage, expected_state_version):
        path, intent = self._intent(record, stage, expected_state_version)
        if path.exists():
            previous = json.loads(path.read_text(encoding="utf-8"))
            if previous != intent:
                raise ValueError(
                    "run/system/episode/slot is already reserved for another request"
                ) from None
            try:
                return self.read(record.decision_id)
            except FileNotFoundError:
                raise IndeterminateExecution(
                    "reserved execution has no final trace; reconcile state"
                ) from None
        if self._path(record.decision_id).exists():
            raise ValueError("decision ID already has a trace outside this execution request")
        return None

    def reserve(self, record, stage, expected_state_version):
        """Reserve one effect after live identity validation, before execution."""
        path, intent = self._intent(record, stage, expected_state_version)
        try:
            _publish(path, json.dumps(intent, sort_keys=True) + "\n")
        except FileExistsError:
            return self.replay(record, stage, expected_state_version)
        return None
