"""Inspect local GGUF v3 tokenizer metadata without loading weights or inference.

This is artifact inspection, not a token counter or validated context policy.
Format: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md
Only the bounded metadata prefix is read. Token arrays stay local; the report
contains their counts/hashes and relevant tokenizer flags, never model weights.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path

MAX_METADATA_BYTES = 64 * 1024 * 1024
MAX_ITEMS = 1_000_000
SCALARS = {
    0: "B",
    1: "b",
    2: "H",
    3: "h",
    4: "I",
    5: "i",
    6: "f",
    7: "?",
    10: "Q",
    11: "q",
    12: "d",
}


def inspect(path: Path, *, reference_tokenizer: Path | None = None) -> dict:
    with path.open("rb") as handle:
        digest = hashlib.sha256()

        def read(size):
            if size < 0 or handle.tell() + size > MAX_METADATA_BYTES:
                raise ValueError("GGUF metadata exceeds inspection byte limit")
            data = handle.read(size)
            if len(data) != size:
                raise ValueError("truncated GGUF metadata")
            digest.update(data)
            return data

        def number(fmt):
            return struct.unpack("<" + fmt, read(struct.calcsize(fmt)))[0]

        def string():
            return read(number("Q")).decode("utf-8", errors="strict")

        def value(kind, *, in_array=False):
            if kind in SCALARS:
                return number(SCALARS[kind])
            if kind == 8:
                return string()
            if kind == 9 and not in_array:
                element_type, count = number("I"), number("Q")
                if count > MAX_ITEMS or element_type not in {*SCALARS, 8}:
                    raise ValueError("unsupported or oversized GGUF metadata array")
                return [value(element_type, in_array=True) for _ in range(count)]
            raise ValueError(f"unsupported GGUF metadata type: {kind}")

        if read(4) != b"GGUF" or number("I") != 3:
            raise ValueError("only little-endian GGUF v3 is supported")
        tensors, count = number("Q"), number("Q")
        if count > 100_000:
            raise ValueError("too many GGUF metadata entries")
        metadata = {}
        for _ in range(count):
            key = string()
            if key in metadata:
                raise ValueError(f"duplicate GGUF metadata key: {key}")
            metadata[key] = value(number("I"))
        report = {
            "evidence_kind": "gguf_tokenizer_metadata_not_token_counts",
            "gguf_version": 3,
            "tensor_count": tensors,
            "metadata_entries": count,
            "metadata_prefix_bytes": handle.tell(),
            "metadata_prefix_sha256": digest.hexdigest(),
            "tensor_data_read": False,
            "model_calls": 0,
            "validated_prompt_counter": False,
            "tokenizer": {},
        }
        for key, item in sorted(metadata.items()):
            if not key.startswith("tokenizer."):
                continue
            if isinstance(item, list):
                encoded = json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode()
                report["tokenizer"][key] = {
                    "items": len(item),
                    "canonical_json_sha256": hashlib.sha256(encoded).hexdigest(),
                }
            elif isinstance(item, str) and len(item) > 200:
                report["tokenizer"][key] = {
                    "utf8_bytes": len(item.encode()),
                    "sha256": hashlib.sha256(item.encode()).hexdigest(),
                }
            else:
                report["tokenizer"][key] = item
        if reference_tokenizer is not None:
            if reference_tokenizer.stat().st_size > MAX_METADATA_BYTES:
                raise ValueError("reference tokenizer exceeds inspection byte limit")
            reference_bytes = reference_tokenizer.read_bytes()
            reference = json.loads(reference_bytes)
            vocab = dict(reference["model"]["vocab"])
            for token in reference["added_tokens"]:
                if token["content"] in vocab and vocab[token["content"]] != token["id"]:
                    raise ValueError("reference tokenizer has conflicting token IDs")
                vocab[token["content"]] = token["id"]
            tokens = metadata["tokenizer.ggml.tokens"]
            if len(vocab) > MAX_ITEMS or any(
                type(index) is not int or index < 0 or index >= MAX_ITEMS
                for index in vocab.values()
            ):
                raise ValueError("invalid reference token IDs")
            if len(set(vocab.values())) != len(vocab):
                raise ValueError("reference tokenizer assigns multiple tokens to one ID")
            mismatches = sum(
                index >= len(tokens) or tokens[index] != token for token, index in vocab.items()
            )
            merges = reference["model"]["merges"]
            merges = [pair if isinstance(pair, str) else " ".join(pair) for pair in merges]
            report["reference_comparison"] = {
                "tokenizer_sha256": hashlib.sha256(reference_bytes).hexdigest(),
                "reference_token_ids": len(vocab),
                "token_id_mismatches": mismatches,
                "gguf_token_ids_not_in_reference": len(
                    set(range(len(tokens))) - set(vocab.values())
                ),
                "merge_order_identical": metadata["tokenizer.ggml.merges"] == merges,
                "behavioral_equivalence_validated": False,
            }
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-tokenizer", type=Path)
    args = parser.parse_args()
    report = inspect(args.gguf, reference_tokenizer=args.reference_tokenizer)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("Inspected tokenizer metadata only; tensor data read: false; model calls: 0")


if __name__ == "__main__":
    main()
