"""Measure candidate explanation lengths offline; do not change runtime defaults."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.measure_a01_response_bounds import (  # noqa: E402
    TOKENIZER_SHA256,
    _max_state,
    _maximal_records,
)


def assess(tokenizer_path):
    import tokenizers

    raw = tokenizer_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != TOKENIZER_SHA256:
        raise ValueError("pinned Qwen3 tokenizer required")
    tokenizer = tokenizers.Tokenizer.from_str(raw.decode())
    records, _ = _maximal_records(_max_state())
    rows = []
    for limit in (96, 192, 256, 384):
        for pattern in ("complete sentence", "dense text"):
            text = (
                "The job can start after checking capacity and the available carbon forecast. "
                if pattern == "complete sentence"
                else "碳能水1234567890abcdefghijklmnopqrstuvwxyz"
            )
            text = (text * (limit // len(text) + 1))[:limit]
            for name, original in records.items():
                value = original.to_jsonable()
                if name == "agent_plan":
                    continue
                explanation = value["explanation"] if name == "plain_policy_output" else value
                explanation["summary"] = text
                explanation["limitations"] = [text] * 4
                for claim in explanation["claims"]:
                    claim["text"] = text
                # Keep the existing 96-character plan details and four-claim shape.
                type(original).from_jsonable(value)
                wire = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                count = len(tokenizer.encode(wire, add_special_tokens=False).ids)
                rows.append(
                    {
                        "limit": limit,
                        "fixture": pattern,
                        "shape": name,
                        "tokens": count,
                        "fits_current_1536_output": count <= 1536,
                    }
                )
    return {
        "scope": "synthetic candidate response measurement, not a worst-case bound",
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizers_version": tokenizers.__version__,
        "rows": rows,
        "model_calls": 0,
        "limitations": [
            "Character limits alone do not bound tokenizer costs for all text.",
            "Prompt plus schema plus output must also fit the context before adoption.",
            "No candidate grammar, runtime setting or response pin is adopted here.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = assess(args.tokenizer)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
