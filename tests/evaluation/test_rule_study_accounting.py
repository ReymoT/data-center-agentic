"""RULE-03 accounting-sidecar checker: binding, coverage, identity, weights and visibility.

All inputs are hand-built pairs in the RULE-04 sidecar shape, not generator output.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from dc_sustainability.evaluation import rule_study_accounting as ra
from dc_sustainability.evaluation import rule_study_cases as rc
from dc_sustainability.evaluation import rule_study_trace as tr
from dc_sustainability.evaluation import rule_study_verifier as v

ROOT = Path(__file__).parents[2]
GEN_SHA = "a" * 64
PROFILE = [100, 300, 200, 200, 100, 300] + [200] * 24


def job(job_id, power, duration, arrival, deadline, flexible):
    return {
        "job_id": job_id,
        "power_kw": power,
        "duration_slots": duration,
        "arrival_slot": arrival,
        "deadline_slot": deadline,
        "flexible": flexible,
    }


def visible(case_id, stratum, jobs, label="jointly_feasible"):
    return {
        "case_id": case_id,
        "stratum": stratum,
        "feasibility_label": label,
        "capacity_kw": 60,
        "background_kw": 20,
        "scores": None if stratum == "missing_forecast" else list(PROFILE),
        "jobs": jobs,
    }


CASES = [
    visible("N1", "normal_feasible", [job("J1", 20, 1, 0, 3, True), job("J2", 20, 2, 1, 3, False)]),
    visible(
        "O1",
        "overloaded_impossible",
        [
            job("J1", 30, 1, 0, 1, False),
            job("J2", 30, 1, 0, 1, False),
            job("J3", 10, 1, 2, 4, True),
        ],
        label="jointly_infeasible",
    ),
    visible(
        "M1", "missing_forecast", [job("J1", 10, 2, 0, 3, True), job("J2", 30, 1, 1, 2, False)]
    ),
]


def entry(raw, weights=PROFILE):
    case = tr.case_from_dict(raw)
    return {
        "case_id": raw["case_id"],
        "full_case_sha256": v.canonical_sha256(rc.case_identity(case)),
        "workload_sha256": v.canonical_sha256(rc.workload_identity(case)),
        "weights": list(weights),
        "weights_visible_to_policy": raw["stratum"] != "missing_forecast",
    }


def seal(case_set, sidecar):
    sidecar["case_set_sha256"] = v.canonical_sha256(case_set)
    return case_set, sidecar


def pair():
    case_set = {
        "set_id": "dev",
        "cases": copy.deepcopy(CASES),
        "metadata": {"generator_source_sha256": GEN_SHA},
    }
    sidecar = {
        "record_kind": ra.SIDECAR_KIND,
        "set_id": "dev",
        "case_set_sha256": "",
        "generator_source_sha256": GEN_SHA,
        "visibility": "evaluator-only; never supply to a policy",
        "units": "artificial score weights per slot",
        "cases": [entry(c) for c in CASES],
    }
    return seal(case_set, sidecar)


def status(report, name):
    return report["checks"][name]["status"]


def test_consistent_pair_passes():
    report = ra.check_accounting(*pair())
    assert report["overall"] == "PASS"
    assert report["cases"] == {"visible": 3, "sidecar": 3, "paired": 3, "hidden": 1}
    assert all(c["status"] == "PASS" for c in report["checks"].values())


def test_changed_visible_set_breaks_binding():
    case_set, sidecar = pair()
    case_set["cases"][0]["scores"][0] = 300
    report = ra.check_accounting(case_set, sidecar)
    assert status(report, "binding") == "FAIL"
    assert report["overall"] == "FAIL"


@pytest.mark.parametrize(
    "field,value", [("set_id", "final"), ("generator_source_sha256", "b" * 64)]
)
def test_header_mismatch_breaks_binding(field, value):
    case_set, sidecar = pair()
    sidecar[field] = value
    assert status(ra.check_accounting(case_set, sidecar), "binding") == "FAIL"


def test_visible_set_without_generator_hash_fails_binding():
    case_set, sidecar = pair()
    del case_set["metadata"]
    case_set, sidecar = seal(case_set, sidecar)
    assert status(ra.check_accounting(case_set, sidecar), "binding") == "FAIL"


def test_missing_extra_and_duplicate_entries_fail_coverage():
    case_set, sidecar = pair()
    sidecar["cases"].pop()
    report = ra.check_accounting(case_set, sidecar)
    assert status(report, "coverage") == "FAIL"
    assert {"missing_from_sidecar": ["M1"]} in report["checks"]["coverage"]["failures"]

    case_set, sidecar = pair()
    stray = copy.deepcopy(sidecar["cases"][0])
    stray["case_id"] = "X9"
    sidecar["cases"].append(stray)
    assert status(ra.check_accounting(case_set, sidecar), "coverage") == "FAIL"

    case_set, sidecar = pair()
    sidecar["cases"].append(copy.deepcopy(sidecar["cases"][0]))
    report = ra.check_accounting(case_set, sidecar)
    assert {"duplicate_case_ids": ["N1"]} in report["checks"]["coverage"]["failures"]


@pytest.mark.parametrize("field", ["full_case_sha256", "workload_sha256"])
def test_wrong_identity_hash_fails(field):
    case_set, sidecar = pair()
    sidecar["cases"][1][field] = "0" * 64
    report = ra.check_accounting(case_set, sidecar)
    assert status(report, "identity") == "FAIL"
    assert report["checks"]["identity"]["failures"] == [{"case_id": "O1", "field": field}]


def test_full_hash_uses_visible_not_hidden_scores():
    # The missing-forecast full identity has scores null, as the generator records it.
    case_set, sidecar = pair()
    hidden = tr.case_from_dict(CASES[2])
    assert hidden.scores is None
    assert sidecar["cases"][2]["full_case_sha256"] == v.canonical_sha256(rc.case_identity(hidden))
    assert status(ra.check_accounting(case_set, sidecar), "identity") == "PASS"


@pytest.mark.parametrize("slot,value", [(0, 150), (6, 100), (29, 300)])
def test_out_of_domain_or_nondrain_weight_fails(slot, value):
    case_set, sidecar = pair()
    sidecar["cases"][2]["weights"][slot] = value  # hidden case: not caught by visibility
    report = ra.check_accounting(case_set, sidecar)
    assert status(report, "weight_domain") == "FAIL"
    assert report["checks"]["weight_domain"]["failures"] == ["M1"]


def test_visibility_flag_must_match_stratum():
    case_set, sidecar = pair()
    sidecar["cases"][2]["weights_visible_to_policy"] = True
    assert status(ra.check_accounting(case_set, sidecar), "visibility") == "FAIL"
    case_set, sidecar = pair()
    sidecar["cases"][0]["weights_visible_to_policy"] = False
    assert status(ra.check_accounting(case_set, sidecar), "visibility") == "FAIL"


def test_visible_scores_must_equal_sidecar_weights():
    case_set, sidecar = pair()
    sidecar["cases"][0]["weights"][1] = 100
    report = ra.check_accounting(case_set, sidecar)
    assert report["checks"]["visibility"]["failures"] == [
        {"case_id": "N1", "reason": "visible scores differ"}
    ]


def test_exposed_hidden_weights_fail_visibility():
    case_set, sidecar = pair()
    case_set["cases"][2]["scores"] = list(PROFILE)
    case_set, sidecar = seal(case_set, sidecar)
    sidecar["cases"][2]["full_case_sha256"] = v.canonical_sha256(
        rc.case_identity(tr.case_from_dict(case_set["cases"][2]))
    )
    report = ra.check_accounting(case_set, sidecar)
    assert {"case_id": "M1", "reason": "hidden weights exposed"} in report["checks"]["visibility"][
        "failures"
    ]


def test_constant_hidden_profile_fails():
    case_set, sidecar = pair()
    sidecar["cases"][2]["weights"] = [200] * 30
    report = ra.check_accounting(case_set, sidecar)
    assert status(report, "hidden_profile") == "FAIL"
    assert report["checks"]["hidden_profile"]["failures"] == ["M1"]


def test_constant_overload_profile_is_allowed():
    case_set, sidecar = pair()
    case_set["cases"][1]["scores"] = [200] * 30
    case_set, sidecar = seal(case_set, sidecar)
    sidecar["cases"][1] = entry(case_set["cases"][1], [200] * 30)
    assert ra.check_accounting(case_set, sidecar)["overall"] == "PASS"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e["weights"].__setitem__(0, True),
        lambda e: e["weights"].__setitem__(0, 100.0),
        lambda e: e["weights"].pop(),
        lambda e: e.__setitem__("extra", 1),
        lambda e: e.__setitem__("full_case_sha256", "ABC"),
        lambda e: e.__setitem__("weights_visible_to_policy", 1),
    ],
)
def test_malformed_entries_fail_well_formed(mutate):
    case_set, sidecar = pair()
    mutate(sidecar["cases"][0])
    report = ra.check_accounting(case_set, sidecar)
    assert status(report, "well_formed") == "FAIL"
    assert report["overall"] == "FAIL"


def test_wrong_record_kind_or_extra_field_fails():
    case_set, sidecar = pair()
    sidecar["record_kind"] = "rule_study_case_set_v1"
    assert status(ra.check_accounting(case_set, sidecar), "well_formed") == "FAIL"
    case_set, sidecar = pair()
    sidecar["note"] = "x"
    assert status(ra.check_accounting(case_set, sidecar), "well_formed") == "FAIL"


def test_empty_pair_is_not_a_pass():
    case_set, sidecar = pair()
    case_set["cases"], sidecar["cases"] = [], []
    case_set, sidecar = seal(case_set, sidecar)
    report = ra.check_accounting(case_set, sidecar)
    assert report["overall"] == "INCOMPLETE"
    assert status(report, "coverage") == "NOT_RUN"


def test_reader_limit_and_shape_refused():
    case_set, sidecar = pair()
    with pytest.raises(ValueError):
        ra.check_accounting(case_set, {"cases": "nope"})
    sidecar["cases"] = sidecar["cases"] * 41
    with pytest.raises(ValueError, match="limit"):
        ra.check_accounting(case_set, sidecar)


def test_impact_arithmetic():
    case = tr.case_from_dict(CASES[0])
    weights = PROFILE
    # J1 20 kW at slot 1 (300); J2 20 kW x 2 slots at 2-3 (200+200).
    assert ra.job_impact(case, weights, {"J1": 1, "J2": 2}) == 20 * 300 + 20 * 400
    assert ra.job_impact(case, weights, {}) == 0
    assert ra.site_impact(case, weights, {"J1": 1}) == 20 * 300 + 20 * sum(PROFILE)


@pytest.mark.parametrize(
    "starts,weights",
    [({"J9": 0}, PROFILE), ({"J2": 29}, PROFILE), ({"J1": -1}, PROFILE), ({"J1": 0}, [200])],
)
def test_impact_refuses_bad_inputs(starts, weights):
    with pytest.raises(ValueError):
        ra.job_impact(tr.case_from_dict(CASES[0]), weights, starts)


def test_load_sidecar_refuses_duplicate_keys_and_nan(tmp_path):
    dup = tmp_path / "dup.json"
    dup.write_text('{"cases": [], "cases": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        ra.load_sidecar(dup)
    nan = tmp_path / "nan.json"
    nan.write_text('{"cases": [NaN]}', encoding="utf-8")
    with pytest.raises(ValueError, match="nonfinite"):
        ra.load_sidecar(nan)


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_rule_study_accounting.py"), *args],
        capture_output=True,
        text=True,
    )


def test_cli_exit_codes_and_exclusive_output(tmp_path):
    case_set, sidecar = pair()
    cases = _write(tmp_path / "cases.json", case_set)
    good = _write(tmp_path / "acct.json", sidecar)
    out = tmp_path / "report.json"
    result = _cli("--cases", str(cases), "--accounting", str(good), "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert json.loads(out.read_text("utf-8"))["overall"] == "PASS"
    again = _cli("--cases", str(cases), "--accounting", str(good), "--out", str(out))
    assert again.returncode != 0 and "refusing to overwrite" in again.stderr

    sidecar["cases"].pop()
    bad = _write(tmp_path / "bad.json", sidecar)
    assert _cli("--cases", str(cases), "--accounting", str(bad)).returncode == 1
