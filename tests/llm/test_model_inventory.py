"""Synthetic metadata tests; actual installation evidence is captured separately."""

from copy import deepcopy

import pytest

from scripts.inspect_ollama import compare_inventory, inventory


def inputs():
    details = {
        "format": "gguf",
        "family": "qwen3",
        "families": ["qwen3"],
        "parameter_size": "8.2B",
        "quantization_level": "Q4_K_M",
    }
    return (
        {"version": "synthetic-runtime"},
        {
            "models": [
                {
                    "name": "qwen3:8b",
                    "digest": "a" * 64,
                    "size": 100,
                    "details": {**details, "runner": "ggml", "context_length": 40960},
                }
            ]
        },
        {
            "details": details,
            "license": "Apache License\nVersion 2.0",
            "template": "synthetic template",
            "parameters": "synthetic parameters",
            "model_info": {"general.architecture": "qwen3"},
            "modelfile": "FROM C:/private/path/to/model",
        },
    )


def test_tag_extensions_do_not_cause_false_identity_mismatch_and_paths_are_excluded():
    result = inventory(*inputs())
    assert result["model_digest"] == "a" * 64
    assert result["license"]["spdx"] == "Apache-2.0"
    assert result["model_calls"] == 0 and result["experiment_ready"] is False
    assert "private" not in str(result) and "modelfile" not in result


@pytest.mark.parametrize(
    "fault", ["missing_model", "short_digest", "different_quantization", "license"]
)
def test_missing_or_wrong_identity_cannot_be_published_as_accepted_inventory(fault):
    version, tags, show = inputs()
    if fault == "missing_model":
        tags["models"] = []
    elif fault == "short_digest":
        tags["models"][0]["digest"] = "a" * 12
    elif fault == "different_quantization":
        tags["models"][0]["details"]["quantization_level"] = "Q8_0"
    else:
        show["license"] = "unverified license"
    with pytest.raises(ValueError):
        inventory(version, tags, show)


def test_comparison_ignores_capture_time_but_rejects_a_changed_artifact():
    original = inventory(*inputs())
    reread = deepcopy(original)
    reread["captured_at_utc"] = "different inspection time"
    compare_inventory(original, reread)
    reread["model_digest"] = "b" * 64
    with pytest.raises(ValueError, match="model_digest"):
        compare_inventory(original, reread)
