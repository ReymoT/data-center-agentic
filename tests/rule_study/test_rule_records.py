"""Study-local records: strict validation, exact identity, stable bytes and honest nulls."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from dc_sustainability.rule_study import cases as c
from dc_sustainability.rule_study import records as r
from tests.rule_study.helpers import REPO_ROOT, run


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    case_run, _, _ = run(tmp_path_factory.mktemp("records"), c.CASE_A)
    return case_run


def decision_dict(saved, index=0):
    return json.loads(saved.outcomes[index].record.to_json())


def result_dict(saved):
    return json.loads(saved.result.to_json())


# --------------------------------------------------------------------------- serialization
def test_study_json_is_sorted_compact_and_ends_with_one_lf():
    text = r.study_json({"b": 1, "a": [1, 2], "z": "é"})
    assert text == '{"a":[1,2],"b":1,"z":"é"}\n'
    assert not text.endswith("\n\n")


def test_study_json_rejects_non_finite_numbers():
    with pytest.raises(ValueError):
        r.study_json({"x": float("nan")})


def test_hash_is_sha256_of_the_exact_bytes():
    import hashlib

    text = r.study_json({"a": 1})
    assert r.study_sha256(text) == hashlib.sha256(b'{"a":1}\n').hexdigest()


def test_record_round_trips_with_identical_bytes(saved):
    record = saved.outcomes[0].record
    again = r.RuleStudyDecision.from_json(record.to_json())
    assert again == record and again.to_json() == record.to_json()
    result = r.RuleStudyResult.from_json(saved.result.to_json())
    assert result.to_json() == saved.result.to_json()


# --------------------------------------------------------------------------- strictness
def test_unknown_fields_are_rejected(saved):
    data = decision_dict(saved)
    data["surprise"] = 1
    with pytest.raises(ValidationError):
        r.RuleStudyDecision.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field,value",
    [
        ("record_kind", "decision_record_v1"),
        ("adapter_version", "proposal-2"),
        ("study_id", "rule-study-other"),
        ("policy_id", "greedy_c"),
    ],
)
def test_exact_identity_values_are_required(saved, field, value):
    data = decision_dict(saved)
    data[field] = value
    with pytest.raises(ValidationError):
        r.RuleStudyDecision.model_validate_json(json.dumps(data))


def test_legacy_f02_identity_fields_cannot_be_spoofed(saved):
    for extra in ({"system": "greedy_a"}, {"record_type": "decision"}):
        data = decision_dict(saved)
        data.update(extra)
        with pytest.raises(ValidationError):
            r.RuleStudyDecision.model_validate_json(json.dumps(data))


def test_model_call_count_must_be_exactly_zero(saved):
    data = decision_dict(saved)
    for bad in (1, True, "0", None, 0.0):
        data["model_call_count"] = bad
        with pytest.raises(ValidationError):
            r.RuleStudyDecision.model_validate_json(json.dumps(data))
    result = result_dict(saved)
    result["model_call_count"] = 1
    with pytest.raises(ValidationError):
        r.RuleStudyResult.model_validate_json(json.dumps(result))


def test_decision_index_must_equal_the_state_before_slot(saved):
    data = decision_dict(saved)
    data["decision_index"] = 3
    with pytest.raises(ValidationError, match="state-before slot"):
        r.RuleStudyDecision.model_validate_json(json.dumps(data))


def test_selected_stage_must_reference_a_passing_check(saved):
    data = decision_dict(saved)
    data["selected_stage_id"] = "STG-99"
    with pytest.raises(ValidationError, match="does not reference"):
        r.RuleStudyDecision.model_validate_json(json.dumps(data))
    data = decision_dict(saved)
    data["proposal_stages"][0]["check_result"]["status"] = "fail"
    with pytest.raises(ValidationError):
        r.RuleStudyDecision.model_validate_json(json.dumps(data))


def test_signed_excess_must_equal_total_minus_limit(saved):
    entry = next(
        e for e in saved.outcomes[0].record.proposal_stages[0].arithmetic if e.limit is not None
    )
    data = json.loads(json.dumps(entry.to_jsonable()))
    data["signed_excess"] = data["signed_excess"] + 1
    with pytest.raises(ValidationError, match="total - limit"):
        r.ArithmeticEntry.model_validate_json(json.dumps(data))


# --------------------------------------------------------------------------- bindings
def _real_bindings():
    return r.Bindings.model_validate(json.loads(decision_bindings_json()))


def decision_bindings_json():
    from tests.rule_study.helpers import bindings_for

    return bindings_for(c.CASE_A).to_json()


def test_bindings_have_no_null_and_reject_placeholders():
    data = json.loads(decision_bindings_json())
    assert all(isinstance(value, str) for value in data.values())
    for key in ("spec_sha256", "adapter_source_sha256", "generator_source_sha256"):
        for fake in ("0" * 64, "a" * 64, "f" * 64):
            with pytest.raises(ValidationError, match="placeholder"):
                r.Bindings.model_validate({**data, key: fake})
    with pytest.raises(ValidationError):
        r.Bindings.model_validate({**data, "code_commit": "0" * 40})
    for key in data:  # the merged reader refuses null, so this model must as well
        with pytest.raises(ValidationError):
            r.Bindings.model_validate({**data, key: None})
    with pytest.raises(ValidationError):
        r.Bindings.model_validate({**data, "code_commit": data["code_commit"][:12]})


def test_saved_records_carry_every_binding_as_a_real_value(saved):
    bindings = decision_dict(saved)["bindings"]
    assert set(bindings) == set(r.Bindings.model_fields)
    assert all(value is not None for value in bindings.values())
    assert bindings["case_sha256"] == c.CASE_A.case_sha256()
    assert result_dict(saved)["bindings"] == bindings


# --------------------------------------------------------------------------- stages / results
def test_stage_origins_distinguish_fallback_from_a_direct_policy():
    assert {"greedy_a", "greedy_a_fallback", "fault_injection"} <= set(r.StageOrigin.__args__)
    assert r.StageOrigin.__args__.count("greedy_a_fallback") == 1


def test_complete_result_must_bind_all_thirty_decisions(saved):
    data = result_dict(saved)
    data["decision_sha256s"] = data["decision_sha256s"][:10]
    with pytest.raises(ValidationError, match="all 30"):
        r.RuleStudyResult.model_validate_json(json.dumps(data))


def test_failed_result_cannot_carry_accounting(saved):
    data = result_dict(saved)
    data["status"] = "failed"
    with pytest.raises(ValidationError, match="failed result"):
        r.RuleStudyResult.model_validate_json(json.dumps(data))


def test_completed_and_unfinished_are_disjoint_and_missed_is_unfinished(saved):
    data = result_dict(saved)
    data["unfinished_job_ids"] = ["J1"]
    with pytest.raises(ValidationError, match="both completed and unfinished"):
        r.RuleStudyResult.model_validate_json(json.dumps(data))
    data = result_dict(saved)
    data["missed_job_ids"] = ["J1"]
    with pytest.raises(ValidationError, match="missed job is unfinished"):
        r.RuleStudyResult.model_validate_json(json.dumps(data))


def test_result_rejects_fields_outside_the_merged_reader_contract(saved):
    for extra in ("decisions", "model_call_count", "unscheduled_job_ids"):
        data = result_dict(saved)
        data[extra] = []
        with pytest.raises(ValidationError):
            r.RuleStudyResult.model_validate_json(json.dumps(data))


def test_execution_state_after_is_required_unless_indeterminate(saved):
    data = decision_dict(saved)["execution"]
    data["state_after"] = None
    with pytest.raises(ValidationError, match="state_after is required"):
        r.Execution.model_validate_json(json.dumps(data))
    data.update(
        status="indeterminate", current_starts=[], transition_ref=None, transition_sha256=None
    )
    assert r.Execution.model_validate_json(json.dumps(data)).state_after is None


# --------------------------------------------------------------------------- example file
def test_illustrative_example_file_is_not_a_valid_study_record():
    example = Path(REPO_ROOT) / "docs" / "rule_study" / "adapter_record.example.json"
    text = example.read_text(encoding="utf-8")
    assert json.loads(text)["record_kind"] == "illustrative_example_not_executable"
    with pytest.raises(ValidationError):
        r.RuleStudyDecision.model_validate_json(text)
    with pytest.raises(ValidationError):
        r.RuleStudyResult.model_validate_json(text)


def test_case_hash_is_the_canonical_hash_of_the_case_json_object():
    from dc_sustainability.evaluation import rule_study_verifier as v

    for case in c.AUTHORED_CASES.values():
        assert case.case_sha256() == v.canonical_sha256(case.case_json())
    assert len({case.case_sha256() for case in c.AUTHORED_CASES.values()}) == 4
    assert c.CASE_B_FAULT.case_json()["fault_starts"] == ["J1", "J2"]
    assert "fault_starts" not in c.CASE_B.case_json()


def test_models_mirror_the_merged_readers_exact_field_sets():
    from dc_sustainability.evaluation import rule_study_trace as tr

    def fields(model):
        return set(model.model_fields)

    assert fields(r.RuleStudyDecision) == set(tr.DECISION_FIELDS)
    assert fields(r.Bindings) == set(tr.BINDING_FIELDS)
    assert fields(r.StateBefore) == set(tr.STATE_BEFORE_FIELDS)
    assert fields(r.ProposalStage) == set(tr.STAGE_FIELDS)
    assert fields(r.Execution) == set(tr.EXECUTION_FIELDS)
    assert fields(r.StateAfter) == set(tr.STATE_AFTER_FIELDS)
    assert fields(r.RuleStudyResult) == set(tr.RESULT_FIELDS)
    assert tr.DECISION_KIND == "rule_study_decision_v1" and tr.RESULT_KIND == "rule_study_result_v1"
    assert tr.STUDY_ID == r.STUDY_ID and set(tr.POLICY_IDS) == set(r.POLICY_IDS)
    assert set(tr.STAGE_ORIGINS) == set(r.StageOrigin.__args__)


def test_authored_cases_equal_the_independent_verifiers_reading_of_the_specification():
    from dc_sustainability.evaluation import rule_study_trace as tr
    from dc_sustainability.evaluation import rule_study_verifier as v

    spec = json.loads((REPO_ROOT / "docs/rule_study/specification.json").read_text("utf-8"))
    authored = {case.case_id: case for case in v.authored_cases(spec)}
    assert set(authored) == set(c.AUTHORED_CASES) == {"A", "B", "B-fault", "B-progress"}
    for case_id, mine in c.AUTHORED_CASES.items():
        assert tr.case_from_dict(mine.case_json()) == authored[case_id]
