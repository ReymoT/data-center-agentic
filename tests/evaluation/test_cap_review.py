"""Rule §11.9 cap hits, cut-off text and reporting; decisions are synthetic, not ratings."""

import copy
import json

import pytest

from dc_sustainability.evaluation import agreement as g
from dc_sustainability.evaluation import review
from tests.evaluation.test_calibration import CAL, cases
from tests.evaluation.test_text_review import example

# The example summary is 274 characters and its second limitation exactly 78, so a
# 78-character limit hits both; the claims (30-33 characters) stay below it.
LIMIT = 78
SUMMARY_TAIL = "The goal is to keep emissions as low as possible."
LIMITATION_TAIL = "would miss its deadline."


def capped(limit=LIMIT, unfinished=(True, False)):
    """The example output with a cap review; the summary decided per ``unfinished``."""
    case, entry = example()
    entry["cap_review"] = review.blank_annotation(case, "Y", cap_limit=limit)["cap_review"]
    for unit, flag in zip(entry["cap_review"]["units"], unfinished):
        tail = SUMMARY_TAIL if unit["field"] == "summary" else LIMITATION_TAIL
        unit.update(unfinished=flag, cut_off_text=tail if flag else None)
    return case, entry


def test_cap_hits_are_computed_with_the_limit_as_input():
    case = cases()[0]
    output = case.outputs["Y"]
    assert review.cap_hits(output, LIMIT) == [("summary", "summary"), ("limitation", "1")]
    assert review.cap_hits(output, 30) == [
        ("summary", "summary"),
        ("limitation", "0"),
        ("limitation", "1"),
        ("claim", "C1"),
        ("claim", "C2"),
        ("claim", "C3"),
    ]
    assert review.cap_hits(output, 256) == [("summary", "summary")]
    assert review.cap_hits(output, 1000) == []
    assert review.cap_hits(case.outputs["X"], 1) == []  # no explanation, nothing capped
    for bad in (0, -1, 96.0, True, "96"):
        with pytest.raises(ValueError, match="positive integer"):
            review.cap_hits(output, bad)


def test_blank_cap_review_is_incomplete_until_decided():
    case, entry = example()
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
    review.validate_annotation(case, entry, complete=True, require_text_review=True)


def test_scores_carry_cap_counts_and_completeness_stays_as_written():
    case, entry = capped()
    plain = review.score_annotation(case, example()[1])
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
        "faithfulness_nothing_unfinished": 1.0,
        "outputs_nothing_unfinished": 2,
    }
    assert report["Plain"]["completeness_with_cap_hit"] is None
    with pytest.raises(ValueError, match="needs a cap review"):
        review.cap_report([("Plain", review.score_annotation(*example()))])


def _original(decisions, *, cap=True):
    """Matty's normalized calibration file with a synthetic cap review per output."""
    data = json.loads((CAL / "ratings/E04_Matty_normalized_2026-10-31.json").read_text())
    by_id = {c.case_id: c for c in cases()}
    for entry in data["outputs"]:
        if not cap:
            continue
        units = review.blank_annotation(by_id[entry["case_id"]], entry["output"], cap_limit=LIMIT)
        entry["cap_review"] = units["cap_review"]
        for unit, flag in zip(entry["cap_review"]["units"], decisions):
            tail = SUMMARY_TAIL if unit["field"] == "summary" else LIMITATION_TAIL
            unit.update(unfinished=flag, cut_off_text=tail if flag else None)
    return g.load_original(json.dumps(data).encode(), cases(), cap_limit=LIMIT if cap else None)


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
