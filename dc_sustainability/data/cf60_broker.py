"""Opt-in CF60-v1 broker. Privileged ingestion is deliberately outside this module.

RestrictedHistory retains only authorized rows, never an unrestricted loader or
full-series reference. This is a capability boundary for trusted Python code,
not a sandbox against arbitrary code execution/introspection in the same process.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from types import MappingProxyType

from dc_sustainability import schemas as s

VERSION = "CF60-v1"
IMPLEMENTATION = "cf60-restricted-broker-v1"
H = timedelta(hours=1)
ORIGIN = datetime(2022, 1, 1, tzinfo=timezone.utc)
STOP = datetime(2023, 1, 1, tzinfo=timezone.utc)


def utc_hour(value):
    if (
        not isinstance(value, datetime)
        or value.utcoffset() != timedelta(0)
        or value.minute
        or value.second
        or value.microsecond
    ):
        raise ValueError("explicit UTC hour required")


def candidates(issue, interpretation):
    utc_hour(issue)
    if interpretation not in {"start", "end"}:
        raise ValueError("explicit conditional start/end interpretation required")
    return tuple(issue - age * H - (H if interpretation == "start" else 0 * H) for age in (2, 3, 4))


def bundle_hashes():
    root = Path(__file__).resolve().parents[2]
    paths = (
        "dc_sustainability/data/cf60_broker.py",
        "dc_sustainability/data/cf60_acquisition.py",
        "dc_sustainability/data/cf60_receiving.py",
        "dc_sustainability/data/carbon_source.py",
        "dc_sustainability/schemas.py",
    )
    return {p: sha256((root / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in paths}


def code_hash():
    """Canonical LF source identity, reproducible across host line endings."""
    return sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


class RestrictedHistory:
    """Issue-scoped row capability minted by a privileged acquisition process.

    Constructor consumes an already filtered iterable; full CSV parsing/checksum
    validation is privileged and must not be called a restricted operation.
    Missing/out-of-year candidates are recorded without consulting a backing store.
    Every public read attempt is logged before validation. No enumeration/loader API.
    """

    __slots__ = (
        "__rows",
        "__allowed",
        "__attempts",
        "issue",
        "interpretation",
        "source",
        "authorization",
    )

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("immutable issue capability")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise AttributeError("immutable issue capability")

    def __init__(self, rows, *, issue, interpretation, source: s.SourceRef, authorization: str):
        if type(source) is not s.SourceRef:
            raise TypeError("plain F02 SourceRef metadata required; no privileged handles")
        if type(authorization) is not str or not authorization.strip() or not source.sha256:
            raise ValueError("input authorization and checksum-pinned source required")
        self.issue, self.interpretation = issue, interpretation
        self.source, self.authorization = source, authorization
        self.__allowed = candidates(issue, interpretation)
        self.__attempts = []
        selected = {}
        for label, value in rows:
            utc_hour(label)
            if label not in self.__allowed or not ORIGIN <= label < STOP:
                raise PermissionError("row outside issue authorization")
            if label in selected:
                raise ValueError("duplicate row")
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError("malformed source evidence")
            selected[label] = value
        self.__rows = MappingProxyType(selected)

    def read(self, label):
        event = {"label": str(label), "status": "rejected"}
        self.__attempts.append(event)
        utc_hour(label)
        if label not in self.__allowed:
            raise PermissionError("out-of-allowlist source read")
        value = self.__rows.get(label)
        event["status"] = "missing" if value is None else "read"
        return value

    def footprint(self):
        return tuple(dict(event) for event in self.__attempts)


@dataclass(frozen=True)
class IssueResult:
    forecasts: tuple[s.CarbonForecast, ...]
    missing_slots: tuple[int, ...]
    receipt_json: str


def issue_forecast(history: RestrictedHistory, *, anchor, slot: int, trusted_issue):
    """Reissue at trusted runner time; return only the current F02 visible horizon.

    Caller must mint a fresh capability per issue and publish the result atomically
    at trusted_issue. No policy-supplied clock or precomputed schedule is accepted.
    Q04 assessment/fallback remains the existing consumer's responsibility.
    """
    if type(history) is not RestrictedHistory:
        raise TypeError("restricted issue capability required; no arrays/loaders")
    utc_hour(anchor)
    utc_hour(trusted_issue)
    if type(slot) is not int or not 0 <= slot < 30:
        raise ValueError("slot 0..29 required")
    if trusted_issue != anchor + slot * H or history.issue != trusted_issue:
        raise ValueError("trusted clock/capability mismatch")
    if history.footprint():
        raise ValueError("fresh unused capability required")
    labels = candidates(trusted_issue, history.interpretation)
    values = [history.read(label) for label in labels]
    selected = next((i for i, value in enumerate(values) if value is not None), None)
    visible = tuple(range(slot, min(slot + 24, 30)))
    facts = (
        ()
        if selected is None
        else tuple(
            s.CarbonForecast(
                fact_id=f"FACT-CF60-{slot}-{v}",
                value=values[selected],
                unit="g/kWh",
                source_id=history.source.source_id,
                source_sha256=history.source.sha256,
                valid_slot=v,
                issued_at_utc=trusted_issue,
                forecast_kind="persistence",
                semantics=s.CarbonSemantics(
                    pollutant_basis="unresolved",
                    interval_convention="unresolved",
                    emissions_factor_type="average",
                    slot_mapping_status="provisional",
                ),
                quality_status="unvalidated",
            )
            for v in visible
        )
    )
    receipt = {
        "algorithm": VERSION,
        "implementation": IMPLEMENTATION,
        "code_sha256": code_hash(),
        "bundle_sha256": bundle_hashes(),
        "source": history.source.to_jsonable(),
        "input_authorization": history.authorization,
        "interpretation": history.interpretation,
        "issue": trusted_issue.isoformat(),
        "anchor": anchor.isoformat(),
        "slot": slot,
        "lag_hours": 1,
        "completion_ages_hours": [2, 3, 4],
        "attempts": history.footprint(),
        "selected_label": None if selected is None else labels[selected].isoformat(),
        "output_hashes": [f.canonical_hash() for f in facts],
        "missing_slots": list(visible) if selected is None else [],
        "scientific_adoption": False,
    }
    receipt["footprint_sha256"] = s.sha256_hex(receipt["attempts"])
    return IssueResult(facts, visible if selected is None else (), s.canonical_json(receipt))
