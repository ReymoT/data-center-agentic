"""E05 agreement tests on synthetic complete ratings of the development cases.

Kappa values are worked out by hand: kappa = (po - pe) / (1 - pe), with pe the sum over
labels of the two raters' label proportions multiplied together.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from dc_sustainability.evaluation import agreement as g
from dc_sustainability.evaluation import review

ROOT = Path(__file__).resolve().parents[2]
CASES = review.load_cases(
    json.loads((ROOT / "docs/e04/development_cases.json").read_text(encoding="utf-8"))
)
BY_ID = {c.case_id: c for c in CASES}


def ratings(rater="A"):
    """A complete, valid ratings file: every claim supported, every part rated 1."""
    outputs = []
    for case in CASES:
        for key in review.OUTPUT_KEYS:
            entry = review.blank_annotation(case, key)
            for a in entry["assertions"]:
                a.update(label="supported", supporting_cited_ids=a["cited_ids"])
                a["restated_in_summary"] = False
            if entry["completeness"] is not None:
                score = 1 if entry["explanation_present"] else 0
                entry["completeness"] = dict.fromkeys(review.COMPLETENESS, score)
            outputs.append(entry)
    return {"rubric_version": review.RUBRIC_VERSION, "rater": rater, "outputs": outputs}


def entry(data, case_id, key):
    return next(o for o in data["outputs"] if (o["case_id"], o["output"]) == (case_id, key))


def load(data):
    return g.load_original(json.dumps(data).encode("utf-8"), CASES)


def extracted(aid, text, label, source="summary"):
    return {
        "assertion_id": aid,
        "source": source,
        "text": text,
        "label": label,
        "cited_ids": [],
        "supporting_cited_ids": [],
    }


# ----------------------------------------------------------------- kappa by hand
def test_kappa_hand_example():
    # po = 4/5 = 0.8; A: S 3, C 1, U 1; B: S 2, C 1, U 2.
    # pe = 0.6*0.4 + 0.2*0.2 + 0.2*0.4 = 0.36; kappa = 0.44 / 0.64 = 0.6875.
    pairs = [("S", "S"), ("S", "S"), ("C", "C"), ("S", "U"), ("U", "U")]
    assert g.cohens_kappa(pairs) == pytest.approx(0.6875)


def test_kappa_undefined_when_there_is_nothing_to_compare():
    assert g.cohens_kappa([]) is None
    assert g.cohens_kappa([("S", "S")] * 5) is None  # chance agreement is 1


# ----------------------------------------------------------------- loading originals
def test_original_is_identified_by_its_exact_bytes():
    raw = json.dumps(ratings()).encode("utf-8")
    original = g.load_original(raw, CASES)
    assert original.sha256 == hashlib.sha256(raw).hexdigest()
    assert len(original.entries) == 22


def test_hash_is_the_committed_lf_hash_on_a_crlf_checkout():
    raw = (json.dumps(ratings(), indent=1) + "\n").encode("utf-8")
    crlf = raw.replace(b"\n", b"\r\n")  # what a Windows checkout with autocrlf holds
    assert g.load_original(crlf, CASES).sha256 == hashlib.sha256(raw).hexdigest()


def test_incomplete_or_partial_originals_are_refused():
    partial = ratings()
    partial["outputs"].pop()
    with pytest.raises(ValueError, match="missing outputs"):
        load(partial)
    unlabelled = ratings()
    entry(unlabelled, "DEV01", "X")["assertions"][0]["label"] = None
    with pytest.raises(ValueError, match="label"):
        load(unlabelled)


# ----------------------------------------------------------------- comparison
def test_identical_ratings_agree_fully_with_undefined_kappa():
    result = g.compare(load(ratings("A")), load(ratings("B")))
    assert result.not_applicable == 2  # both DEV11 no-ops
    assert (result.labels.n, result.labels.agreed, result.labels.percent) == (32, 32, 100.0)
    assert result.labels.kappa is None  # every label "supported": chance agreement is 1
    assert result.extraction.agreement is None  # no summary/limitation assertions at all


def test_one_label_disagreement_among_32_claims():
    # 31 pairs (S, S) and one (C, S): po = 31/32, pe = 31/32 * 1, so kappa = 0.
    a = ratings("A")
    entry(a, "DEV01", "X")["assertions"][0]["label"] = "contradicted"
    result = g.compare(load(a), load(ratings("B")))
    assert (result.labels.n, result.labels.agreed) == (32, 31)
    assert result.labels.percent == pytest.approx(100 * 31 / 32)
    assert result.labels.kappa == pytest.approx(0.0)
    assert result.claim_labels == result.labels


def test_extraction_agreement_uses_explicit_matches_only():
    a, b = ratings("A"), ratings("B")
    entry(a, "DEV02", "X")["assertions"] += [
        extracted("S1", "Defer J2.", "supported"),
        extracted("S2", "Slot 3 is cheapest.", "supported"),
    ]
    entry(b, "DEV02", "X")["assertions"] += [
        extracted("S1", "Slot 3 has the lowest forecast.", "contradicted")
    ]
    unmatched = g.compare(load(a), load(b))
    assert (unmatched.extraction.both, unmatched.extraction.only_a) == (0, 2)
    assert unmatched.extraction.only_b == 1

    result = g.compare(load(a), load(b), {("DEV02", "X"): [("S2", "S1")]})
    e = result.extraction
    assert (e.both, e.only_a, e.only_b, e.agreement) == (1, 1, 0, 0.5)
    assert (result.labels.n, result.labels.agreed) == (33, 32)  # 32 claims + 1 match
    assert (result.claim_labels.n, result.claim_labels.agreed) == (32, 32)


def test_matches_must_name_existing_extracted_assertions_once():
    a, b = ratings("A"), ratings("B")
    entry(a, "DEV02", "X")["assertions"].append(extracted("S1", "x", "supported"))
    entry(b, "DEV02", "X")["assertions"].append(extracted("S1", "x", "supported"))
    with pytest.raises(ValueError, match="exist"):
        g.compare(load(a), load(b), {("DEV02", "X"): [("C1", "S1")]})
    with pytest.raises(ValueError, match="more than once"):
        g.compare(load(a), load(b), {("DEV02", "X"): [("S1", "S1"), ("S1", "S1")]})


def test_completeness_agreement_per_part():
    b = ratings("B")
    entry(b, "DEV01", "X")["completeness"]["limitations"] = 0
    result = g.compare(load(ratings("A")), load(b))
    part = result.completeness["limitations"]
    assert (part.n, part.agreed) == (20, 19)  # 22 outputs minus the two no-ops
    assert result.completeness["decision"].agreed == 20


def test_summary_report_keeps_undefined_values_as_none():
    report = g.summary(g.compare(load(ratings("A")), load(ratings("B"))))
    assert report["labels_all_matched"]["kappa"] is None
    assert report["extraction"]["agreement"] is None
    assert report["originals"]["a"]["rater"] == "A"
    json.dumps(report)  # JSON-ready


# ----------------------------------------------------------------- adjudication
def disagreeing():
    a, b = ratings("A"), ratings("B")
    entry(a, "DEV01", "X")["assertions"][0]["label"] = "contradicted"
    entry(b, "DEV02", "X")["assertions"].append(extracted("S1", "Defer J2.", "supported"))
    entry(b, "DEV01", "Y")["completeness"]["reason"] = 0
    return g.compare(load(a), load(b))


def test_adjudication_lists_every_disagreement_undecided():
    record = g.adjudication_record(disagreeing())
    kinds = [(i["kind"], i["case_id"], i["output"]) for i in record["items"]]
    assert kinds == [
        ("label", "DEV01", "X"),
        ("extraction", "DEV02", "X"),
        ("completeness", "DEV01", "Y"),
    ]
    assert all(i["decision"] is None for i in record["items"])
    assert record["adjudicators"] == []


def decided(record):
    record = copy.deepcopy(record)
    record["adjudicators"] = ["Nisha", "MattyAnd"]
    label, extraction, completeness = record["items"]
    label.update(decision="supported", rationale="Within tolerance on recheck.")
    extraction.update(decision="keep", decided_label="supported", rationale="Plan fact.")
    completeness.update(decision=1, rationale="The summary gives a reason.")
    return record


def test_complete_joint_adjudication_is_accepted():
    comparison = disagreeing()
    g.validate_adjudication(decided(g.adjudication_record(comparison)), comparison)


@pytest.mark.parametrize(
    "change,message",
    [
        (lambda r: r["items"][0].update(decision=None), "label"),
        (lambda r: r["items"][1].update(decision="keep", decided_label=None), "keep"),
        (lambda r: r["items"][2].update(rationale=""), "rationale"),
        (lambda r: r.update(adjudicators=["Nisha"]), "two adjudicators"),
        (lambda r: r["originals"]["a"].update(sha256="0" * 64), "different originals"),
        (lambda r: r["items"].pop(), "differ"),
        (lambda r: r["items"][0].update(a="supported"), "differ"),
    ],
)
def test_incomplete_or_altered_adjudication_is_refused(change, message):
    comparison = disagreeing()
    record = decided(g.adjudication_record(comparison))
    change(record)
    with pytest.raises(ValueError, match=message):
        g.validate_adjudication(record, comparison)


def test_dropping_a_one_sided_assertion_needs_no_label():
    comparison = disagreeing()
    record = decided(g.adjudication_record(comparison))
    record["items"][1].update(decision="drop", decided_label=None)
    g.validate_adjudication(record, comparison)
