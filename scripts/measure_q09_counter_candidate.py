"""Measure actual BPE tokens for a restricted legacy-rendering research candidate.

Needs an explicitly supplied compiled qwen3_legacy_render.go and an isolated
tokenizers==0.23.3 installation. Never installs dependencies, contacts an API,
loads weights, or supplies a production counter. Results remain BLOCKED until
runtime rendering/tokenizer equivalence and dependency adoption are established.
"""

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
from pathlib import Path

TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
TEMPLATE_SHA256 = "ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4"


def measure(*, tokenizer_path: Path, template_path: Path, renderer: Path, preparation: Path):
    import tokenizers

    if importlib.metadata.version("tokenizers") != "0.23.3":
        raise ValueError("research candidate requires tokenizers==0.23.3")
    tokenizer_bytes, template_bytes = tokenizer_path.read_bytes(), template_path.read_bytes()
    if hashlib.sha256(tokenizer_bytes).hexdigest() != TOKENIZER_SHA256:
        raise ValueError("tokenizer artifact differs from the pinned research reference")
    if hashlib.sha256(template_bytes).hexdigest() != TEMPLATE_SHA256:
        raise ValueError("template differs from the installed research reference")
    source = json.loads(preparation.read_text(encoding="utf-8"))
    if source.get("evidence_kind") != "offline_probe_input_preparation_not_inference":
        raise ValueError("expected the public Q09 probe preparation record")
    tokenizer = tokenizers.Tokenizer.from_str(tokenizer_bytes.decode("utf-8"))

    def render(messages):
        process = subprocess.run(
            [str(renderer.resolve())],
            input=json.dumps({"template": template_bytes.decode(), "messages": messages}),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
            timeout=30,
        )
        return json.loads(process.stdout)["prompt"]

    # Hand-derived whitespace/special-marker checks against the actual Go engine,
    # including Unicode and content resembling template actions (must stay data).
    for system_text, user_text in (("SYSTEM", "USER"), ("é", "温度 🧪"), ("{{ .Tools }}", "a\nb")):
        expected = (
            "<|im_start|>system\n\n" + system_text + "<|im_end|>\n"
            "<|im_start|>user\n" + user_text + " /no_think<|im_end|>\n"
            "<|im_start|>assistant\n<think>\n\n</think>\n\n"
        )
        if (
            render(
                [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]
            )
            != expected
        ):
            raise ValueError("legacy rendering differs from hand-derived template vector")

    rows = []
    for item in source["candidates"]:
        request = item["request"]
        encoded = json.dumps(request, allow_nan=False, separators=(",", ":")).encode()
        if hashlib.sha256(encoded).hexdigest() != item["request_sha256"]:
            raise ValueError("prepared request hash mismatch")
        if request["model"] != "qwen3:8b" or request["think"] is not False:
            raise ValueError("unsupported model/thinking mode")
        messages = request["messages"]
        if (
            len(messages) != 2
            or [m.get("role") for m in messages] != ["system", "user"]
            or any(set(m) != {"role", "content"} for m in messages)
            or request.get("tools")
        ):
            raise ValueError("candidate supports only two-message, text-only, tool-free probes")
        prompt = render(messages)
        ids = tokenizer.encode(prompt, add_special_tokens=False).ids
        rows.append(
            {
                "system": item["system"],
                "request_sha256": item["request_sha256"],
                "candidate_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "candidate_prompt_utf8_bytes": len(prompt.encode()),
                "candidate_bpe_tokens": len(ids),
                "token_ids_sha256": hashlib.sha256(
                    json.dumps(ids, separators=(",", ":")).encode()
                ).hexdigest(),
                "schema_utf8_bytes": len(
                    json.dumps(request["format"], separators=(",", ":")).encode()
                ),
            }
        )
    return {
        "evidence_kind": "offline_tokenizer_rendering_candidate_not_deployment_validation",
        "status": "blocked",
        "model_calls": 0,
        "validated_prompt_counter": False,
        "tokenizers_version": "0.23.3",
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizer_source": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json",
        "template_sha256": TEMPLATE_SHA256,
        "rendering_scope": "installed Go template, exactly system then user, think=false, no tools",
        "schema_scope": "format retained in request; not a template variable on this legacy path",
        "renderer_binary_sha256": hashlib.sha256(renderer.read_bytes()).hexdigest(),
        "renderer_source_sha256": hashlib.sha256(
            Path(__file__).with_name("qwen3_legacy_render.go").read_bytes()
        ).hexdigest(),
        "hand_derived_render_vectors_passed": 3,
        "candidates": rows,
        "blockers": [
            "HF tokenizer behavior versus installed GGUF/runtime tokenizer not validated",
            "Actual 0.40.6 native-versus-template rendering path not established",
            "Restricted candidate does not implement general agent repair/history rendering",
            "New tokenizer dependency not adopted in shared environment/locks",
            "Runtime agreement, service/context validation and explicit run authorization pending",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tokenizer", "template", "renderer", "preparation", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = measure(
        tokenizer_path=args.tokenizer,
        template_path=args.template,
        renderer=args.renderer,
        preparation=args.preparation,
    )
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Measured actual candidate BPE tokens offline; production validation: blocked")


if __name__ == "__main__":
    main()
