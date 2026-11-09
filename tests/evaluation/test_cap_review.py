"""Rule §11.9 cap hits, cut-off text and reporting; decisions are synthetic, not ratings."""

import copy
import json
from dataclasses import replace

import pytest

from dc_sustainability.evaluation import agreement as g
from dc_sustainability.evaluation import review
from tests.evaluation.test_calibration import CAL, cases
from tests.evaluation.test_text_review import example

# Synthetic summary and second limitation are exactly 78 characters.
# Overlong source text must not be confused with an exact cap hit.
LIMIT = 78
SUMMARY_TAIL = "The goal is to keep emissions as low as possible."
LIMITATION_TAIL = "would miss its deadline."


def cap_example():
    case, entry = example()
    tail = SUMMARY_TAIL
    prefix = "One. Two. "
    padding = LIMIT - len(prefix) - len(tail)
    summary = prefix + "x" * (padding - 2) + ". " + tail
    old = case.outputs["Y"]
    explanation = old.explanation.model_copy(update={"summary": summary})
    case = replace(case, outputs={**case.outputs, "Y": replace(old, explanation=explanation)})
    audit = review.blank_annotation(case, "Y", text_review=True)["text_review"]
    for source, units in audit.items():
        ids = [a["assertion_id"] for a in entry["assertions"] if a["source"] == source]
        for unit in units:
            unit.update(decision="not_checkable", assertion_ids=[])
        if ids:
            units[0].update(decision="extracted", assertion_ids=ids)
    entry["text_review"] = audit
    return case, entry


def cap_cases():
    changed = cap_example()[0]
    return tuple(changed if c.case_id == changed.case_id else c for c in cases())


def capped(limit=LIMIT, unfinished=(True, False)):
    """The example output with a cap review; the summary decided per ``unfinished``."""
    case, entry = cap_example()
    entry["cap_review"] = review.blank_annotation(case, "Y", cap_limit=limit)["cap_review"]
    for unit, flag in zip(entry["cap_review"]["units"], unfinished):
        tail = SUMMARY_TAIL if unit["field"] == "summary" else LIMITATION_TAIL
        unit.update(unfinished=flag, cut_off_text=tail if flag else None)
    return case, entry


def test_cap_hits_are_computed_with_the_limit_as_input():
    case = cap_cases()[0]
    output = case.outputs["Y"]
    assert review.cap_hits(output, LIMIT) == [("summary", "summary"), ("limitation", "1")]
    assert all(field == "claim" for field, _ in review.cap_hits(output, 30))
    assert review.cap_hits(output, 256) == []
    assert review.cap_hits(output, 1000) == []
    # The legacy 274-character summary is over the limit, not an exact cap hit.
    assert ("summary", "summary") not in review.cap_hits(cases()[0].outputs["Y"], LIMIT)
    for bad in (0, -1, 96.0, True, "96"):
        with pytest.raises(ValueError, match="positive integer"):
            review.cap_hits(output, bad)


def test_blank_cap_review_is_incomplete_until_decided():
    case, entry = cap_example()
    entry["cap_review"] = review.blank_annotation(case, "Y", cap_limit=LIMIT)["cap_review"]
    assert [u["unfinished"] for u in entry["cap_review"]["units"]] == [None, None]
    review.validate_annotation(case, entry, complete=False, cap_limit=LIMIT)
    with pytest.raises(ValueError, match="unfinished decision"):
        review.validate_annotation(case, entry, complete=True, cap_limit=LIMIT)


def test_decided_cap_review_passes_and_is_required_when_asked():
    case, entry = capped()
    review.validate_annotation(case, entry, complete=True, cap_limit=LIMIT)
    with pytest.raises(ValueError, match="96-character limit is required"):
        review.validate_annotation(case, entry, complete=True, cap_limit=96)
    del entry["cap_review"]
    with pytest.raises(ValueError, match="is required"):
        review.validate_annotation(case, entry, complete=True, cap_limit=LIMIT)
    review.validate_annotation(case, entry, complete=True)  # legacy path unchanged


