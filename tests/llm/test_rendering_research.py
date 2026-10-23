"""Actual Go-generated golden prompts and research-boundary rejection tests.

CI needs neither a Go compiler nor tokenizers. These tests do not prove runtime
rendering, token counts, a model response or production counter acceptance.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from dc_sustainability.llm import rendering_research as r

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures/qwen3-go-rendering-vectors.json").read_text("utf-8")
)


@pytest.mark.parametrize("vector", GOLDEN["vectors"], ids=lambda vector: vector["name"])
def test_python_matches_actual_go_engine_golden(vector):
    before = copy.deepcopy(vector["messages"])
    assert r._render_text_history(vector["messages"]) == vector["prompt"]
    assert vector["messages"] == before


def test_golden_provenance_matches_pinned_template_and_oracle_source():
    assert GOLDEN["template_sha256"] == r.TEMPLATE_SHA256
    assert (
        GOLDEN["oracle_source_sha256"]
        == hashlib.sha256(
            (ROOT / "scripts/qwen3_history_oracle.go").read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
    )
    assert (
        GOLDEN["evidence_kind"] == "golden_prompts_from_actual_go_template_engine_not_model_outputs"
    )


@pytest.mark.parametrize(
    "messages",
    [
        None,
        [],
        (),
        [{"role": "user", "content": "x"}],
        [{"role": "system", "content": ""}, {"role": "user", "content": "x"}],
        [{"role": "system", "content": "s"}, {"role": "user", "content": None}],
        [{"role": "system", "content": "s"}, {"role": "user", "content": 1}],
        [{"role": "system", "content": "s"}, {"role": "user", "content": "u", "images": []}],
        [{"role": "system", "content": "s"}, {"role": "USER", "content": "u"}],
        [{"role": "system", "content": "s"}, {"role": "tool", "content": "u"}],
        [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "u"},
            {"role": "system", "content": "second"},
        ],
        [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "u"},
            {"role": "user", "content": "second"},
        ],
        [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "u"},
            {"role": "assistant", "content": "a", "thinking": "hidden"},
        ],
    ],
)
def test_unsupported_history_is_rejected_without_best_effort_rendering(messages):
    with pytest.raises(ValueError, match="research history"):
        r._render_text_history(messages)


def request():
    """Small synthetic request for scope guards, not a token-count fixture."""
    return {
        "model": "qwen3:8b",
        "messages": GOLDEN["vectors"][0]["messages"],
        "format": {"type": "object"},
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.2,
            "top_p": 1,
            "seed": 101,
            "num_ctx": 16384,
            "num_predict": 1536,
        },
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "other"),
        ("stream", True),
        ("stream", 0),
        ("think", True),
        ("think", 0),
        ("keep_alive", "0"),
        ("format", None),
        ("format", {}),
    ],
)
def test_unsupported_request_mode_is_rejected(field, value):
    candidate = request()
    candidate[field] = value
    with pytest.raises(ValueError, match="mode"):
        r._validate_request(candidate)


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", True),
        ("seed", -1),
        ("seed", 1.0),
        ("temperature", float("nan")),
        ("temperature", 0),
        ("top_p", True),
        ("top_p", 0.5),
        ("num_ctx", "16384"),
        ("num_ctx", 32768),
        ("num_predict", True),
        ("num_predict", 1535),
    ],
)
def test_changed_or_non_strict_options_are_rejected(field, value):
    candidate = request()
    candidate["options"][field] = value
    with pytest.raises(ValueError, match="research options"):
        r._validate_request(candidate)


@pytest.mark.parametrize(
    "change", ["extra_request", "missing_request", "extra_option", "missing_option"]
)
def test_unknown_features_and_missing_settings_have_no_implicit_defaults(change):
    candidate = request()
    if change == "extra_request":
        candidate["tools"] = []
    elif change == "missing_request":
        del candidate["format"]
    elif change == "extra_option":
        candidate["options"]["stop"] = []
    else:
        del candidate["options"]["num_ctx"]
    with pytest.raises(ValueError):
        r._validate_request(candidate)


def test_changed_artifact_is_refused_before_rendering():
    with pytest.raises(ValueError, match="pinned research artifact"):
        r.render_candidate(request(), template_bytes=b"unapproved synthetic template")


def test_invalid_unicode_is_not_silently_replaced():
    with pytest.raises(UnicodeEncodeError):
        r._render_text_history(
            [{"role": "system", "content": "s"}, {"role": "user", "content": "\ud800"}]
        )
