"""Offline context accounting for saved requests and a proposed output reserve."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.agent.renderers import render_proposal  # noqa: E402
from dc_sustainability.llm.plain import render_messages  # noqa: E402
from dc_sustainability.llm.rendering_research import _render_text_history  # noqa: E402
from dc_sustainability.llm.response_bounds import bounded_response_schema  # noqa: E402
from scripts.measure_a01_response_bounds import TOKENIZER_SHA256, _max_state  # noqa: E402
from tests.contracts import fixtures as f  # noqa: E402


def candidate_schema(original):
    """Modify the three explanation text bounds in a copy, retaining plan limits."""
    schema = copy.deepcopy(original)
    explanation = schema if schema["title"] == "Explanation" else schema["$defs"].get("Explanation")
    if explanation is not None:
        explanation["properties"]["summary"]["maxLength"] = 256
        explanation["properties"]["limitations"]["items"]["maxLength"] = 256
        schema["$defs"]["Claim"]["properties"]["text"]["maxLength"] = 256
    return schema


def assess(attempts, tokenizer_path):
    import tokenizers

    raw = tokenizer_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != TOKENIZER_SHA256 or tokenizers.__version__ != "0.23.3":
        raise ValueError("pinned Qwen3 tokenizer and tokenizers 0.23.3 required")
    tokenizer = tokenizers.Tokenizer.from_str(raw.decode())
    rows = []
    seen = set()
    for path in sorted(attempts.rglob("provider-attempts/*.json")):
        attempt = json.loads(path.read_bytes())
        if attempt["run_id"] != "RUN-fd87c6c8a9cb":
            raise ValueError("unexpected saved run")
        request = json.loads(attempt["request_json"])
        identity = attempt["client_trace_id"]
        if identity in seen:
            raise ValueError("duplicate attempt identity")
        seen.add(identity)
        rendered = _render_text_history(request["messages"])
        count = len(tokenizer.encode(rendered, add_special_tokens=False).ids)
        if count != attempt["prompt_tokens"]:
            raise ValueError("saved native/offline prompt count mismatch")
        changed = candidate_schema(request["format"])
        rows.append(
            {
                "system": attempt["system"],
                "slot": attempt["slot"],
                "stage": attempt["stage"],
                "attempt_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "request_sha256": hashlib.sha256(attempt["request_json"].encode()).hexdigest(),
                "prompt_tokens": count,
                "native_count_matches": True,
                "candidate_schema_sha256": s.sha256_hex(changed),
                "context_headroom_with_4096_output": 16384 - 4096 - count,
            }
        )
    if len(rows) != 17:
        raise ValueError("expected exactly 17 saved requests")
    state = _max_state()
    stress = []
    for system, representation, model, renderer in (
        ("plain_llm", "flat", s.PolicyOutput, render_messages),
        ("agent", "graph", s.Plan, render_proposal),
    ):
        context = s.Context.build(state, f.snapshot(), representation=representation)
        messages = renderer(context)
        count = len(tokenizer.encode(_render_text_history(messages), add_special_tokens=False).ids)
        schema = candidate_schema(bounded_response_schema(model, state, system=system)[0])
        stress.append(
            {
                "system": system,
                "waiting_jobs": 20,
                "prompt_tokens": count,
                "candidate_schema_sha256": s.sha256_hex(schema),
                "context_headroom_with_4096_output": 12288 - count,
            }
        )
    return {
        "scope": "offline candidate context accounting; no production setting adoption",
        "tokenizer_sha256": TOKENIZER_SHA256,
        "context_tokens": 16384,
        "proposed_output_tokens": 4096,
        "required_max_prompt_tokens": 12288,
        "current_max_prompt_tokens": 14848,
        "overflow_if_old_prompt_ceiling_is_retained": 2560,
        "saved_requests": rows,
        "synthetic_stress_prompts": stress,
        "model_calls": 0,
        "limitations": [
            "Candidate schema changes are copied JSON specifications, not runtime grammar compilation.",
            "The accepted template renders messages; format stays a separate grammar argument.",
            "New native/runtime parity and timing require an authorized candidate validation.",
            "Samples do not bound every possible prompt; each request must enforce the new ceiling.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = assess(args.attempts, args.tokenizer)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print("17 native counts matched; required candidate prompt ceiling: 12288")
    print(result["synthetic_stress_prompts"])


if __name__ == "__main__":
    main()
