"""Q07 candidate scores and the public development card."""

import importlib.util
import json
import re
from pathlib import Path

import pytest

from dc_sustainability.data.carbon_source import SHA256 as CARBON_SHA256
from dc_sustainability.policies.learned import PUBLISHED_DEVELOPMENT_SHA256
from dc_sustainability.training.dataset import LabeledRow
from dc_sustainability.training.features import FEATURE_NAMES
from dc_sustainability.training.metrics import (
    CandidateScore,
    development_card_facts,
    development_card_json,
    render_development_card,
    score_candidates,
    score_fitted_rows,
    sum_candidate_scores,
)
from dc_sustainability.training.train import ARTIFACT_SCHEMA, ModelSpec, fit_model

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "docs" / "handoffs" / "P04_REAL_DEVELOPMENT_ARTIFACTS.md"
CARD = ROOT / "models" / "development_candidate_card.md"
CARD_JSON = ROOT / "models" / "development_card.json"
_METRIC_KEYS = frozenset({"precision", "recall", "f1", "f1_score"})


@pytest.mark.parametrize(
    ("labels", "probabilities", "precision", "recall", "f1"),
    [
        ([True, True, False, False], [0.8, 0.4, 0.6, 0.1], 0.5, 0.5, 0.5),
        ([True, False], [0.2, 0.1], None, 0.0, None),
        ([False, False], [0.9, 0.1], 0.0, None, None),
        ([False], [0.2], None, None, None),
        ([True, False, None], [0.9, 0.2, None], 1.0, 1.0, 1.0),
    ],
)
def test_q07_table(labels, probabilities, precision, recall, f1):
    score = score_candidates(labels, probabilities)
    assert score.precision == precision
    assert score.recall == recall
    assert score.f1 == f1
    assert score.basis == "caller_rows"


def test_threshold_tie_is_positive_and_just_below_is_negative():
    at_threshold = score_candidates([True], [0.5])
    below = score_candidates([True], [0.499999])
    assert at_threshold.true_positive == 1
    assert at_threshold.precision == 1.0
    assert below.false_negative == 1
    assert below.precision is None
    assert below.recall == 0.0
    assert below.f1 is None


def test_defined_zero_rates_have_zero_f1():
    score = score_candidates([True, False], [0.1, 0.9])
    assert score.precision == 0.0
    assert score.recall == 0.0
    assert score.f1 == 0.0


def test_excluded_row_stays_out_of_the_cells():
    score = score_candidates([True, False, None], [0.9, 0.2, None])
    assert score.true_positive == 1
    assert score.true_negative == 1
    assert score.false_positive == 0
    assert score.false_negative == 0
    assert score.excluded == 1
    assert score.scored == 2
    assert score.precision == 1.0


def test_empty_input_has_zero_cells_and_undefined_rates():
    score = score_candidates((), ())
    assert score == CandidateScore(0, 0, 0, 0, 0)
    assert score.scored == 0
    assert score.precision is None
    assert score.recall is None
    assert score.f1 is None


@pytest.mark.parametrize(
    ("labels", "probabilities"),
    [
        ([True], [0.2, 0.1]),
        ([True, None], [0.2, 0.1]),
        ([True], [None]),
        ([None], [0.2]),
        ([True], [1.1]),
        ([True], [-0.01]),
        ([True], [float("nan")]),
        ([True], [float("inf")]),
        ([1], [0.9]),
        ([True], [True]),
    ],
)
def test_score_candidates_rejects_bad_pairs(labels, probabilities):
    with pytest.raises(ValueError):
        score_candidates(labels, probabilities)


def test_negative_cell_is_rejected():
    with pytest.raises(ValueError):
        CandidateScore(0, 0, 0, 0, -1)


def test_sum_recomputes_rates_from_cells():
    none_predicted = score_candidates([True, False], [0.2, 0.1])
    with_gap = score_candidates([True, False, None], [0.9, 0.2, None])
    combined = sum_candidate_scores((none_predicted, with_gap))
    assert combined.basis == "caller_rows"
    assert combined.true_positive == 1
    assert combined.false_positive == 0
    assert combined.true_negative == 2
    assert combined.false_negative == 1
    assert combined.excluded == 1
    assert combined.precision == 1.0
    assert combined.recall == 0.5
    assert combined.f1 == pytest.approx(2 / 3)
    assert sum_candidate_scores(()) == CandidateScore(0, 0, 0, 0, 0)


