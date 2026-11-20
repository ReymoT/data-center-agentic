"""RULE-04 generator: draw order, acceptance, identity, isolation and checker agreement.

Only the development seed domain is generated here. The final set must not exist before the
rule/verifier freeze and bounded approval, so final-domain tests cover the refusal paths only.
"""

import copy
import json
import random
from pathlib import Path

import pytest

from dc_sustainability.evaluation import rule_study_cases as rc
from dc_sustainability.evaluation import rule_study_generator as g

ROOT = Path(__file__).parents[2]
SPEC = json.loads((ROOT / "docs/rule_study/specification.json").read_text("utf-8"))
SCRIPT = ROOT / "scripts" / "generate_rule_study_cases.py"


@pytest.fixture(scope="module")
def development():
    return g.generate("development", spec=SPEC)


def J(job_id, power, duration, arrival, deadline, flexible):
    return g.Job(job_id, power, duration, arrival, deadline, flexible)


# --- Draw order ----------------------------------------------------------------------------


def _hand_draw(rng, counts):
    """The spec's draw order written out longhand, independent of draw_proposal."""
    count = rng.choice(counts)
    jobs = []
    for i in range(1, count + 1):
        power = rng.choice((10, 20, 30))
        duration = rng.choice((1, 2))
        arrival = rng.choice((0, 1, 2))
        flexible = rng.choice((False, True))
        slack = rng.choice((0, 1, 2))
        jobs.append(
            (f"J{i}", power, duration, arrival, min(6, arrival + duration + slack), flexible)
        )
    head = [rng.choice((100, 200, 300)) for _ in range(6)]
    return jobs, head + [200] * 24


def test_first_development_case_matches_hand_traced_draws(development):
    case_set, _ = development
    first = case_set["cases"][0]
    assert first["generator_attempt"] == 2
    rng = random.Random(2026111901)
    _hand_draw(rng, (2, 3, 4))  # attempt 1 was rejected
    jobs, scores = _hand_draw(rng, (2, 3, 4))
    assert [tuple(j.values()) for j in first["jobs"]] == jobs
    assert first["scores"] == scores


def test_first_development_case_golden_values(development):
    first = development[0]["cases"][0]
    assert [tuple(j.values()) for j in first["jobs"]] == [
        ("J1", 20, 2, 0, 3, False),
        ("J2", 30, 1, 2, 4, True),
        ("J3", 20, 1, 1, 3, False),
    ]
    assert first["scores"][:6] == [100, 100, 200, 300, 300, 200]


def test_overload_consumes_the_same_draws_as_any_other_proposal():
    a, b = random.Random(7), random.Random(7)
    g.draw_proposal(a, "overloaded_impossible")
    _hand_draw(b, (3, 4))
    assert a.getstate() == b.getstate()


def test_overload_proposals_carry_the_fixed_conflict_pair():
    rng = random.Random(11)
    for _ in range(50):
        proposal = g.draw_proposal(rng, "overloaded_impossible")
        assert proposal.jobs[:2] == g.CONFLICT_PAIR
        assert len(proposal.jobs) in (3, 4)


def test_generation_is_byte_deterministic(development):
    again = g.generate("development", spec=SPEC)
    assert g.dumps(again[0]) == g.dumps(development[0])
    assert g.dumps(again[1]) == g.dumps(development[1])


# --- Feasibility and acceptance ------------------------------------------------------------


@pytest.mark.parametrize(
    ("jobs", "expected"),
    [
        ((J("J1", 30, 1, 0, 1, False), J("J2", 30, 1, 0, 1, False)), False),  # case B
        ((J("J1", 30, 1, 0, 1, False), J("J2", 30, 1, 0, 2, True)), True),  # B-progress
        ((J("J1", 20, 2, 0, 2, False), J("J2", 30, 1, 1, 2, False)), False),  # overlap at slot 1
        (
            (J("J1", 20, 2, 0, 3, True), J("J2", 30, 1, 1, 2, False)),
            False,
        ),  # both starts hit slot 1
        ((J("J1", 20, 2, 0, 4, True), J("J2", 30, 1, 1, 2, False)), True),  # J1 moves after
        ((J("J1", 40, 1, 0, 1, False),), True),  # exactly at capacity
        ((J("J1", 50, 1, 0, 1, False),), False),  # over capacity alone
    ],
)
def test_joint_feasibility_hand_cases(jobs, expected):
    assert g.jointly_feasible(jobs, 60, 20) is expected


def test_rejection_reasons():
    scores = (100, 300, 200, 200, 100, 300) + (200,) * 24
    flat = (200,) * 30
    feasible_flex = (J("J1", 10, 1, 0, 3, True), J("J2", 10, 1, 0, 1, False))
    assert g.rejection_reason(g.Proposal(feasible_flex, scores), "normal_feasible") is None
    assert (
        g.rejection_reason(g.Proposal(feasible_flex, flat), "normal_feasible") == "constant_profile"
    )
    assert (
        g.rejection_reason(g.Proposal(feasible_flex, flat), "missing_forecast")
        == "constant_profile"
    )
    rigid = (J("J1", 10, 1, 0, 3, False), J("J2", 10, 1, 0, 1, False))
    assert g.rejection_reason(g.Proposal(rigid, scores), "normal_feasible") == "no_flexible_job"
    clash = g.CONFLICT_PAIR + (J("J3", 10, 1, 0, 3, True),)
    assert g.rejection_reason(g.Proposal(clash, scores), "normal_feasible") == "jointly_infeasible"
    assert g.rejection_reason(g.Proposal(clash, flat), "overloaded_impossible") is None


