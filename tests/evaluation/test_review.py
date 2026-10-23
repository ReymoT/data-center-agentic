"""E04 review material: committed cases, blinding, annotation structure and metrics.

Scoring tests use a small case built here, not the development cases, so this file
does not reveal expected labels for the material raters will annotate.
"""

import copy
import json
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import review as rv
from scripts import build_e04_cases as build
from tests.contracts import fixtures as f

E04 = Path(build.__file__).resolve().parents[1] / "docs" / "e04"


def committed(name):
    return (E04 / name).read_text(encoding="utf-8")


def cases():
    return rv.load_cases(json.loads(committed("development_cases.json")))


# ----------------------------------------------------------------- committed material
def test_committed_files_match_the_generator():
    for name, text in build.build().items():
        assert committed(name) == text, f"{name} is stale; run scripts/build_e04_cases.py"


def test_cases_cover_the_q10_categories_with_at_least_ten_pairs():
    categories = {category for _, category, *_ in build.CASES}
    assert build.REQUIRED_CATEGORIES <= categories
    loaded = cases()
    assert len(loaded) == len(build.CASES)
    reviewable = [c for c in loaded if not all(c.not_applicable(k) for k in rv.OUTPUT_KEYS)]
    assert len(reviewable) >= 10


def test_every_output_is_bound_to_its_decision_and_f02_valid():
    for case in cases():
        assert case.state.constraint_snapshot_id == case.snapshot.snapshot_id
        for out in case.outputs.values():
            if out.plan is not None:
                assert (out.plan.slot, out.plan.state_version) == (
                    case.state.current_slot,
                    case.state.state_version,
                )
            s.PolicyOutput(  # the blinded output is a full F02 output once a system is added
                system="agent",
                output_status=out.output_status,
                plan=out.plan,
                explanation=out.explanation,
                raw_response=out.raw_response,
            )


def test_rater_material_does_not_reveal_systems_or_categories():
    # System identities and the distinctive category labels. "missing_evidence" is also an
    # F02 reason value and plain words like "abstention" are F02 field names, so neither
    # is a marker.
    words = ("agent", "plain_llm", "plain llm", "category")
    words += tuple(c for _, c, *_ in build.CASES if "_" in c and c != "missing_evidence")
    for name in ("RATER_PACKET.md", "development_cases.json", "annotation_template.json"):
        text = committed(name).lower()
        for word in words:
            assert word not in text, (name, word)


def test_template_lists_every_claim_and_leaves_every_judgement_empty():
    template = json.loads(committed("annotation_template.json"))
    by_key = {(c.case_id, k): c for c in cases() for k in rv.OUTPUT_KEYS}
    assert len(template["outputs"]) == len(by_key)
    for entry in template["outputs"]:
        case = by_key[(entry["case_id"], entry["output"])]
        rv.validate_annotation(case, entry, complete=False)
        assert all(a["label"] is None for a in entry["assertions"])
        if entry["not_applicable"]:
            rv.validate_annotation(case, entry, complete=True)  # nothing to rate on a no-op
        else:
            with pytest.raises(ValueError):
                rv.validate_annotation(case, entry, complete=True)


# ----------------------------------------------------------------- a small scoring case
def small_case(explanation=True, status="ok"):
    state = f.visible_state()
    plan = f.plan() if status == "ok" else None
    exp = None
    if explanation:
        exp = s.Explanation(
            source="llm",
            summary="J1 starts now. J2 starts at slot 2.",
            claims=(
                s.Claim(claim_id="C1", text="J1 arrived at slot 0.", evidence_ids=("FACT-JOB-J1",)),
                s.Claim(
                    claim_id="C2",
                    text="J2 is 30 kW.",
                    evidence_ids=("FACT-JOB-J2", "FACT-JOB-J1"),
                    value=30.0,
                    unit="kW",
                ),
            ),
        )
    data = {
        "rubric_version": rv.RUBRIC_VERSION,
        "cases": [
            {
                "case_id": "T1",
                "snapshot": f.snapshot().to_jsonable(),
                "state": state.to_jsonable(),
                "outputs": {
                    k: {
                        "output_status": status,
                        "plan": plan.to_jsonable() if plan else None,
                        "explanation": exp.model_dump(mode="json") if exp else None,
                        "raw_response": None if status == "ok" else "{",
                    }
                    for k in rv.OUTPUT_KEYS
                },
            }
        ],
    }
    return rv.load_cases(data)[0]


