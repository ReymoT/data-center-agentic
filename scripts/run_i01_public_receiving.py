"""One-shot, fail-closed public six-system I01 receiving driver.

This operational wrapper is never imported automatically by the package.  It is pinned to the
fresh single-use authorization, pinned execution code, accepted Ollama 0.40.5 and
the public EP-HAND1 input.  Raw evidence remains under the caller's private output
directory.  The wrapper permits no retry or replacement run.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.agent.renderers import (  # noqa: E402
    proposal_template_sha256,
    render_proposal,
    render_repair,
    repair_template_sha256,
)
from dc_sustainability.evaluation.replay import compare_result, executed_starts, replay_episode  # noqa: E402
from dc_sustainability.evaluation.validator import Q03_OPTION_B  # noqa: E402
from dc_sustainability.experiments import models, runner, trained  # noqa: E402
from dc_sustainability.experiments.config import (  # noqa: E402
    ModelSettings,
    RunConfig,
    TrainedSettings,  # noqa: E402
    lf_sha256,
    load_bundle,
)
from dc_sustainability.explanations.agent import (  # noqa: E402
    explanation_template_sha256,
    render_explanation,
)
from dc_sustainability.llm.plain import prompt_template_sha256  # noqa: E402
from dc_sustainability.llm.provider import Deployment, OllamaProvider  # noqa: E402
from dc_sustainability.llm.rendering_research import render_candidate  # noqa: E402
from dc_sustainability.policies import learned  # noqa: E402
from scripts.a01_igpu_preflight import (  # noqa: E402
    EXPECTED_RUNTIME_SHA256,
    REQUIRED_ENVIRONMENT,
    _port_is_free,
    _read_metadata,
    _wait_until_ready,
    parse_arc_compute,
)
from scripts.inspect_ollama import compare_inventory, inspect  # noqa: E402

HEAD = "40dcd800babf0964e718a8a538548e454d9c0e3c"
AUTHORIZATION = "PENDING_FRESH_MATTY_AUTHORIZATION"
BUNDLE_SHA256 = "8bef36ace7bc4a3cf2debdce81c75edd87e175b20592a520a5449ec1fb0cddd6"
MODEL_DIGEST = "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
TEMPLATE_SHA256 = "ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4"
TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
TOTAL_SECONDS = 3900


def validate_authorization(approval, candidate, readiness_hash, launcher_hash):
    if (
        approval.get("status") != "approved"
        or approval.get("approved_by") != "MattyAnd"
        or approval.get("candidate_config_hash") != candidate["candidate_config_hash"]
        or approval.get("bounds")
        != candidate["proposed_outer_controls_not_enforced_by_identity_alone"]
        or approval.get("readiness_sha256") != readiness_hash
        or approval.get("launcher_sha256") != launcher_hash
        or not isinstance(approval.get("single_use_id"), str)
        or not approval["single_use_id"].strip()
        or not isinstance(approval.get("approval_ref"), str)
        or not approval["approval_ref"].strip()
    ):
        raise RuntimeError("fresh approval must bind candidate, controls, readiness and launcher")
    return approval["approval_ref"]


def consume_authorization(approval, config_hash, directory):
    directory.mkdir(exist_ok=True)
    path = directory / (canonical_sha256(approval["single_use_id"]) + ".json")
    with path.open("x", encoding="utf-8") as receipt:
        json.dump(
            {"single_use_id": approval["single_use_id"], "candidate_config_hash": config_hash},
            receipt,
        )
        receipt.flush()
        os.fsync(receipt.fileno())


def terminate_owned_at_deadline(process, triggered):
    triggered.set()
    if process is not None and process.poll() is None:
        process.terminate()


def verify_units(config, private_runs, statuses, episode):
    rows = []
    for status in statuses:
        folder = private_runs / config.run_id / "units" / status.unit.key
        if (folder / "policy_errors.json").exists():
            raise StopRun("policy errors retained; receiving is not a pass")
        result = s.EpisodeResult.from_json((folder / "result.json").read_text(encoding="utf-8"))
        if (result.system, result.run_id, result.episode_id, result.trial) != (
            status.unit.system,
            config.run_id,
            episode.episode_id,
            status.unit.trial,
        ):
            raise StopRun("saved result identity mismatch")
        records = sorted(
            (
                s.DecisionRecord.from_json(path.read_text(encoding="utf-8"))
                for path in (folder / "traces").glob("*.json")
            ),
            key=lambda record: record.slot,
        )
        if [record.slot for record in records] != list(range(30)):
            raise StopRun("receiving requires all 30 distinct slot records")
        if any(
            (record.system, record.run_id, record.episode_id, record.trial)
            != (status.unit.system, config.run_id, episode.episode_id, status.unit.trial)
            for record in records
        ):
            raise StopRun("saved trace identity mismatch")
        replay = replay_episode(episode, executed_starts(records, episode.episode_id), Q03_OPTION_B)
        if not replay.valid or compare_result(replay, result):
            raise StopRun("independent replay or result comparison failed")
        rows.append(
            {
                "system": status.unit.system,
                "traces": len(records),
                "replay_findings": 0,
                "result_mismatches": 0,
                "recorded_model_calls": sum(record.model_call_count for record in records),
            }
        )
    return rows


class StopRun(BaseException):
    """Abort the one-shot exercise without allowing the harness to repair."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def command(*parts: str) -> str:
    return subprocess.run(parts, check=True, capture_output=True, text=True).stdout.strip()


