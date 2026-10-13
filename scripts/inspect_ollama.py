"""Read-only inventory of the accepted local model; never pulls or calls a model.

This is installation evidence, not an experiment configuration or F02 interface.
Only public metadata and content hashes are exported; local paths are excluded.
"""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MODEL = "qwen3:8b"
COMPARISON_FIELDS = (
    "runtime_version",
    "model_digest",
    "details",
    "license",
    "template_sha256",
    "parameters_sha256",
)


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def inventory(version: dict, tags: dict, show: dict) -> dict:
    """Require actual identity/quantization/license evidence; no inferred success."""
    models = [m for m in tags["models"] if m["name"] == MODEL]
    if len(models) != 1:
        raise ValueError("the accepted model must be uniquely installed")
    model = models[0]
    if not isinstance(version.get("version"), str) or not version["version"]:
        raise ValueError("runtime version is missing")
    if not re.fullmatch(r"[0-9a-f]{64}", model["digest"]):
        raise ValueError("a full model digest is required")
    details = show["details"]
    # /api/tags may add runner/context fields not present in /api/show.
    identity_fields = ("format", "family", "families", "parameter_size", "quantization_level")
    if any(details[k] != model["details"][k] for k in identity_fields):
        raise ValueError("tag and show metadata disagree")
    if details["quantization_level"] != "Q4_K_M" or details["family"] != "qwen3":
        raise ValueError("installed artifact differs from accepted Qwen3/Q4_K_M")
    if not re.search(r"Apache License\s+Version 2\.0", show["license"]):
        raise ValueError("installed license does not identify Apache 2.0")
    for name in ("license", "template", "parameters"):
        if not isinstance(show[name], str) or not show[name].strip():
            raise ValueError(f"missing {name} evidence")
    if type(model["size"]) is not int or model["size"] <= 0:
        raise ValueError("installed artifact size is invalid")
    info = show["model_info"]
    return {
        "evidence_kind": "installed_model_inventory_not_run_configuration",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "runtime_version": version["version"],
        "model_digest": model["digest"],
        "size_bytes": model["size"],
        "details": {k: details[k] for k in identity_fields},
        "capabilities": show.get("capabilities", []),
        "model_info": {
            k: info[k]
            for k in (
                "general.architecture",
                "general.parameter_count",
                "qwen3.context_length",
                "qwen3.block_count",
                "qwen3.embedding_length",
            )
            if k in info
        },
        "license": {
            "spdx": "Apache-2.0",
            "utf8_sha256": text_hash(show["license"]),
            "source": "local /api/show license field",
            "upstream_model_card": "https://huggingface.co/Qwen/Qwen3-8B",
            "packaged_model": "https://ollama.com/library/qwen3:8b",
        },
        "template_sha256": text_hash(show["template"]),
        "parameters_sha256": text_hash(show["parameters"]),
        "model_calls": 0,
        "experiment_ready": False,
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, new_url):
        raise ValueError("metadata inspection cannot follow a redirect")


def inspect(base_url: str) -> dict:
    url = urlsplit(base_url)
    if (
        url.scheme != "http"
        or url.hostname not in {"127.0.0.1", "localhost", "::1"}
        or url.username
        or url.password
        or url.path not in {"", "/"}
        or url.query
        or url.fragment
    ):
        raise ValueError("use a loopback HTTP endpoint without credentials or a path")
    opener = build_opener(ProxyHandler({}), NoRedirect())

    def read(path: str, body=None):
        request = Request(
            base_url.rstrip("/") + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        with opener.open(request, timeout=10) as response:
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("metadata response exceeds 1 MiB")
            return json.loads(raw)

    version, tags = read("/api/version"), read("/api/tags")
    show = read("/api/show", {"model": MODEL, "verbose": False})
    result = inventory(version, tags, show)
    # Detect a mutable tag being replaced while its metadata was inspected.
    again = inventory(
        read("/api/version"),
        read("/api/tags"),
        read("/api/show", {"model": MODEL, "verbose": False}),
    )
    compare_inventory(result, again)
    return result


def compare_inventory(expected: dict, actual: dict):
    changed = [key for key in COMPARISON_FIELDS if expected[key] != actual[key]]
    if changed:
        raise ValueError(f"installed inventory differs in: {', '.join(changed)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--compare", type=Path, help="compare installed identity to a saved inventory"
    )
    parser.add_argument("--out", type=Path, help="write a new inventory file; refuses to overwrite")
    args = parser.parse_args()
    actual = inspect(args.url)
    if args.compare:
        compare_inventory(json.loads(args.compare.read_text(encoding="utf-8")), actual)
    text = json.dumps(actual, indent=2, allow_nan=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Recorded installed metadata in {args.out}; model calls: 0")
    else:
        print(text)


if __name__ == "__main__":
    main()
