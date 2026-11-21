"""RULE-03: independent check of the evaluator-only accounting sidecar (#241, #242).

RULE-04's generator writes two files per seed domain: the policy-visible case set and an
evaluator-only accounting sidecar (``rule_study_accounting_weights_v1``) with all 30
artificial weights per case. The case checker (``rule_study_cases``) only sees the
visible set, so it cannot check missing-forecast weights. This module checks the
sidecar against its supplied visible set, independently of the generator:

- **well_formed**: exact record fields, 30 integer (not bool) weights per case;
- **binding**: same ``set_id``, ``case_set_sha256`` equals the canonical hash of the
  supplied visible set, and the generator source hash matches the set's metadata;
- **coverage**: every visible case appears exactly once, and nothing else does;
- **identity**: each entry's full-case and workload hashes match the visible case,
  recomputed with the case checker's own identity functions;
- **weight_domain**: slots 0-5 in {100, 200, 300}, drain slots 6-29 all 200;
- **visibility**: ``weights_visible_to_policy`` is false exactly for missing-forecast
  cases; visible scores equal the sidecar weights; hidden cases expose null scores;
- **hidden_profile**: normal and missing-forecast weights vary over slots 0-5 (the
  generator's nonconstant-profile acceptance, which the visible checker cannot see for
  missing-forecast cases).

It also provides ``job_impact`` and ``site_impact``, independent reference arithmetic for
the declared unit (power_kW x 1 h x PUE 1.0 x weight, in score-kWh) so later metric
records can be recomputed. A PASS here says only that the supplied pair is consistent;
it does not authenticate who generated it, its seed, freeze state or any policy result.
Standard library only; it does not import the generator.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Mapping

from dc_sustainability.evaluation import rule_study_cases as rc
from dc_sustainability.evaluation import rule_study_verifier as v

RECORD_KIND = "rule_study_accounting_check_v1"
SIDECAR_KIND = "rule_study_accounting_weights_v1"
SIDECAR_FIELDS = frozenset(
    {
        "record_kind",
        "set_id",
        "case_set_sha256",
        "generator_source_sha256",
        "visibility",
        "units",
        "cases",
    }
)
ENTRY_FIELDS = frozenset(
    {"case_id", "full_case_sha256", "workload_sha256", "weights", "weights_visible_to_policy"}
)
PUE = 1
HIDDEN_STRATA = frozenset({"missing_forecast"})
NONCONSTANT_STRATA = frozenset({"normal_feasible", "missing_forecast"})


def _hex64(value) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _entry_problem(entry) -> str | None:
    if not isinstance(entry, Mapping) or set(entry) != ENTRY_FIELDS:
        return "unsupported or missing entry fields"
    if not isinstance(entry["case_id"], str) or not entry["case_id"].strip():
        return "nonempty case_id required"
    if not _hex64(entry["full_case_sha256"]) or not _hex64(entry["workload_sha256"]):
        return "hashes must be 64 lowercase hex characters"
    weights = entry["weights"]
    if not isinstance(weights, list) or len(weights) != v.HORIZON:
        return f"weights must list {v.HORIZON} slots"
    if any(type(w) is not int for w in weights):
        return "weights must be integers, not bool/float"
    if type(entry["weights_visible_to_policy"]) is not bool:
        return "weights_visible_to_policy must be bool"
    return None


def _verdict(problems: list, checked: int) -> dict:
    if checked == 0:
        return {"status": "NOT_RUN", "reason": "nothing to check", "checked": 0}
    return {"status": "FAIL" if problems else "PASS", "checked": checked, "failures": problems}


def check_accounting(case_set: Mapping, sidecar: Mapping) -> dict:
    """Check one sidecar against the visible case set it claims to describe."""
    rc._validate_set(case_set)
    if not isinstance(sidecar, Mapping) or not isinstance(sidecar.get("cases"), list):
        raise ValueError("sidecar must be an object with a cases list")
    if len(sidecar["cases"]) > rc.MAX_CASES_PER_SET:
        raise ValueError("sidecar reader limit exceeded")

    header = []
    if set(sidecar) != SIDECAR_FIELDS:
        header.append("unsupported or missing sidecar fields")
    if sidecar.get("record_kind") != SIDECAR_KIND:
        header.append(f"record_kind must be {SIDECAR_KIND}")
    entries, malformed = {}, []
    ids = Counter()
    for n, entry in enumerate(sidecar["cases"]):
        problem = _entry_problem(entry)
        if problem:
            malformed.append({"index": n, "reason": problem})
            continue
        ids[entry["case_id"]] += 1
        entries.setdefault(entry["case_id"], entry)

    visible, unreadable = {}, []
    for raw in case_set["cases"]:
        try:
            case = rc._case_from_dict(raw)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            unreadable.append({"case_id": rc._safe_id(raw), "reason": str(exc)})
            continue
        if raw.get("stratum") not in rc.STRATA:
            unreadable.append({"case_id": case.case_id, "reason": "unknown stratum"})
            continue
        visible[case.case_id] = (raw["stratum"], case)

    binding = []
    if sidecar.get("set_id") != case_set["set_id"]:
        binding.append("set_id differs from the visible set")
    if sidecar.get("case_set_sha256") != v.canonical_sha256(case_set):
        binding.append("case_set_sha256 does not match the supplied visible set")
    meta = case_set.get("metadata")
    claimed = meta.get("generator_source_sha256") if isinstance(meta, Mapping) else None
    if claimed is None:
        binding.append("visible set records no generator_source_sha256")
    elif sidecar.get("generator_source_sha256") != claimed:
        binding.append("generator_source_sha256 differs from the visible set")

    coverage = []
    duplicates = sorted(i for i, k in ids.items() if k > 1)
    if duplicates:
        coverage.append({"duplicate_case_ids": duplicates})
    missing = sorted(set(visible) - set(entries))
    extra = sorted(set(entries) - set(visible))
    if missing:
        coverage.append({"missing_from_sidecar": missing})
    if extra:
        coverage.append({"not_in_visible_set": extra})

    identity, domain, visibility, profile = [], [], [], []
    paired = sorted(set(visible) & set(entries))
    for case_id in paired:
        stratum, case = visible[case_id]
        entry = entries[case_id]
        weights = tuple(entry["weights"])
        if entry["full_case_sha256"] != v.canonical_sha256(rc.case_identity(case)):
            identity.append({"case_id": case_id, "field": "full_case_sha256"})
        if entry["workload_sha256"] != v.canonical_sha256(rc.workload_identity(case)):
            identity.append({"case_id": case_id, "field": "workload_sha256"})
        head, tail = weights[: rc.AUTHORED_SLOTS], weights[rc.AUTHORED_SLOTS :]
        if not set(head) <= rc.SCORE_VALUES or any(w != rc.DRAIN_SCORE for w in tail):
            domain.append(case_id)
        hidden = stratum in HIDDEN_STRATA
        if entry["weights_visible_to_policy"] == hidden:
            visibility.append({"case_id": case_id, "reason": "visibility flag disagrees"})
        if hidden and case.scores is not None:
            visibility.append({"case_id": case_id, "reason": "hidden weights exposed"})
        if not hidden and case.scores != weights:
            visibility.append({"case_id": case_id, "reason": "visible scores differ"})
        if stratum in NONCONSTANT_STRATA and len(set(head)) == 1:
            profile.append(case_id)

    hidden_checked = sum(1 for c in paired if visible[c][0] in NONCONSTANT_STRATA)
    checks = {
        "well_formed": _verdict(
            header + malformed + unreadable,
            len(sidecar["cases"]) + len(case_set["cases"]),
        ),
        "binding": _verdict(binding, 3),
        "coverage": _verdict(coverage, len(visible)),
        "identity": _verdict(identity, len(paired)),
        "weight_domain": _verdict(domain, len(paired)),
        "visibility": _verdict(visibility, len(paired)),
        "hidden_profile": _verdict(profile, hidden_checked),
    }
    statuses = [c["status"] for c in checks.values()]
    overall = (
        "FAIL"
        if "FAIL" in statuses
        else "PASS"
        if all(s == "PASS" for s in statuses)
        else "INCOMPLETE"
    )
    return {
        "record_kind": RECORD_KIND,
        "checker_source_sha256": _own_sha256(),
        "case_checker_source_sha256": hashlib.sha256(
            Path(rc.__file__).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
        "set_id": case_set["set_id"],
        "case_set_sha256": v.canonical_sha256(case_set),
        "sidecar_sha256": v.canonical_sha256(sidecar),
        "cases": {
            "visible": len(case_set["cases"]),
            "sidecar": len(sidecar["cases"]),
            "paired": len(paired),
            "hidden": sum(1 for c in paired if visible[c][0] in HIDDEN_STRATA),
        },
        "checks": checks,
        "overall": overall,
        "scope": "supplied visible-set/sidecar pair only; not seed, provenance, freeze, "
        "generator acceptance or any policy/metric result",
        "notes": [
            "Weights are artificial scores, not g/kWh or emissions.",
            "The sidecar is evaluator-only and must never be given to a policy.",
        ],
    }


def job_impact(case: v.Case, weights, starts: Mapping[str, int]) -> int:
    """Synthetic job impact in score-kWh: sum of power_kW x 1 h x PUE x weight per run slot."""
    weights = tuple(weights)
    if len(weights) != v.HORIZON:
        raise ValueError(f"weights must list {v.HORIZON} slots")
    jobs = {j.job_id: j for j in case.jobs}
    if set(starts) - set(jobs):
        raise ValueError("starts name unknown jobs")
    total = 0
    for job_id, start in starts.items():
        job = jobs[job_id]
        if type(start) is not int or start < 0 or start + job.duration_slots > v.HORIZON:
            raise ValueError(f"start for {job_id} outside the horizon")
        total += job.power_kw * PUE * sum(weights[start : start + job.duration_slots])
    return total


def site_impact(case: v.Case, weights, starts: Mapping[str, int]) -> int:
    """Job impact plus background_kW over all 30 slots, same unit and PUE."""
    weights = tuple(weights)
    return job_impact(case, weights, starts) + case.background_kw * PUE * sum(weights)


def load_sidecar(path: Path) -> Mapping:
    with Path(path).open("rb") as handle:
        raw = handle.read(rc.MAX_INPUT_BYTES + 1)
    if len(raw) > rc.MAX_INPUT_BYTES:
        raise ValueError("sidecar input byte limit exceeded")

    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ValueError("duplicate JSON key")
            data[key] = value
        return data

    def reject_constant(value):
        raise ValueError("nonfinite JSON number")

    data = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
    if not isinstance(data, Mapping) or not isinstance(data.get("cases"), list):
        raise ValueError("sidecar must be an object with a cases list")
    return data


def _own_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
