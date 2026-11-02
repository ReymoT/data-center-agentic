"""Prospective annotation coverage; examples are synthetic, not human judgments."""

import copy
import json

import pytest

from dc_sustainability.evaluation import review
from tests.evaluation.test_calibration import CAL, cases


def example():
    case = cases()[0]
    original = json.loads((CAL / "ratings/E04_Matty_normalized_2026-10-31.json").read_text())
    entry = next(e for e in original["outputs"] if e["output"] == "Y")
    entry["text_review"] = review.blank_annotation(case, "Y", text_review=True)["text_review"]
    # Test-only coarse linkage, not an extraction answer key.
    for source, units in entry["text_review"].items():
        ids = [a["assertion_id"] for a in entry["assertions"] if a["source"] == source]
        for unit in units:
            unit.update(decision="not_checkable", assertion_ids=[])
        if ids:
            units[0].update(decision="extracted", assertion_ids=ids)
    return case, entry


def test_complete_review_and_exact_text():
    case, entry = example()
    review.validate_annotation(case, entry, complete=True, require_text_review=True)
    changed = copy.deepcopy(entry)
    changed["text_review"]["summary"][0]["text"] = "altered"
    with pytest.raises(ValueError, match="exact source text"):
        review.validate_annotation(case, changed, complete=True)


@pytest.mark.parametrize(
    "fault", ["missing_field", "missing_unit", "undecided", "unknown_id", "unlinked"]
)
def test_complete_review_refuses_silent_omissions(fault):
    case, entry = example()
    if fault == "missing_field":
        del entry["text_review"]
    elif fault == "missing_unit":
        entry["text_review"]["summary"].pop()
    elif fault == "undecided":
        entry["text_review"]["summary"][-1]["decision"] = None
    elif fault == "unknown_id":
        entry["text_review"]["summary"][0]["assertion_ids"] = ["S999"]
    else:
        entry["text_review"]["summary"][0].update(decision="not_checkable", assertion_ids=[])
    with pytest.raises(ValueError):
        review.validate_annotation(case, entry, complete=True, require_text_review=True)


def test_blank_audit_is_incomplete_and_raw_is_covered():
    case = cases()[0]
    entry = review.blank_annotation(case, "X", text_review=True)
    assert entry["text_review"]["raw"]
    review.validate_annotation(case, entry, complete=False, require_text_review=True)
    with pytest.raises(ValueError):
        review.validate_annotation(case, entry, complete=True, require_text_review=True)
