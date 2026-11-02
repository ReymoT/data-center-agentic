"""Offline receiving pin preparation only; no model/provider construction or dispatch."""

import json
from pathlib import Path

from dc_sustainability.agent import renderers
from dc_sustainability.experiments.config import (
    ModelSettings,
    RunConfig,
    TrainedSettings,
    lf_sha256,
    load_bundle,
)
from dc_sustainability.experiments.trained import TrainedInputs, TrainedPolicy, check_inputs
from dc_sustainability.explanations.agent import explanation_template_sha256
from dc_sustainability.llm.plain import prompt_template_sha256
from dc_sustainability.policies.learned import load_verified


def prepare(candidate: dict, artifact_paths: dict[str, Path], root: Path) -> dict:
    """Validate all offline identities and actual binary bindings, without execution."""
    identity = candidate["candidate_config_identity"]
    if candidate["dispatch_authorized"] is not False:
        raise ValueError("offline preparation must not claim dispatch authorization")
    if identity["lock_sha256"] != lf_sha256(
        root / "requirements/requirements-windows-py312.lock.txt"
    ):
        raise ValueError("candidate lock must use the current LF-normalized CLI hash")
    bundle_path = root / "docs/evidence/ep-hand1-episode-bundle.json"
    bundle = load_bundle(bundle_path)
    if identity["episodes"] != [
        {"episode_id": "EP-HAND1", "bundle_sha256": lf_sha256(bundle_path)}
    ]:
        raise ValueError("only exact public EP-HAND1 receiving is prepared here")
    pins = identity["model"]
    expected_outer = {
        "maximum_unit_attempts": {"plain_llm": 6, "agent": 18},
        "maximum_total_attempts": 24,
        "maximum_total_wall_seconds": 3900,
        "retries": 0,
        "warmups": 0,
        "single_use_authorization_required": True,
    }
    if (
        candidate["proposed_outer_controls_not_enforced_by_identity_alone"] != expected_outer
        or pins["max_total_attempts"] != 24
        or pins["decision_seconds"] != 480
        or pins["deployment"]["request_timeout_seconds"] != 150
        or pins["deployment"]["max_run_attempts"] != 18
        or pins["seeds"] != [[0, 101]]
        or identity["model_trials"] != [0]
    ):
        raise ValueError("candidate differs from the exact bounded public receiving proposal")
    if pins["plain_prompt_sha256"] != prompt_template_sha256():
        raise ValueError("Plain prompt pin changed")
    freeze = json.loads(
        (root / "docs/evidence/a02-episode-authorization-preparation-2026-10-30.json").read_text()
    )["renderer_freeze"]
    actual_renderers = {
        "proposal_template_sha256": renderers.proposal_template_sha256(),
        "repair_template_sha256": renderers.repair_template_sha256(),
        "explanation_template_sha256": explanation_template_sha256(),
    }
    if any(value != freeze[name] for name, value in actual_renderers.items()):
        raise ValueError("Agent renderer differs from reviewed template freeze")
    settings = ModelSettings(
        seeds=tuple(map(tuple, pins["seeds"])),
        decision_seconds=pins["decision_seconds"],
        max_total_attempts=pins["max_total_attempts"],
        deployment=pins["deployment"],
        plain_prompt_sha256=pins["plain_prompt_sha256"],
        agent_renderer_ref=pins["agent_renderer_ref"],
    )
    trained = TrainedSettings(tuple(identity["trained"]["artifacts"].items()))
    config = RunConfig(
        identity["name"],
        tuple(identity["systems"]),
        ((bundle.episode.episode_id, str(bundle_path), lf_sha256(bundle_path)),),
        model_trials=tuple(identity["model_trials"]),
        code_revision=identity["code_revision"],
        lock_sha256=identity["lock_sha256"],
        model=settings,
        trained=trained,
    )
    if (
        config.identity() != identity
        or config.config_hash != candidate["candidate_config_hash"]
        or config.run_id != candidate["candidate_run_id"]
    ):
        raise ValueError("candidate identity/hash/run ID mismatch")
    if set(config.systems) != {
        "greedy_a",
        "greedy_b",
        "decision_tree_c",
        "random_forest_d",
        "plain_llm",
        "agent",
    }:
        raise ValueError("all six systems are required")
    policies = {
        system: TrainedPolicy(load_verified(artifact_paths[system], expected_sha256=digest))
        for system, digest in trained.artifacts
    }
    bound = check_inputs(trained, TrainedInputs(policies), config.systems)
    execution_files = {}
    for path in sorted((root / "dc_sustainability").rglob("*.py")):
        if path.name == "readiness.py" or "visualization" in path.parts:
            continue  # offline checker and viewer are not execution code
        execution_files[path.relative_to(root).as_posix()] = lf_sha256(path)
    return {
        "status": "offline_pins_verified_dispatch_blocked",
        "candidate_run_id": config.run_id,
        "candidate_config_hash": config.config_hash,
        "code_revision": config.code_revision,
        "lock_sha256": config.lock_sha256,
        "renderer_sha256": actual_renderers,
        "verified_artifact_sha256": {
            system: policy.artifact_sha256 for system, policy in bound.policies.items()
        },
        "execution_file_lf_sha256": execution_files,
        "model_requests": 0,
        "held_out_access": False,
        "proposed_bounds": candidate["proposed_outer_controls_not_enforced_by_identity_alone"],
        "remaining_dispatch_gates": [
            "fresh Matty single-use authorization for exact candidate and bounds",
            "fresh runtime/model/template/native-counter and Arc/Vulkan identity checks",
            "reviewed launcher enforces Plain 6/Agent 18/total 24 and 3900-second outer watchdog",
            "stop on unknown/unsaved attempt or failed identity; persist failures; verify owned-process cleanup",
        ],
        "independent_content_acceptance": False,
        "note": "One public development episode/trial; not a held-out freeze or study authorization.",
    }
