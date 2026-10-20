"""Prepare public-development probe inputs offline; never call or load a model.

Uses the real L01 renderer and public F02 example records. Byte/character sizes are
diagnostics, NOT token counts. This is preparation, not a runnable inference driver.
The later authorized probe must call PlainLLMPolicy.propose for its plain attempt.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.llm.plain import render_messages  # noqa: E402

DIGEST = "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"


def prepare(inventory: dict) -> dict:
    examples = ROOT / "tests/contracts/examples"
    state = s.VisibleState.from_json((examples / "visible_state.json").read_text("utf-8"))
    snapshot = s.ConstraintSnapshot.from_json(
        (examples / "constraint_snapshot.json").read_text("utf-8")
    )
    context = s.Context.build(state, snapshot, "flat")
    if not state.waiting_jobs:
        raise ValueError("The probe requires the public nonempty-queue development state")
    plain_messages = render_messages(context)
    rules = (ROOT / "prompts/shared/task_rules.md").read_text("utf-8").strip()
    agent_messages = [
        {
            "role": "system",
            "content": rules + "\n\nReturn a proposed Plan matching the supplied schema. "
            "This is a transport compatibility probe, with no tools or execution. "
            "Use only the supplied public development facts; do not claim checks ran.",
        },
        {"role": "user", "content": context.content.to_json()},
    ]
    candidates = []
    for system, messages, record in (
        ("plain_llm", plain_messages, s.PolicyOutput),
        ("agent", agent_messages, s.Plan),
    ):
        # Prepared request data only. There is deliberately no provider instance,
        # counter callback, network operation, generated output or execution path.
        payload = {
            "model": "qwen3:8b",
            "messages": messages,
            "format": record.model_json_schema(),
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
        encoded = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")
        candidates.append(
            {
                "system": system,
                "response_record": record.__name__,
                "request_sha256": hashlib.sha256(encoded).hexdigest(),
                "request_utf8_bytes": len(encoded),
                "message_characters": sum(len(m["content"]) for m in messages),
                "rendered_prompt_tokens": None,
                "request": payload,
            }
        )
    blockers = [
        "Pinned tokenizer/template-aware counter and both rendered prompt measurements missing",
        "12000-token ceiling provisional; no pre-dispatch context validation evidence",
        "Explicit bounded inference run authorization not recorded",
    ]
    for key, expected in (("runtime_version", "0.40.5"), ("model_digest", DIGEST)):
        if inventory.get(key) != expected:
            blockers.append(f"{key}: agreed {expected}, observed {inventory.get(key)!r}")
    return {
        "evidence_kind": "offline_probe_input_preparation_not_inference",
        "status": "blocked",
        "schema_version": s.SCHEMA_VERSION,
        "context_hash": context.content_hash,
        "episode_id": state.episode_id,
        "slot": state.current_slot,
        "fixture_scope": "public synthetic hand example; carbon semantics unresolved",
        "agreed_runtime_version": "0.40.5",
        "observed_runtime_version": inventory.get("runtime_version"),
        "model_digest": DIGEST,
        "trial_seeds": [101, 102, 103],
        "probe_seed": 101,
        "bounds": {
            "max_run_attempts": 2,
            "max_response_bytes": 2097152,
            "per_call_seconds": 120,
            "overall_seconds": 300,
            "parallel_calls": 1,
            "warmup_calls": 0,
        },
        "model_calls": 0,
        "blockers": blockers,
        "candidates": candidates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = prepare(json.loads(args.inventory.read_text(encoding="utf-8")))
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Prepared both real request shapes offline; model calls: 0; status: blocked")
    for blocker in result["blockers"]:
        print(f"- {blocker}")


if __name__ == "__main__":
    main()