def save_private_attempt(path: Path, attempt) -> None:
    payload = {
        "client_trace_id": attempt.client_trace_id,
        "system": attempt.system,
        "episode_id": attempt.episode_id,
        "slot": attempt.slot,
        "seed": attempt.seed,
        "started_at_utc": attempt.started_at_utc,
        "latency_ms": attempt.latency_ms,
        "request_json": attempt.request_json,
        "runtime_version": attempt.runtime_version,
        "model_digest": attempt.model_digest,
        "raw_response_base64": base64.b64encode(attempt.raw_response).decode(),
        "http_status": attempt.http_status,
        "provider_request_id": attempt.provider_request_id,
        "prompt_tokens": attempt.prompt_tokens,
        "completion_tokens": attempt.completion_tokens,
        "total_duration_ns": attempt.total_duration_ns,
        "error": attempt.error,
        "uncertain_outcome": attempt.uncertain_outcome,
        "parsed_output": None if attempt.output is None else attempt.output.to_jsonable(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


class StrictProvider(OllamaProvider):
    """Persist and stop on any response/transport failure; never auto-repair it."""

    def __init__(self, *args, emergency_dir: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self._emergency_dir = emergency_dir

    def generate(self, **kwargs):
        if kwargs.get("system") == "plain_llm" and len(self.attempts) >= 6:
            raise StopRun("Plain request ceiling reached before dispatch")
        attempt = super().generate(**kwargs)
        if attempt.error is not None or attempt.uncertain_outcome:
            save_private_attempt(self._emergency_dir / f"{attempt.client_trace_id}.json", attempt)
            raise StopRun(
                f"authorized stop after {attempt.system} slot {attempt.slot}: "
                f"{attempt.error or 'uncertain outcome'}"
            )
        return attempt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--tokenizer-packages", required=True, type=Path)
    parser.add_argument("--accepted-inventory", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--port", type=int, default=11439)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--readiness", required=True, type=Path)
    parser.add_argument("--tree", required=True, type=Path)
    parser.add_argument("--forest", required=True, type=Path)
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()

    runtime = args.runtime.resolve(strict=True)
    model_store = args.models.resolve(strict=True)
    tokenizer_path = args.tokenizer.resolve(strict=True)
    packages = args.tokenizer_packages.resolve(strict=True)
    accepted_inventory = args.accepted_inventory.resolve(strict=True)
    out = args.out.resolve()
    bundle_path = (ROOT / "docs/evidence/ep-hand1-episode-bundle.json").resolve(strict=True)

    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    ready = json.loads(args.readiness.read_text(encoding="utf-8"))
    if ready.get("launcher_lf_sha256") != lf_sha256(Path(__file__)):
        raise RuntimeError("launcher differs from the prepared LF pin")
    if (
        candidate["candidate_config_identity"]["code_revision"] != HEAD
        or ready["candidate_config_hash"] != candidate["candidate_config_hash"]
    ):
        raise RuntimeError("candidate/readiness identities differ")
    command("git", "merge-base", "--is-ancestor", HEAD, "HEAD")
    for rel, digest in ready["execution_file_lf_sha256"].items():
        if lf_sha256(ROOT / rel) != digest:
            raise RuntimeError(f"execution code changed: {rel}")
    authorization_ref = AUTHORIZATION
    if not args.dry_run:
        if args.authorization is None:
            raise RuntimeError("fresh Matty single-use authorization required before startup")
        approval = json.loads(args.authorization.read_text(encoding="utf-8"))
        authorization_ref = validate_authorization(
            approval, candidate, lf_sha256(args.readiness), lf_sha256(Path(__file__))
        )
    if command("git", "status", "--porcelain"):
        raise RuntimeError("tracked repository worktree is not clean")
    if sha256(runtime) != EXPECTED_RUNTIME_SHA256:
        raise RuntimeError("runtime binary differs from accepted Ollama 0.40.5")
    if lf_sha256(bundle_path) != BUNDLE_SHA256:
        raise RuntimeError("EP-HAND1 bundle differs from the authorized LF hash")
    if sha256(tokenizer_path) != TOKENIZER_SHA256:
        raise RuntimeError("tokenizer artifact differs from the validated reference")
    expected_prompts = {
        "plain": "ff5501341f4e9d14fbde2a12bf41f3d13c2be0d67a0f753dd3026f4c4be5586d",
        "proposal": "a2d52e38c42a699533e0608ad2aa39c65ac6871993d5f2ce04492d367e4f6e39",
        "repair": "e928cd5eb9cf3fc1853ffe7332050554ce2e274031ce2c408544eaa3dbf807ba",
        "explanation": "6524939914db0389104e96dc6d55a406234e1ed93624e1a58816ac6735947446",
    }
    actual_prompts = {
        "plain": prompt_template_sha256(),
        "proposal": proposal_template_sha256(),
        "repair": repair_template_sha256(),
        "explanation": explanation_template_sha256(),
    }
    if actual_prompts != expected_prompts:
        raise RuntimeError("a frozen prompt or renderer changed")
    if out.exists():
        raise FileExistsError(f"preserve prior evidence; output already exists: {out}")
    if not _port_is_free(args.port):
        raise RuntimeError("isolated loopback port is already occupied")

    sys.path.insert(0, str(packages))
    import tokenizers  # type: ignore

    if tokenizers.__version__ != "0.23.3":
        raise RuntimeError("isolated tokenizer version differs from 0.23.3")
    tokenizer = tokenizers.Tokenizer.from_str(tokenizer_path.read_text(encoding="utf-8"))
    episode = load_bundle(bundle_path).episode
    lock_path = ROOT / "requirements/requirements-windows-py312.lock.txt"
    deployment = Deployment(
        base_url=f"http://127.0.0.1:{args.port}",
        runtime_version="0.40.5",
        model_digest=MODEL_DIGEST,
        max_run_attempts=18,
        max_response_bytes=2 * 1024 * 1024,
        max_prompt_tokens=16384 - 1536,
        context_policy_ref="qwen3-legacy-template-tokenizers-0.23.3-native-count-validated-a01",
        request_timeout_seconds=150,
    )
    settings = ModelSettings(
        seeds=((0, 101),),
        decision_seconds=480,
        max_total_attempts=24,
        deployment=models.deployment_pins(deployment),
        plain_prompt_sha256=actual_prompts["plain"],
        agent_renderer_ref=(
            "dc_sustainability.agent.renderers:render_proposal,render_repair;"
            "dc_sustainability.explanations.agent:render_explanation"
        ),
    )
    config = RunConfig(
        candidate["candidate_config_identity"]["name"],
        tuple(candidate["candidate_config_identity"]["systems"]),
        ((episode.episode_id, str(bundle_path), BUNDLE_SHA256),),
        model_trials=(0,),
        code_revision=HEAD,
        lock_sha256=lf_sha256(lock_path),
        model=settings,
        trained=TrainedSettings(
            tuple(candidate["candidate_config_identity"]["trained"]["artifacts"].items())
        ),
    )
    expected_outer = {
        "maximum_unit_attempts": {"plain_llm": 6, "agent": 18},
        "maximum_total_attempts": 24,
        "maximum_total_wall_seconds": 3900,
        "retries": 0,
        "warmups": 0,
        "single_use_authorization_required": True,
    }
    if candidate["proposed_outer_controls_not_enforced_by_identity_alone"] != expected_outer:
        raise RuntimeError("outer bounds differ from the reviewed launcher")
    if ready["proposed_bounds"] != expected_outer:
        raise RuntimeError("readiness bounds differ from the reviewed launcher")
    if config.identity() != candidate["candidate_config_identity"]:
        raise RuntimeError("constructed configuration differs from candidate")
    artifact_paths = {"decision_tree_c": args.tree, "random_forest_d": args.forest}
    policies = {
        system: trained.TrainedPolicy(
            learned.load_verified(artifact_paths[system], expected_sha256=digest)
        )
        for system, digest in config.trained.artifacts
    }
    trained_inputs = trained.check_inputs(
        config.trained, trained.TrainedInputs(policies), config.systems
    )
    static = {
        "authorization_ref": authorization_ref,
        "repo_commit": HEAD,
        "checkout_commit": command("git", "rev-parse", "HEAD"),
        "readiness_sha256": lf_sha256(args.readiness),
        "launcher_sha256": lf_sha256(Path(__file__)),
        "text_pin_convention": "LF-normalized readiness and launcher; raw binary/tokenizer hashes",
        "bundle_sha256": BUNDLE_SHA256,
        "config_identity": config.identity(),
        "config_hash": config.config_hash,
        "prompt_hashes": actual_prompts,
        "runtime_executable_sha256": sha256(runtime),
        "tokenizer_sha256": sha256(tokenizer_path),
        "bounds": {
            "plain": 6,
            "agent": 18,
            "combined": 24,
            "request_seconds": 150,
            "agent_decision_seconds": 480,
            "total_seconds": TOTAL_SECONDS,
            "retries": 0,
            "warmups": 0,
        },
    }
    if args.dry_run:
        print(json.dumps({"status": "dry_run_passed", **static}, indent=2))
        return 0

    if args.authorization.resolve() == (out / "authorization-consumed.json"):
        raise RuntimeError("authorization input cannot be its consumption record")
    consumption_root = ROOT.parent / ".i01-consumed-authorizations"
    consume_authorization(approval, config.config_hash, consumption_root)
    out.mkdir(parents=True)
    private_runs = out / "private-runs"
    emergency = out / "emergency-attempts"
    stdout_path, stderr_path = out / "ollama-stdout.log", out / "ollama-stderr.log"
    summary_path, failure_path = out / "sanitized-summary.json", out / "failure.json"
    environment = {k: v for k, v in os.environ.items() if not k.startswith("OLLAMA_")}
    environment.update(REQUIRED_ENVIRONMENT)
    environment["OLLAMA_HOST"] = f"127.0.0.1:{args.port}"
    environment["OLLAMA_MODELS"] = str(model_store)

    process = None
    timer = None
    deadline_triggered = threading.Event()
    inventory_before = inventory_after = compute = None
    providers: list[StrictProvider] = []
    counts: dict[str, int] = {}
    started = time.monotonic()
    cleanup = {"owned_process_exited": False, "listener_remaining": None}

    def stop_at_deadline():
        terminate_owned_at_deadline(process, deadline_triggered)

    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen(
                [str(runtime), "serve"],
                cwd=runtime.parent,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _wait_until_ready(process, args.port)
            # This managed Windows host denies CIM listener-owner enumeration even
            # though the endpoint is reachable.  The port was proven free before
            # Popen; readiness, a live retained process handle and an exclusive-bind
            # refusal together establish that this launch causally reserved it.
            if process.poll() is not None or _port_is_free(args.port):
                raise RuntimeError("started runtime did not retain the isolated port")
            inventory_before = inspect(deployment.base_url)
            compare_inventory(
                json.loads(accepted_inventory.read_text(encoding="utf-8")), inventory_before
            )
            if _read_metadata(args.port, "/api/ps").get("models") != []:
                raise RuntimeError("the isolated server was not unloaded before dispatch")
            show = _read_metadata(args.port, "/api/show")
            template_bytes = show["template"].encode("utf-8")
            if hashlib.sha256(template_bytes).hexdigest() != TEMPLATE_SHA256:
                raise RuntimeError("runtime template differs from the accepted hash")

            def counter(request: dict) -> int:
                prompt = render_candidate(request, template_bytes=template_bytes)
                count = len(tokenizer.encode(prompt, add_special_tokens=False).ids)
                counts[canonical_sha256(request)] = count
                return count

            def validate_plain_gate() -> None:
                nonlocal compute
                plain = providers[1]
                attempts = plain.attempts
                if not 1 <= len(attempts) <= 6:
                    raise StopRun(f"Plain used {len(attempts)} requests; authorized maximum is 6")
                for attempt in attempts:
                    if attempt.error or attempt.uncertain_outcome or attempt.output is None:
                        raise StopRun("Plain did not pass strict response and persistence gates")
                    request = json.loads(attempt.request_json)
                    if counts.get(canonical_sha256(request)) != attempt.prompt_tokens:
                        raise StopRun("Plain offline/native prompt counts differ")
                    envelope = json.loads(attempt.raw_response)
                    if envelope.get("done_reason") != "stop":
                        raise StopRun("Plain response did not finish with done_reason=stop")
                stderr.flush()
                text = stderr_path.read_text(encoding="utf-8", errors="replace")
                compute = parse_arc_compute(text)
                if "load_tensors: offloaded 37/37 layers to GPU" not in text:
                    raise StopRun("Plain did not establish full 37/37 GPU offload")
                loaded = _read_metadata(args.port, "/api/ps").get("models")
                if not isinstance(loaded, list) or len(loaded) != 1:
                    raise StopRun("Plain gate expected exactly one loaded accepted model")
                model = loaded[0]
                if (
                    model.get("digest") != MODEL_DIGEST
                    or model.get("size_vram") != model.get("size")
                    or model.get("context_length") != 16384
                ):
                    raise StopRun("loaded model identity, full offload or context differs")
                compare_inventory(inventory_before, inspect(deployment.base_url))

            def factory():
                if len(providers) == 2:
                    validate_plain_gate()
                provider = StrictProvider(
                    deployment, count_prompt_tokens=counter, emergency_dir=emergency
                )
                providers.append(provider)
                return provider

            model_inputs = models.ModelInputs(
                provider_factory=factory,
                agent_renderers=models.AgentRenderers(
                    proposal=render_proposal, repair=render_repair, explanation=render_explanation
                ),
            )
            remaining = TOTAL_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                raise StopRun("overall deadline exhausted before the first model unit")
            timer = threading.Timer(remaining, stop_at_deadline)
            timer.daemon = True
            timer.start()
            statuses = runner.run(config, private_runs, model_inputs, trained=trained_inputs)
            if deadline_triggered.is_set():
                raise StopRun("paired total deadline exhausted")
            if len(statuses) != 6 or any(s.status != "completed" for s in statuses):
                raise StopRun(f"six units did not all complete: {statuses}")
            unit_replay = verify_units(config, private_runs, statuses, episode)
            attempts = [a for p in providers for a in p.attempts]
            by_system = {
                system: sum(a.system == system for a in attempts)
                for system in ("plain_llm", "agent")
            }
            if by_system["plain_llm"] > 6 or by_system["agent"] > 18 or len(attempts) > 24:
                raise StopRun(f"request cap exceeded: {by_system}, total {len(attempts)}")
            for attempt in attempts:
                request = json.loads(attempt.request_json)
                if counts.get(canonical_sha256(request)) != attempt.prompt_tokens:
                    raise StopRun("offline/native prompt counts differ")
            inventory_after = inspect(deployment.base_url)
            compare_inventory(inventory_before, inventory_after)
            stderr.flush()
            text = stderr_path.read_text(encoding="utf-8", errors="replace")
            compute = parse_arc_compute(text)
            if "load_tensors: offloaded 37/37 layers to GPU" not in text:
                raise StopRun("full 37/37 layer offload was not retained")
            decision_files = list(private_runs.glob("*/units/*/traces/*.json"))
            decisions = [json.loads(path.read_text(encoding="utf-8")) for path in decision_files]
            agent_decisions = [d for d in decisions if d.get("system") == "agent"]
            stage_counts = {
                "repair_present": sum(d.get("repaired") is not None for d in agent_decisions),
                "fallback_present": sum(d.get("fallback") is not None for d in agent_decisions),
                "executed": sum(d.get("final_status") == "executed" for d in agent_decisions),
            }
            attempt_rows = []
            for attempt in attempts:
                request = json.loads(attempt.request_json)
                attempt_rows.append(
                    {
                        "system": attempt.system,
                        "slot": attempt.slot,
                        "request_sha256": hashlib.sha256(attempt.request_json.encode()).hexdigest(),
                        "response_sha256": hashlib.sha256(attempt.raw_response).hexdigest(),
                        "http_status": attempt.http_status,
                        "latency_ms": attempt.latency_ms,
                        "offline_prompt_tokens": counts[canonical_sha256(request)],
                        "native_prompt_tokens": attempt.prompt_tokens,
                        "completion_tokens": attempt.completion_tokens,
                        "error": attempt.error,
                        "uncertain_outcome": attempt.uncertain_outcome,
                    }
                )
            summary = {
                "evidence_kind": "bounded_public_development_receiving_not_study_result",
                **static,
                "status": "passed",
                "elapsed_seconds": time.monotonic() - started,
                "requests": {**by_system, "total": len(attempts)},
                "attempts": attempt_rows,
                "stage_counts": stage_counts,
                "unit_replay": unit_replay,
                "identity_before": inventory_before,
                "identity_after": inventory_after,
                "compute": compute,
                "runtime_stdout_sha256": sha256(stdout_path),
                "runtime_stderr_sha256": sha256(stderr_path),
                "private_run_root_sha256": canonical_sha256(
                    sorted(
                        (str(p.relative_to(private_runs)), sha256(p))
                        for p in private_runs.rglob("*")
                        if p.is_file()
                    )
                ),
                "wrapper_sha256": sha256(Path(__file__)),
                "limitations": [
                    "One public development receiving exercise; not a study or held-out result.",
                    "Repair or fallback is reported only if present in the saved Agent decisions.",
                    "Raw requests, responses, traces and results remain outside Git.",
                ],
            }
    except BaseException as exc:
        failure = {
            **static,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": time.monotonic() - started,
            "deadline_triggered": deadline_triggered.is_set(),
            "wrapper_sha256": sha256(Path(__file__)),
        }
        with failure_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(failure, handle, indent=2, allow_nan=False)
            handle.write("\n")
        print(failure["error"], file=sys.stderr)
        return 2
    finally:
        if timer is not None:
            timer.cancel()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        cleanup["owned_process_exited"] = process is None or process.poll() is not None
        cleanup["listener_remaining"] = not _port_is_free(args.port)
        cleanup["overall_deadline_exceeded"] = time.monotonic() - started > TOTAL_SECONDS
        cleanup_path = out / "cleanup.json" if out.exists() else None
        if cleanup_path is not None:
            with cleanup_path.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(cleanup, handle, indent=2)
                handle.write("\n")
    if (
        not cleanup["owned_process_exited"]
        or cleanup["listener_remaining"]
        or cleanup["overall_deadline_exceeded"]
    ):
        with failure_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(
                {
                    **static,
                    "status": "failed",
                    "error": "cleanup or overall deadline gate failed",
                    "cleanup": cleanup,
                },
                handle,
                indent=2,
            )
        print("exact-process cleanup or overall deadline verification failed", file=sys.stderr)
        return 3
    summary["cleanup"] = cleanup
    summary["elapsed_seconds"] = time.monotonic() - started
    with summary_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"I01 six-system receiving passed; sanitized evidence: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