def test_attempt_limit_is_an_explicit_failure():
    with pytest.raises(RuntimeError, match="within 3 attempts"):
        g._generate("development", set(), set(), per_stratum=40, max_attempts=3)


def test_duplicates_authored_and_excluded_cases_are_rejected_and_redrawn():
    accepted, _ = g._generate("development", set(), set(), per_stratum=2)
    first = accepted[0].full_sha256
    again, report = g._generate("development", {first}, set(), per_stratum=2)
    assert first not in {c.full_sha256 for c in again}
    assert report["normal_feasible"]["rejected"]["authored_overlap"] == 1
    again, report = g._generate("development", set(), {first}, per_stratum=2)
    assert report["normal_feasible"]["rejected"]["development_overlap"] == 1


def test_development_set_report_and_diversity(development):
    report = development[0]["metadata"]["report"]
    for stratum in g.STRATA:
        assert report[stratum]["accepted"] == 40
        assert report[stratum]["distinct_full_case_hashes"] == 40
        assert 1 <= report[stratum]["distinct_workload_hashes"] <= 40
        rejected = sum(report[stratum]["rejected"].values())
        assert report[stratum]["attempts"] == 40 + rejected


# --- Identity and the independent checker --------------------------------------------------


def test_identity_hashes_match_the_rule03_convention(development):
    case_set, accounting = development
    for raw, private in zip(case_set["cases"], accounting["cases"]):
        parsed = rc._case_from_dict(raw)
        assert private["full_case_sha256"] == rc.v.canonical_sha256(rc.case_identity(parsed))
        assert private["workload_sha256"] == rc.v.canonical_sha256(rc.workload_identity(parsed))


def test_authored_identities_match_the_rule03_checker():
    full, _ = rc.authored_identities(SPEC)
    assert g.authored_full_identities(SPEC) == full


def test_development_set_passes_the_independent_case_checker(development):
    report = rc.check_case_sets(
        [development[0]],
        spec=SPEC,
        expected_per_stratum={development[0]["set_id"]: 40},
    )
    assert report["overall"] == "PASS"
    assert all(o["full_case_overlap"] == 0 for o in report["overlap"])


# --- Isolation -----------------------------------------------------------------------------


def test_missing_forecast_weights_live_only_in_the_accounting_file(development):
    case_set, accounting = development
    private = {c["case_id"]: c for c in accounting["cases"]}
    for case in case_set["cases"]:
        hidden = case["stratum"] == "missing_forecast"
        assert (case["scores"] is None) is hidden
        assert private[case["case_id"]]["weights_visible_to_policy"] is (not hidden)
        assert len(private[case["case_id"]]["weights"]) == 30
        if not hidden:
            assert private[case["case_id"]]["weights"] == case["scores"]
    visible_text = g.dumps(case_set)
    assert g.ACCOUNTING_RECORD_KIND not in visible_text
    assert '"weights"' not in visible_text


def test_accounting_file_is_bound_to_its_case_set(development):
    case_set, accounting = development
    assert accounting["case_set_sha256"] == g.canonical_sha256(case_set)
    assert accounting["set_id"] == case_set["set_id"]


def test_metadata_records_provenance(development):
    meta = development[0]["metadata"]
    assert meta["seed"] == 2026111901 and meta["seed_domain"] == "development"
    assert meta["spec_sha256"] == g.SUPPORTED_SPEC_SHA256
    assert meta["generator_source_sha256"] == g.source_sha256()
    assert meta["authorization"] is None


# --- Guards --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "authorization",
    [None, "", "approved", "https://github.com/someone/else/issues/1#issuecomment-2"],
)
def test_final_domain_refuses_without_a_recorded_authorization(authorization):
    with pytest.raises(PermissionError):
        g.generate("final", authorization=authorization, spec=SPEC)


def test_authorization_is_rejected_for_development():
    with pytest.raises(ValueError):
        g.generate(
            "development",
            authorization="https://github.com/ReymoT/data-center-agentic/issues/242#issuecomment-1",
            spec=SPEC,
        )


def test_unknown_domain_and_changed_specification_are_refused():
    with pytest.raises(ValueError):
        g.generate("held_out", spec=SPEC)
    changed = copy.deepcopy(SPEC)
    changed["status"] = "edited"
    with pytest.raises(ValueError, match="specification"):
        g.generate("development", spec=changed)


# --- CLI -----------------------------------------------------------------------------------


def _run(*args):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT
    )


def test_cli_writes_both_files_and_never_overwrites(tmp_path, development):
    cases, accounting = tmp_path / "dev.json", tmp_path / "dev.accounting.json"
    done = _run(
        "--domain", "development", "--out-cases", str(cases), "--out-accounting", str(accounting)
    )
    assert done.returncode == 0, done.stderr
    assert cases.read_text("utf-8") == g.dumps(development[0])
    assert accounting.read_text("utf-8") == g.dumps(development[1])
    again = _run(
        "--domain",
        "development",
        "--out-cases",
        str(cases),
        "--out-accounting",
        str(tmp_path / "x.json"),
    )
    assert again.returncode != 0 and "already exists" in again.stderr


def test_cli_refuses_final_without_authorization(tmp_path):
    done = _run(
        "--domain",
        "final",
        "--out-cases",
        str(tmp_path / "f.json"),
        "--out-accounting",
        str(tmp_path / "fa.json"),
    )
    assert done.returncode == 1 and "refused" in done.stderr
    assert not (tmp_path / "f.json").exists() and not (tmp_path / "fa.json").exists()
