"""Small binary-format cases; synthetic metadata is not model-tokenizer evidence."""

import hashlib
import json
import struct

import pytest

from scripts.inspect_gguf_tokenizer import inspect


def text(value):
    raw = value.encode()
    return struct.pack("<Q", len(raw)) + raw


def header(entries):
    return b"GGUF" + struct.pack("<IQQ", 3, 2, entries)


def test_reads_metadata_prefix_without_tensor_data(tmp_path):
    prefix = header(2)
    prefix += text("tokenizer.ggml.tokens") + struct.pack("<IIQ", 9, 8, 2)
    prefix += text("a") + text("é")
    prefix += text("tokenizer.ggml.add_bos_token") + struct.pack("<I?", 7, False)
    path = tmp_path / "synthetic.gguf"
    path.write_bytes(prefix + b"not valid tensor data; must not be parsed")
    result = inspect(path)
    assert result["metadata_prefix_bytes"] == len(prefix)
    assert result["metadata_prefix_sha256"] == hashlib.sha256(prefix).hexdigest()
    encoded = json.dumps(["a", "é"], ensure_ascii=False, separators=(",", ":")).encode()
    assert result["tokenizer"]["tokenizer.ggml.tokens"] == {
        "items": 2,
        "canonical_json_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    assert result["tokenizer"]["tokenizer.ggml.add_bos_token"] is False
    assert not result["tensor_data_read"] and not result["validated_prompt_counter"]


@pytest.mark.parametrize(
    "data",
    [
        b"GGUF",
        b"bad!" + struct.pack("<IQQ", 3, 0, 0),
        b"GGUF" + struct.pack("<IQQ", 2, 0, 0),
        header(100001),
        header(1) + struct.pack("<Q", 65 * 1024 * 1024),
        header(1) + text("x") + struct.pack("<IIQ", 9, 8, 1000001),
        header(1) + text("x") + struct.pack("<IIQ", 9, 9, 1),
        header(1) + text("x") + struct.pack("<I", 99),
        header(2) + (text("x") + struct.pack("<IB", 0, 1)) * 2,
    ],
)
def test_rejects_truncated_unsupported_or_unbounded_metadata(tmp_path, data):
    path = tmp_path / "invalid.gguf"
    path.write_bytes(data)
    with pytest.raises(ValueError):
        inspect(path)


@pytest.mark.parametrize("reference_id,mismatches", [(0, 0), (1, 1)])
def test_compares_real_id_and_merge_order_without_claiming_behavior_equivalence(
    tmp_path, reference_id, mismatches
):
    prefix = header(2)
    prefix += text("tokenizer.ggml.tokens") + struct.pack("<IIQ", 9, 8, 2)
    prefix += text("a") + text("padding")
    prefix += text("tokenizer.ggml.merges") + struct.pack("<IIQ", 9, 8, 1) + text("a b")
    path = tmp_path / "synthetic.gguf"
    path.write_bytes(prefix)
    reference = tmp_path / "reference.json"
    reference.write_text(
        json.dumps(
            {
                "model": {"vocab": {"a": reference_id}, "merges": [["a", "b"]]},
                "added_tokens": [],
            }
        )
    )
    result = inspect(path, reference_tokenizer=reference)["reference_comparison"]
    assert result["token_id_mismatches"] == mismatches
    assert result["merge_order_identical"] and result["gguf_token_ids_not_in_reference"] == 1
    assert not result["behavioral_equivalence_validated"]