def filled(case):
    entry = rv.blank_annotation(case, "X")
    c1, c2 = entry["assertions"]
    c1.update(label="supported", supporting_cited_ids=["FACT-JOB-J1"], restated_in_summary=False)
    c2.update(label="supported", supporting_cited_ids=["FACT-JOB-J2"], restated_in_summary=False)
    entry["assertions"] += [
        {
            "assertion_id": "S1",
            "source": "summary",
            "text": "J1 starts now.",
            "label": "supported",
            "cited_ids": [],
            "supporting_cited_ids": [],
        },
        {
            "assertion_id": "S2",
            "source": "summary",
            "text": "J2 starts at slot 2.",
            "label": "contradicted",
            "cited_ids": [],
            "supporting_cited_ids": [],
        },
    ]
    entry["completeness"] = {"decision": 1, "reason": 0, "evidence": 1, "limitations": 0}
    return entry


def test_hand_scored_output():
    # 4 assertions, 3 supported; C1 and C2 have supporting citations; 2 of 3 cited
    # pairs support; 2 of 4 completeness parts. (S2 is labelled contradicted only to
    # exercise the arithmetic; the label itself is a rater's choice.)
    score = rv.score_annotation(small_case(), filled(small_case()))
    assert (score.checkable, score.supported) == (4, 3)
    assert score.faithfulness == 0.75
    assert score.coverage == 0.5
    assert score.precision == pytest.approx(2 / 3)
    assert score.completeness == 0.5


def test_failed_output_has_zero_coverage_and_undefined_faithfulness():
    case = small_case(explanation=False, status="malformed")
    entry = rv.blank_annotation(case, "X")
    assert not entry["not_applicable"] and entry["assertions"] == []
    entry["completeness"] = dict.fromkeys(rv.COMPLETENESS, 0)
    score = rv.score_annotation(case, entry)
    assert (score.faithfulness, score.precision) == (None, None)
    assert (score.coverage, score.completeness) == (0.0, 0.0)
    entry["completeness"]["reason"] = 1
    with pytest.raises(ValueError, match="0 completeness"):
        rv.validate_annotation(case, entry, complete=True)


def test_empty_queue_noop_is_not_applicable():
    state = f.visible_state(waiting_job_ids=())
    noop = s.Plan(episode_id=f.EPISODE_ID, slot=0, state_version=0, status="proposed")
    case = rv.ReviewCase(
        "T2",
        f.snapshot(),
        state,
        {k: rv.BlindOutput("ok", noop, None, None) for k in rv.OUTPUT_KEYS},
    )
    entry = rv.blank_annotation(case, "Y")
    assert entry["not_applicable"] and entry["completeness"] is None
    assert rv.score_annotation(case, entry) is None
    entry["completeness"] = dict.fromkeys(rv.COMPLETENESS, 0)
    with pytest.raises(ValueError, match="no-op"):
        rv.validate_annotation(case, entry, complete=True)


@pytest.mark.parametrize("waiting, raw", [(("J1",), None), ((), "Unparsed text")])
def test_empty_plan_is_not_enough_to_exempt_an_output(waiting, raw):
    state = f.visible_state(waiting_job_ids=waiting)
    noop = s.Plan(episode_id=f.EPISODE_ID, slot=0, state_version=0, status="proposed")
    case = rv.ReviewCase(
        "T3",
        f.snapshot(),
        state,
        {k: rv.BlindOutput("ok", noop, None, raw) for k in rv.OUTPUT_KEYS},
    )
    entry = rv.blank_annotation(case, "X")
    assert entry["not_applicable"] is False
    entry["completeness"] = dict.fromkeys(rv.COMPLETENESS, 0)
    score = rv.score_annotation(case, entry)
    assert score is not None
    assert (score.coverage, score.completeness) == (0.0, 0.0)


