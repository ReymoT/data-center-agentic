"""Validate an A01 bounded-validation manifest offline.

This module has no network, process, Ollama, provider, or model-call path.  The
checked-in manifest is expected to be internally valid but blocked.  ``--require-ready``
fails until affected-owner agreement, an exact run commit, reviewed renderers, and a
fresh Matty authorization are recorded explicitly.
"""

import argparse
import json
import re
from pathlib import Path

EXPECTED_IDENTITY = {
    "runtime_version": "0.40.5",
    "model": "qwen3:8b",
    "model_digest": "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41",
    "template_sha256": "ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4",
    "parameters_sha256": "316504eda9b907ddeaf5403f02da3b12d13e998162db42cbb917a1e095cf731a",
}
EXPECTED_SETTINGS = {
    "temperature": 0.2,
    "top_p": 1,
    "seed": 101,
    "num_ctx": 16384,
    "num_predict": 1536,
    "stream": False,
    "think": False,
}
EXPECTED_RESPONSE_TOKENS = {
    "plain_policy_output": 1264,
    "agent_plan": 931,
    "agent_explanation": 298,
}
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_SHA = re.compile(r"[0-9a-f]{40}")


def _sha(value) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _git_sha(value) -> bool:
    return isinstance(value, str) and GIT_SHA.fullmatch(value) is not None


def validate_manifest(manifest: dict, *, require_ready: bool = False) -> list[str]:
    """Return every readiness or integrity blocker without changing the manifest."""
    blockers: list[str] = []

    if manifest.get("schema_version") != "a01-bounded-validation-manifest-v1":
        blockers.append("unexpected manifest schema_version")
    if manifest.get("evidence_kind") != "offline_preparation_not_inference":
        blockers.append("manifest must be labeled offline preparation")
    if manifest.get("preparation_model_calls") != 0:
        blockers.append("offline preparation must record zero model calls")
    if manifest.get("preparation_runtime_requests") != 0:
        blockers.append("offline preparation must record zero runtime requests")

    identity = manifest.get("accepted_identity", {})
    for key, expected in EXPECTED_IDENTITY.items():
        if identity.get(key) != expected:
            blockers.append(f"accepted_identity.{key} does not match the accepted pin")

    settings = manifest.get("accepted_generation_settings", {})
    for key, expected in EXPECTED_SETTINGS.items():
        if settings.get(key) != expected:
            blockers.append(f"accepted_generation_settings.{key} changed")

    sequence = manifest.get("bounded_sequence", {})
    if sequence.get("systems") != ["plain_llm", "agent"]:
        blockers.append("bounded sequence must be Plain first, then Agent")
    if sequence.get("maximum_serial_requests") != 2:
        blockers.append("bounded sequence must permit at most two serial requests")
    for key in ("retries", "warmup_calls", "tool_calls", "simulator_actions", "study_runs"):
        if sequence.get(key) != 0:
            blockers.append(f"bounded_sequence.{key} must be zero")
    if (
        sequence.get("agent_gate")
        != "only_after_valid_plain_stop_and_all_identity_count_offload_gates"
    ):
        blockers.append("Agent dispatch gate changed")

    limits = manifest.get("deadline_proposal", {})
    if limits.get("per_request_seconds") != 150 or limits.get("paired_total_seconds") != 330:
        blockers.append("deadline proposal no longer matches the measured 150/330 recommendation")
    if limits.get("status") not in {"pending_affected_owner_agreement", "accepted"}:
        blockers.append("deadline proposal has an invalid status")

    bounds = manifest.get("response_bounds", {})
    if bounds.get("num_predict") != 1536 or bounds.get("largest_tokens") != 1264:
        blockers.append("response-bound ceiling or maximum changed")
    if bounds.get("measurements") != EXPECTED_RESPONSE_TOKENS:
        blockers.append("response-bound measurements changed")
    if not _sha(bounds.get("evidence_sha256")) or not _sha(bounds.get("implementation_sha256")):
        blockers.append("response-bound evidence and implementation need SHA256 pins")

    agreements = manifest.get("affected_owner_agreement", {})
    for owner in ("nisha", "ved"):
        record = agreements.get(owner, {})
        if record.get("status") not in {"pending", "accepted"}:
            blockers.append(f"{owner} agreement status is invalid")
        if record.get("status") == "accepted" and not record.get("reference"):
            blockers.append(f"{owner} accepted agreement needs an exact reference")
    if limits.get("status") == "accepted" and any(
        agreements.get(owner, {}).get("status") != "accepted"
        or not agreements.get(owner, {}).get("reference")
        for owner in ("nisha", "ved")
    ):
        blockers.append("deadline cannot be accepted without both referenced agreements")

    authorization = manifest.get("run_authorization", {})
    if authorization.get("status") not in {"not_recorded", "recorded"}:
        blockers.append("run authorization status is invalid")
    if authorization.get("status") == "recorded" and not authorization.get("reference"):
        blockers.append("recorded run authorization needs an exact reference")
    if (
        authorization.get("status") == "recorded"
        and authorization.get("authorized_by") != "MattyAnd"
    ):
        blockers.append("recorded run authorization must be issued by MattyAnd")

    freeze = manifest.get("run_freeze", {})
    commit = freeze.get("exact_commit")
    if commit is not None and not _git_sha(commit):
        blockers.append("run_freeze.exact_commit must be a full commit SHA or null")
    if freeze.get("plain_prompt_sha256") is not None and not _sha(
        freeze.get("plain_prompt_sha256")
    ):
        blockers.append("plain_prompt_sha256 must be a SHA256 or null")
    if freeze.get("agent_renderer_ref") is not None and not freeze.get("agent_renderer_ref"):
        blockers.append("agent_renderer_ref cannot be empty")

    if require_ready:
        if limits.get("status") != "accepted":
            blockers.append("exact deadline agreement is not recorded")
        for owner in ("nisha", "ved"):
            if agreements.get(owner, {}).get("status") != "accepted":
                blockers.append(f"{owner} has not accepted the exact deadline")
        if authorization.get("status") != "recorded":
            blockers.append("fresh Matty run authorization is not recorded")
        if commit is None:
            blockers.append("exact run commit is not frozen")
        if freeze.get("plain_prompt_sha256") is None:
            blockers.append("plain prompt hash is not frozen")
        if freeze.get("agent_renderer_ref") is None:
            blockers.append("reviewed Agent renderer reference is not frozen")
        if not manifest.get("ready_for_dispatch"):
            blockers.append("manifest is explicitly not ready for dispatch")
    elif manifest.get("ready_for_dispatch"):
        blockers.append("blocked preparation manifest cannot claim dispatch readiness")

    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    blockers = validate_manifest(manifest, require_ready=args.require_ready)
    if blockers:
        label = "NOT READY" if args.require_ready else "INVALID"
        print(f"A01 bounded-validation manifest: {label}; model calls: 0")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    label = "READY" if args.require_ready else "VALID BLOCKED PREPARATION"
    print(f"A01 bounded-validation manifest: {label}; model calls: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
