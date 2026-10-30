"""Measure the accepted A01 bounded response shapes offline with the pinned tokenizer.

This script never starts Ollama, loads model weights, opens a socket, or generates
model output.  It constructs the largest valid 20-job development response under
the request-local limits and counts its retained JSON with the hash-pinned Qwen3
tokenizer research artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.data.scenarios import generate_jobs  # noqa: E402
from dc_sustainability.llm.response_bounds import bounded_response_schema  # noqa: E402
from tests.contracts import fixtures as f  # noqa: E402

TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"


def _max_state() -> s.VisibleState:
    snapshot = f.snapshot()
    jobs = tuple(
        private.job for private in generate_jobs("spike", seed=20261029, split="development")
    )
    return s.VisibleState.from_snapshot(
        snapshot,
        episode_id="EP-A01BOUNDS",
        current_slot=17,
        state_version=17,
        waiting_jobs=jobs,
        carbon_facts=tuple(fact for fact in f.forecasts() if fact.valid_slot >= 17),
    )


def _visible_evidence(state: s.VisibleState) -> tuple[str, ...]:
    ids = ["FACT-SITE-BG", "FACT-SITE-PUE", "FACT-SITE-SLOTH"]
    ids.extend(f"FACT-JOB-{job.job_id}" for job in state.waiting_jobs)
    ids.extend(fact.fact_id for fact in state.carbon_facts)
    ids.extend(state.constraint_ids)
    return tuple(sorted(set(ids), key=lambda item: (-len(item), item)))


def _maximal_records(state: s.VisibleState):
    _, limits = bounded_response_schema(s.PolicyOutput, state, system="plain_llm")
    evidence = _visible_evidence(state)[: limits.evidence_ids]
    text = "X" * limits.text_characters
    plan = s.Plan(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        deferrals=tuple(
            s.Deferral(
                job_id=job.job_id,
                reason="other",
                detail=text,
                evidence_ids=evidence,
            )
            for job in state.waiting_jobs
        ),
        evidence_ids=evidence,
        status="proposed",
    )
    explanation = s.Explanation(
        source="llm",
        summary=text,
        claims=tuple(
            s.Claim(
                claim_id=f"C{index + 1}",
                text=text,
                evidence_ids=evidence,
                value=999999.999,
                unit="kg",
            )
            for index in range(limits.claims)
        ),
        limitations=tuple(text for _ in range(limits.limitations)),
    )
    return {
        "plain_policy_output": s.PolicyOutput(
            system="plain_llm",
            output_status="ok",
            plan=plan,
            explanation=explanation,
        ),
        "agent_plan": plan,
        "agent_explanation": explanation,
    }, limits


def measure(tokenizer_path: Path) -> dict:
    import tokenizers

    if importlib.metadata.version("tokenizers") != "0.23.3":
        raise ValueError("measurement requires isolated tokenizers==0.23.3")
    raw_tokenizer = tokenizer_path.read_bytes()
    if hashlib.sha256(raw_tokenizer).hexdigest() != TOKENIZER_SHA256:
        raise ValueError("tokenizer artifact differs from the pinned Qwen3 reference")
    tokenizer = tokenizers.Tokenizer.from_str(raw_tokenizer.decode("utf-8"))
    state = _max_state()
    records, limits = _maximal_records(state)
    rows = []
    for name, record in records.items():
        raw = record.to_json().encode("utf-8")
        ids = tokenizer.encode(raw.decode("utf-8"), add_special_tokens=False).ids
        rows.append(
            {
                "shape": name,
                "record_type": type(record).__name__,
                "utf8_bytes": len(raw),
                "candidate_bpe_tokens": len(ids),
                "json_sha256": hashlib.sha256(raw).hexdigest(),
                "token_ids_sha256": hashlib.sha256(
                    json.dumps(ids, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
            }
        )
    return {
        "evidence_kind": "offline_a01_bounded_response_measurement_not_model_output",
        "model_calls": 0,
        "runtime_requests": 0,
        "tokenizers_version": "0.23.3",
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizer_source": (
            "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json"
        ),
        "fixture": "20-job provisional development spike; no held-out data",
        "waiting_jobs": len(state.waiting_jobs),
        "bounds": {
            "plan_entries_per_category": limits.plan_entries,
            "claims": limits.claims,
            "limitations": limits.limitations,
            "text_characters": limits.text_characters,
            "evidence_ids_per_field": limits.evidence_ids,
        },
        "num_predict_accepted_setting": 1536,
        "measurements": rows,
        "largest_candidate_bpe_tokens": max(row["candidate_bpe_tokens"] for row in rows),
        "limitations": [
            "Counts are for deterministic maximal valid fixtures, not model output.",
            "The pinned tokenizer matched earlier native prompt counts but is not a model run.",
            "A fixed deadline still requires affected-owner agreement and fresh authorization.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.tokenizer)
    if result["largest_candidate_bpe_tokens"] > result["num_predict_accepted_setting"]:
        raise ValueError("bounded maximal response exceeds the accepted generation ceiling")
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        "Measured A01 bounded response shapes offline; model calls: 0; largest tokens: "
        f"{result['largest_candidate_bpe_tokens']}"
    )


if __name__ == "__main__":
    main()