def test_repeated_supporting_citation_cannot_inflate_precision():
    case = small_case()
    entry = filled(case)
    entry["assertions"][0]["supporting_cited_ids"] = ["FACT-JOB-J1"] * 5
    with pytest.raises(ValueError, match="unique"):
        rv.score_annotation(case, entry)


@pytest.mark.parametrize("restated", [0, 1])
def test_restatement_requires_a_json_boolean(restated):
    entry = filled(small_case())
    entry["assertions"][0]["restated_in_summary"] = restated
    with pytest.raises(ValueError, match="true or false"):
        rv.validate_annotation(small_case(), entry, complete=True)


@pytest.mark.parametrize("field,value", [("background_kw", 41.0), ("pue", 1.2)])
def test_case_rejects_a_site_that_disagrees_with_its_snapshot(field, value):
    data = json.loads(committed("development_cases.json"))
    data["cases"][0]["state"]["site"][field] = value
    with pytest.raises(ValueError, match="site"):
        rv.load_cases(data)


def test_case_rejects_a_visible_constraint_absent_from_its_snapshot():
    data = json.loads(committed("development_cases.json"))
    data["cases"][0]["state"]["constraint_ids"].append("CON-UNKNOWN")
    with pytest.raises(ValueError, match="constraint"):
        rv.load_cases(data)


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda e: e["assertions"].pop(0), "every Claim record"),
        (lambda e: e["assertions"].append(copy.deepcopy(e["assertions"][2])), "share one ID"),
        (lambda e: e["assertions"][2].update(assertion_id="X9"), "S1 or L1"),
        (lambda e: e["assertions"][2].update(cited_ids=["FACT-JOB-J1"]), "no citations"),
        (lambda e: e["assertions"][0].update(text="edited"), "Claim record"),
        (lambda e: e["assertions"][0].update(cited_ids=["FACT-JOB-J2"]), "evidence IDs"),
        (lambda e: e["assertions"][0].update(supporting_cited_ids=["CON-CAP-01"]), "among its"),
        (lambda e: e["assertions"][1].update(label="partly"), "label must be"),
        (lambda e: e["assertions"][1].update(restated_in_summary=None), "restated"),
        (lambda e: e["completeness"].pop("reason"), "completeness rates"),
        (lambda e: e["completeness"].update(reason=True), "0 or 1"),
        (lambda e: e.update(not_applicable=True), "not_applicable"),
        (lambda e: e.update(case_id="T9"), "another case"),
    ],
)
def test_annotation_rule_violations_are_refused(change, message):
    case = small_case()
    entry = filled(case)
    rv.validate_annotation(case, entry, complete=True)
    change(entry)
    with pytest.raises(ValueError, match=message):
        rv.validate_annotation(case, entry, complete=True)


def test_case_file_refuses_unbound_or_inconsistent_outputs():
    data = json.loads(committed("development_cases.json"))
    bad = copy.deepcopy(data)
    bad["cases"][0]["outputs"]["X"]["plan"]["slot"] = 3
    with pytest.raises(ValueError, match="different decision"):
        rv.load_cases(bad)
    bad = copy.deepcopy(data)
    bad["cases"][0]["outputs"]["X"]["output_status"] = "error"
    with pytest.raises(ValueError, match="exactly the 'ok'"):
        rv.load_cases(bad)
    bad = copy.deepcopy(data)
    bad["cases"][0]["outputs"]["Z"] = bad["cases"][0]["outputs"].pop("Y")
    with pytest.raises(ValueError, match="exactly X and Y"):
        rv.load_cases(bad)
    bad = copy.deepcopy(data)
    bad["rubric_version"] = "other"
    with pytest.raises(ValueError, match="rubric version"):
        rv.load_cases(bad)
