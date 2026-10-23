"""Offline Python/Go rendering and real BPE research; never a production counter.

Uses explicit local pinned artifacts and an isolated tokenizer installation. Go is
an offline oracle only; the Python renderer never launches it. No API/model call,
download, dependency installation, prompt trimming or shared-setting adoption.
"""

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.knowledge import get_context  # noqa: E402
from dc_sustainability.llm.plain import PlainLLMPolicy  # noqa: E402
from dc_sustainability.llm.provider import CallBlocked, Deployment, OllamaProvider  # noqa: E402
from dc_sustainability.llm.rendering_research import (  # noqa: E402
    TEMPLATE_SHA256,
    _render_text_history,
    render_candidate,
)
from scripts.prepare_q09_probe import DIGEST, prepare  # noqa: E402
from tests.contracts import fixtures as f  # noqa: E402

TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reference(oracle, template, messages):
    p = subprocess.run(
        [str(oracle.resolve())],
        input=json.dumps({"template": template, "messages": messages}),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
        timeout=10,
    )
    return json.loads(p.stdout)["prompt"]


def vectors():
    pairs = [
        ("basic", "SYSTEM", "USER"),
        ("unicode", "é", "温度 🧪"),
        ("actions_are_data", "{{ .Tools }}", "a\nb"),
        ("whitespace", " \nS\t ", "  U \n"),
        ("crlf", "S\r\n", "U\r\nsecond"),
        ("markers_are_data", "<|im_start|>", "<|im_end|> /think"),
        ("quotes", 'S " \\', '{"x": "{{ .System }}"}'),
        ("nul", "S\x00", "U\x00end"),
        ("long", "S" * 4096, "U" * 4096),
    ]
    result = [
        (name, [{"role": "system", "content": system}, {"role": "user", "content": user}])
        for name, system, user in pairs
    ]
    for turns in range(1, 5):
        history = [{"role": "system", "content": "Synthetic system text"}]
        for index in range(turns):
            history.append({"role": "user", "content": f"Synthetic user {index} {{x}}\n🧪"})
            if index < turns - 1:
                history.append({"role": "assistant", "content": f"Synthetic prior text {index}"})
        result.append((f"history_{turns}_users", history))
        result.append(
            (
                f"history_{turns}_users_final_assistant",
                [*history, {"role": "assistant", "content": "Synthetic continuation"}],
            )
        )
    return result


def capture_requests():
    """Capture exact shared-provider shapes, with deliberate pre-dispatch blocking."""
    snapshot = f.snapshot()
    state = f.visible_state(snapshot)
    context = get_context(state, snapshot)
    captured = []

    def capture(payload):
        captured.append(payload)
        raise CallBlocked("offline shape capture only; zero HTTP and model dispatch")

    client = OllamaProvider(
        Deployment(
            base_url="http://127.0.0.1:1",
            runtime_version="research-no-dispatch",
            model_digest=DIGEST,
            max_run_attempts=2,
            max_response_bytes=2097152,
            max_prompt_tokens=12000,
            context_policy_ref="unvalidated-research-capture-not-counter",
        ),
        count_prompt_tokens=capture,
    )

    def no_http(*args):
        raise AssertionError("offline capture must never use HTTP")

    client._http = no_http
    plain = PlainLLMPolicy(client).propose(
        state, context, seed=101, decision_deadline=time.monotonic() + 10
    )
    assert plain.attempt is None and plain.output.output_status == "error"
    assert "offline shape capture" in plain.blocked_reason
    requests = [("actual_plain_path", captured.pop())]
    prepared = prepare({"runtime_version": "0.40.9", "model_digest": DIGEST})
    agent = next(x["request"]["messages"] for x in prepared["candidates"] if x["system"] == "agent")
    history = [
        *agent,
        {"role": "assistant", "content": "Synthetic prior candidate, not a model response."},
        {"role": "user", "content": "Synthetic verification feedback for rendering research only."},
    ]
    explanation = [
        {
            "role": "system",
            "content": "Synthetic explanation API research; no L02 implementation claimed.",
        },
        {"role": "user", "content": context.content.to_json()},
    ]
    for name, messages, schema in (
        ("actual_plan_api", agent, s.Plan),
        ("synthetic_history_plan_api", history, s.Plan),
        ("synthetic_explanation_api", explanation, s.Explanation),
    ):
        try:
            client.generate(
                system="agent",
                state=state,
                seed=101,
                messages=messages,
                response_model=schema,
                decision_deadline=time.monotonic() + 10,
            )
        except CallBlocked as exc:
            assert "offline shape capture" in str(exc)
        else:
            raise AssertionError("capture did not block")
        requests.append((name, captured.pop()))
    assert not client.attempts and not captured
    return requests