@pytest.mark.parametrize(
    "fault, message",
    [
        ("dropped_unit", "exactly the computed cap hits"),
        ("added_unit", "exactly the computed cap hits"),
        ("reordered", "exactly the computed cap hits"),
        ("wrong_tail", "exact non-empty end"),
        ("blank_tail", "exact non-empty end"),
        ("finished_with_tail", "finished cap hit has no cut-off text"),
        ("string_flag", "true or false"),
        ("extra_key", "invalid cap_review unit"),
        ("extra_field", "exactly limit and units"),
    ],
)
def test_cap_review_refuses_altered_records(fault, message):
    case, entry = capped()
    units = entry["cap_review"]["units"]
    if fault == "dropped_unit":
        units.pop()
    elif fault == "added_unit":
        units.append({"field": "claim", "unit": "C1", "unfinished": False, "cut_off_text": None})
    elif fault == "reordered":
        units.reverse()
    elif fault == "wrong_tail":
        units[0]["cut_off_text"] = "as low as possible"
    elif fault == "blank_tail":
        units[0]["cut_off_text"] = " "
    elif fault == "finished_with_tail":
        units[1]["cut_off_text"] = LIMITATION_TAIL
    elif fault == "string_flag":
        units[0]["unfinished"] = "yes"
    elif fault == "extra_key":
        units[0]["note"] = ""
    else:
        entry["cap_review"]["note"] = ""
    with pytest.raises(ValueError, match=message):
        review.validate_annotation(case, entry, complete=True)


def test_cut_off_decision_only_at_the_end_of_an_unfinished_text():
    case, entry = capped()
    entry["text_review"]["summary"][-1].update(decision="cut_off", assertion_ids=[])
    review.validate_annotation(case, entry, complete=True, require_text_review=True)
    # Not for an earlier sentence, and never with assertion IDs.
    wrong_place = copy.deepcopy(entry)
    wrong_place["text_review"]["summary"][1].update(decision="cut_off", assertion_ids=[])
    with pytest.raises(ValueError, match="end of a text marked unfinished"):
        review.validate_annotation(case, wrong_place, complete=True)
    with_ids = copy.deepcopy(entry)
    with_ids["text_review"]["summary"][-1]["assertion_ids"] = ["S1"]
    with pytest.raises(ValueError, match="non-checkable text has none"):
        review.validate_annotation(case, with_ids, complete=True)
    # The limitation hit was judged finished, so it cannot be cut off.
    finished = copy.deepcopy(entry)
    finished["text_review"]["limitation"][1].update(decision="cut_off", assertion_ids=[])
    with pytest.raises(ValueError, match="end of a text marked unfinished"):
        review.validate_annotation(case, finished, complete=True)
    # Without any cap review the decision does not exist.
    del entry["cap_review"]
    with pytest.raises(ValueError, match="end of a text marked unfinished"):
        review.validate_annotation(case, entry, complete=True)


def test_unfinished_limitation_can_be_cut_off():
    case, entry = capped(unfinished=(False, True))
    entry["text_review"]["limitation"][1].update(decision="cut_off", assertion_ids=[])
    with pytest.raises(ValueError, match="end of a text marked unfinished"):
        review.validate_annotation(case, entry, complete=True, require_text_review=True)
    entry["cap_review"]["units"][1]["cut_off_text"] = entry["text_review"]["limitation"][1]["text"]
    review.validate_annotation(case, entry, complete=True, require_text_review=True)


def test_whole_claim_fragment_is_excluded_without_losing_other_assertions():
    case, entry = capped()
    old = case.outputs["Y"]
    claim = old.explanation.claims[0].model_copy(update={"text": "x" * LIMIT})
    explanation = old.explanation.model_copy(
        update={"claims": (claim, *old.explanation.claims[1:])}
    )
    case = replace(case, outputs={**case.outputs, "Y": replace(old, explanation=explanation)})
    kept = copy.deepcopy(entry)
    kept["cap_review"]["units"].append(
        {"field": "claim", "unit": claim.claim_id, "unfinished": False, "cut_off_text": None}
    )
    next(a for a in kept["assertions"] if a["assertion_id"] == claim.claim_id)["text"] = claim.text
    dropped = copy.deepcopy(kept)
    dropped["cap_review"]["units"][-1].update(unfinished=True, cut_off_text=claim.text)
    with pytest.raises(ValueError, match="whole-text cut-off"):
        review.validate_annotation(case, dropped, complete=True)
    dropped["assertions"] = [
        a for a in dropped["assertions"] if a["assertion_id"] != claim.claim_id
    ]
    review.validate_annotation(case, dropped, complete=True)
    score = review.score_annotation(case, dropped)
    assert score.checkable == len(dropped["assertions"])
    assert score.unfinished["claim"] == 1
    key = case.case_id, "Y"
    comparison = g.compare(
        g.Original("a", "a" * 64, {key: kept}),
        g.Original("b", "b" * 64, {key: dropped}),
    )
    assert comparison.claim_labels.n == 2
    assert any(o.assertion["assertion_id"] == claim.claim_id for o in comparison.one_sided)


