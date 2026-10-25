"""Offline regressions from real retained metadata; no model dispatch or retry."""

import json
from copy import deepcopy
from itertools import permutations
from pathlib import Path

import pytest

from scripts.inspect_ollama import compare_inventory, text_hash

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = json.loads((ROOT / "docs/evidence/a01-approved-preflight-2026-10-25.json").read_text())
MATCHES = EVIDENCE["offline_analysis"]["matches"]
ACCEPTED_TEXT = MATCHES["accepted_oct18"]["reconstructed_exact_hash_preimage"]
CURRENT_TEXT = MATCHES["preflight_oct25"]["reconstructed_exact_hash_preimage"]


def accepted():
    return json.loads((ROOT / "docs/evidence/ollama-qwen3-8b-2026-10-18.json").read_text())


def actual_display(text):
    result = accepted()
    result["parameters_sha256"] = text_hash(text)
    return result


def test_actual_stopped_preflight_has_equivalent_values_without_rewriting_either_hash():
    before = accepted()
    current = actual_display(CURRENT_TEXT)
    originals = deepcopy((before, current))
    assert text_hash(ACCEPTED_TEXT) == before["parameters_sha256"]
    assert current["parameters_sha256"] == EVIDENCE["observed_parameters_sha256"]
    assert before["parameters_sha256"] != current["parameters_sha256"]
    compare_inventory(before, current)
    compare_inventory(current, before)
    assert (before, current) == originals


def test_every_exact_key_group_order_passes_and_stop_list_order_is_preserved():
    # Build groups from independently retained reconstructed evidence, not from
    # the comparator's private allowlist or its formatting implementation.
    groups = {}
    for line in ACCEPTED_TEXT.splitlines():
        key = line.split()[0]
        groups.setdefault(key, []).append(line)
    assert len(groups) == 5 and len(groups["stop"]) == 2
    observed_hashes = set()
    for order in permutations(groups):
        text = "\n".join(line for key in order for line in groups[key])
        observed_hashes.add(text_hash(text))
        compare_inventory(accepted(), actual_display(text))
    assert len(observed_hashes) == 120


@pytest.mark.parametrize(
    "fault", ["value", "numeric_type", "stop_order", "duplicate", "missing", "extra", "format"]
)
def test_actual_parameter_changes_or_unsupported_text_still_block(fault):
    lines = ACCEPTED_TEXT.splitlines()
    if fault == "value":
        lines = [line.replace("0.95", "1") for line in lines]
    elif fault == "numeric_type":
        lines[-1] += ".0"
    elif fault == "stop_order":
        lines[0], lines[1] = lines[1], lines[0]
    elif fault == "duplicate":
        lines.append(lines[-1])
    elif fault == "missing":
        lines.pop()
    elif fault == "extra":
        lines.append("seed                           101")
    else:
        lines = [line.replace("  ", " ") for line in lines]
    with pytest.raises(ValueError, match="parameters_sha256"):
        compare_inventory(accepted(), actual_display("\n".join(lines)))


@pytest.mark.parametrize("field", ["runtime_version", "model_digest", "template_sha256"])
def test_order_exception_cannot_be_used_for_a_different_identity(field):
    before, current = accepted(), actual_display(CURRENT_TEXT)
    before[field] = current[field] = "unaccepted identity"
    with pytest.raises(ValueError, match="parameters_sha256"):
        compare_inventory(before, current)


def test_unknown_reference_hash_does_not_gain_the_display_order_exception():
    before = accepted()
    before["parameters_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="parameters_sha256"):
        compare_inventory(before, actual_display(CURRENT_TEXT))


@pytest.mark.parametrize("field", ["details", "license"])
def test_other_identity_checks_still_reject_drift_despite_an_allowed_parameter_order(field):
    current = actual_display(CURRENT_TEXT)
    current[field] = {"changed": True}
    with pytest.raises(ValueError, match=field):
        compare_inventory(accepted(), current)