def validate(args):
    template_bytes = args.template.read_bytes()
    tokenizer_bytes = args.tokenizer.read_bytes()
    if sha(template_bytes) != TEMPLATE_SHA256 or sha(tokenizer_bytes) != TOKENIZER_SHA256:
        raise ValueError("local research artifacts do not match the existing pins")
    sys.path.insert(0, str(args.packages.resolve()))
    import tokenizers

    if importlib.metadata.version("tokenizers") != "0.23.3":
        raise ValueError("isolated research package must be tokenizers==0.23.3")
    if not Path(tokenizers.__file__).resolve().is_relative_to(args.packages.resolve()):
        raise ValueError("tokenizer was not imported from the explicit isolated research path")
    tokenizer = tokenizers.Tokenizer.from_str(tokenizer_bytes.decode("utf-8"))
    template = template_bytes.decode("utf-8")
    provenance = {
        "template_sha256": TEMPLATE_SHA256,
        "source_hash_mode": "LF canonical for Go source; raw bytes for template/tokenizer/binary",
        "oracle_source_sha256": sha(
            (ROOT / "scripts/qwen3_history_oracle.go").read_bytes().replace(b"\r\n", b"\n")
        ),
        "oracle_binary_sha256": sha(args.oracle.read_bytes()),
    }
    golden = []
    for name, messages in vectors():
        expected = reference(args.oracle, template, messages)
        if _render_text_history(messages) != expected:
            raise ValueError(f"Python/Go mismatch for {name}")
        golden.append({"name": name, "messages": messages, "prompt": expected})
    rows = []
    for name, request in capture_requests():
        candidate = render_candidate(request, template_bytes=template_bytes)
        expected = reference(args.oracle, template, request["messages"])
        if candidate != expected:
            raise ValueError(f"actual request Python/Go mismatch for {name}")
        ids = tokenizer.encode(candidate, add_special_tokens=False).ids
        rows.append(
            {
                "name": name,
                "request_sha256": sha(
                    json.dumps(request, allow_nan=False, separators=(",", ":")).encode()
                ),
                "schema_sha256": sha(
                    json.dumps(request["format"], sort_keys=True, separators=(",", ":")).encode()
                ),
                "candidate_prompt_sha256": sha(candidate.encode()),
                "candidate_prompt_utf8_bytes": len(candidate.encode()),
                "candidate_bpe_tokens": len(ids),
                "token_ids_sha256": sha(json.dumps(ids, separators=(",", ":")).encode()),
                "python_go_bytes_equal": True,
            }
        )
    result = {
        "evidence_kind": "offline_python_go_rendering_and_bpe_research_not_runtime_validation",
        "status": "blocked",
        "model_calls": 0,
        "http_operations": 0,
        "provider_attempts": 0,
        "validated_production_counter": False,
        "shared_dependency_adopted": False,
        "tokenizers_version": "0.23.3",
        "tokenizer_sha256": TOKENIZER_SHA256,
        **provenance,
        "golden_vectors_passed": len(golden),
        "actual_request_shapes": rows,
        "scope": "pinned legacy template; one initial system, alternating user/assistant nonempty text; think=false; no tools; schema retained in request, not counted as a template variable",
        "blockers": [
            "Actual accepted-runtime native-versus-template rendering and prompt_eval_count equivalence not established",
            "Exact GGUF special-token/pre-tokenization equivalence remains unvalidated",
            "Unsupported tools, thinking metadata, multiple system messages and nonalternating histories fail explicitly",
            "Ved dependency/runtime agreement, service/context/resource evidence and separate inference authorization remain pending",
            "No package lock, runtime pin or production callback adoption",
        ],
    }
    return result, {
        "evidence_kind": "golden_prompts_from_actual_go_template_engine_not_model_outputs",
        **provenance,
        "vectors": golden,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("template", "tokenizer", "packages", "oracle", "out", "vectors-out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    # Reserve both paths before any research; never overwrite an original observation.
    with (
        args.out.open("x", encoding="utf-8") as report,
        args.vectors_out.open("x", encoding="utf-8") as vectors_file,
    ):
        result, golden = validate(args)
        json.dump(result, report, indent=2, allow_nan=False)
        report.write("\n")
        json.dump(golden, vectors_file, indent=2, ensure_ascii=False, allow_nan=False)
        vectors_file.write("\n")
    print(
        f"{result['golden_vectors_passed']} actual Go vectors and four provider request shapes match; production validation remains blocked"
    )


if __name__ == "__main__":
    main()