def test_scores_carry_cap_counts_and_completeness_stays_as_written():
    case, entry = capped()
    plain = review.score_annotation(case, cap_example()[1])
    score = review.score_annotation(case, entry, cap_limit=LIMIT)
    assert plain.cap_hits is None and plain.unfinished is None
    assert score.cap_hits == {"summary": 1, "limitation": 1, "claim": 0}
    assert score.unfinished == {"summary": 1, "limitation": 0, "claim": 0}
    # Main measures are untouched by the cap review.
    assert (score.faithfulness, score.completeness) == (plain.faithfulness, plain.completeness)


def _score(checkable, supported, completeness, hits, unfinished):
    def field(n):
        return {"summary": n, "limitation": 0, "claim": 0}

    return review.OutputScore(
        checkable=checkable,
        supported=supported,
        faithfulness=supported / checkable if checkable else None,
        coverage=None,
        precision=None,
        completeness=completeness,
        cap_hits=field(hits),
        unfinished=field(unfinished),
    )


def test_cap_report_by_system_with_separate_sensitivity():
    report = review.cap_report(
        [
            ("Agent", _score(4, 2, 0.5, 1, 1)),
            ("Agent", _score(4, 4, 1.0, 1, 0)),
            ("Agent", _score(2, 2, 1.0, 0, 0)),
            ("Plain", _score(5, 5, 0.75, 0, 0)),
        ]
    )
    agent = report["Agent"]
    assert agent["outputs"] == 3 and agent["outputs_with_cap_hit"] == 2
    assert agent["cap_hits"] == {"summary": 2, "limitation": 0, "claim": 0}
    assert agent["unfinished"] == {"summary": 1, "limitation": 0, "claim": 0}
    assert agent["completeness_with_cap_hit"] == 0.75
    assert agent["completeness_without_cap_hit"] == 1.0
    assert agent["sensitivity"] == {
        "faithfulness_all": 0.8,
        "faithfulness_excluding_cut_off_fragments": 0.8,
        "outputs_retained": 3,
        "complete_assertions": 10,
        "cut_off_fragments_excluded": 1,
    }
    assert report["Plain"]["completeness_with_cap_hit"] is None
    with pytest.raises(ValueError, match="needs a cap review"):
        review.cap_report([("Plain", review.score_annotation(*example()))])


def _original(decisions, *, cap=True):
    """Matty's normalized calibration file with a synthetic cap review per output."""
    data = json.loads((CAL / "ratings/E04_Matty_normalized_2026-10-31.json").read_text())
    by_id = {c.case_id: c for c in cap_cases()}
    for entry in data["outputs"]:
        if not cap:
            continue
        units = review.blank_annotation(by_id[entry["case_id"]], entry["output"], cap_limit=LIMIT)
        entry["cap_review"] = units["cap_review"]
        for unit, flag in zip(entry["cap_review"]["units"], decisions):
            tail = SUMMARY_TAIL if unit["field"] == "summary" else LIMITATION_TAIL
            unit.update(unfinished=flag, cut_off_text=tail if flag else None)
    return g.load_original(json.dumps(data).encode(), cap_cases(), cap_limit=LIMIT if cap else None)


def test_raters_unfinished_agreement_and_adjudication():
    a, b = _original((True, False)), _original((True, True))
    same = {  # identical extractions, matched to themselves
        key: [(x["assertion_id"],) * 2 for x in e["assertions"] if x["source"] != "claim"]
        for key, e in a.entries.items()
    }
    comparison = g.compare(a, b, same)
    assert comparison.unfinished.n == 2 and comparison.unfinished.agreed == 1
    report = g.summary(comparison)
    assert report["cap_review"]["cap_hits"] == 2
    assert report["cap_review"]["unfinished"] == {"a": 1, "b": 2}
    assert report["cap_review"]["agreement"]["percent"] == 50.0
    items = [i for i in g.adjudication_record(comparison)["items"] if i["kind"] == "unfinished"]
    assert items == [
        {
            "kind": "unfinished",
            "case_id": items[0]["case_id"],
            "output": "Y",
            "field": "limitation",
            "unit": "1",
            "a": False,
            "b": True,
            "decision": None,
            "rationale": "",
        }
    ]
    # Same original apart from the cap decisions, so that is the only disagreement.
    record = g.adjudication_record(comparison)
    assert len(record["items"]) == 1
    record["adjudicators"] = ["Nisha", "Matty"]
    record["items"][0].update(decision="yes", rationale="joint")
    with pytest.raises(ValueError, match="true or false"):
        g.validate_adjudication(record, comparison)
    record["items"][0]["decision"] = True
    g.validate_adjudication(record, comparison)


def test_both_raters_must_record_cap_review_and_draft0_report_is_unchanged():
    with pytest.raises(ValueError, match="both raters record cap_review"):
        g.compare(_original((True, False)), _original((), cap=False), {})
    plain = g.summary(g.compare(_original((), cap=False), _original((), cap=False), {}))
    assert "cap_review" not in plain