def test_score_fitted_rows_matches_thresholded_model_probabilities():
    rows = _separable_rows()
    fitted = fit_model(ModelSpec("decision_tree_c", 3), rows, seed=7)
    excluded = 2
    score = score_fitted_rows(fitted, rows, excluded=excluded)
    true_positive = false_positive = true_negative = false_negative = 0
    for row in rows:
        predicted = fitted.selection_probability_vector(row.features) >= 0.5
        if row.label and predicted:
            true_positive += 1
        elif row.label:
            false_negative += 1
        elif predicted:
            false_positive += 1
        else:
            true_negative += 1
    assert score.true_positive == true_positive
    assert score.false_positive == false_positive
    assert score.true_negative == true_negative
    assert score.false_negative == false_negative
    assert score.excluded == excluded
    assert score.basis == "caller_rows"
    assert score.scored == len(rows)


def test_score_fitted_rows_rejects_negative_excluded():
    rows = _separable_rows()
    fitted = fit_model(ModelSpec("decision_tree_c", 3), rows, seed=7)
    with pytest.raises(ValueError):
        score_fitted_rows(fitted, rows, excluded=-1)


def test_tracked_cards_match_the_renderer():
    assert CARD.read_text(encoding="utf-8") == render_development_card()
    assert CARD_JSON.read_text(encoding="utf-8") == development_card_json()


def test_card_locks_handoff_counts_and_hashes():
    card = render_development_card()
    handoff = HANDOFF.read_text(encoding="utf-8")
    compact_card = _strip_digit_commas(card)
    compact_handoff = _strip_digit_commas(handoff)
    tokens = [
        *PUBLISHED_DEVELOPMENT_SHA256.values(),
        CARBON_SHA256,
        "101.375",
        "6046",
        "1411",
        "4635",
        "840",
        "2765",
        "1009",
        "3363",
        "973",
        "3142",
    ]
    for token in tokens:
        assert token in compact_card
        assert token in compact_handoff
    facts = development_card_facts()
    assert facts.definite_positive == 1411
    assert facts.definite_negative == 4635
    assert facts.seed == _script_default_seed()
    assert facts.total_time_seconds == 101.375
    assert facts.artifact_schema == ARTIFACT_SCHEMA
    assert facts.feature_names == FEATURE_NAMES
    assert facts.carbon_sha256 == CARBON_SHA256
    assert facts.threshold == 0.5
    assert [(fold.training_positive, fold.training_negative) for fold in facts.folds] == [
        (840, 2765),
        (1009, 3363),
        (973, 3142),
    ]
    assert [(fold.held_out_positive, fold.held_out_negative) for fold in facts.folds] == [
        (571, 1870),
        (402, 1272),
        (438, 1493),
    ]
    for fold in facts.folds:
        assert str(fold.held_out_positive) in card
        assert str(fold.held_out_negative) in card
        assert fold.held_out_positive == facts.definite_positive - fold.training_positive
        assert fold.held_out_negative == facts.definite_negative - fold.training_negative
    for digest in PUBLISHED_DEVELOPMENT_SHA256.values():
        assert digest in card
    assert facts.custody_label == "P04_Private_2026-11-02"
    assert "models/artifacts" not in card
    assert f"{facts.custody_label}/" not in card


def test_candidate_metric_section_states_that_fold_rates_are_unpublished():
    card = render_development_card()
    section = _section(card, "Candidate metrics")
    assert "unpublished" in section
    assert "fifteen fold models were not serialized" in section
    assert "full-data refit" in section
    assert re.search(r"\d+\.\d+", section) is None


def test_development_card_json_has_no_study_metric_keys():
    payload = json.loads(development_card_json())
    assert _METRIC_KEYS.isdisjoint(_keys(payload))
    assert payload["measured_state"] == "public_only"
    assert payload["binary_in_checkout"] is False
    assert payload["definite_positive"] == 1411
    assert payload["definite_negative"] == 4635
    for row in payload["selection"]:
        assert row["measured"] is None
        assert _METRIC_KEYS.isdisjoint(row)
    for fold in payload["folds"]:
        assert _METRIC_KEYS.isdisjoint(fold)
    for name in ("precision", "recall", "f1"):
        assert not hasattr(development_card_facts(), name)


def _separable_rows() -> tuple[LabeledRow, ...]:
    rows: list[LabeledRow] = []
    for index, label in enumerate((True, False, True, False)):
        features = [float(index)] * len(FEATURE_NAMES)
        if label:
            features[0] += 20.0
        rows.append(
            LabeledRow(
                episode_id="EP-TEST",
                slot=index,
                job_id=f"J{index}",
                start_slot=index,
                features=tuple(features),
                label=label,
            )
        )
    return tuple(rows)


def _strip_digit_commas(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", text)


def _section(card: str, heading: str) -> str:
    marker = f"## {heading}\n"
    start = card.index(marker) + len(marker)
    rest = card[start:]
    nxt = rest.find("\n## ")
    return rest if nxt < 0 else rest[:nxt]


def _keys(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def _script_default_seed() -> int:
    path = ROOT / "scripts" / "train_p04_development.py"
    spec = importlib.util.spec_from_file_location("train_p04_development_seed", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DEFAULT_SEED
