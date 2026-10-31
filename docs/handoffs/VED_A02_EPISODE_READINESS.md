# Ved A02 Episode Readiness Handoff

**Issue:** #18 — A02 model-driven Agent episode readiness
**Author:** Ved
**Date:** 2026-10-30
**Branch:** `ved/issue-18-agent-episode`
**Base commit:** `e69f0a8dbd1cf21f8efd9a0fdec7641e63aee6be` (origin/main)
**Status:** Partially ready; live dispatch not authorized

---

## 1. Task

Determine whether the project can safely execute one genuine model-driven Agent development episode through the actual production path, prepare all available local prerequisites, document the exact remaining blockers, and report one of Ready / Partially ready / Blocked.

**Constraint:** No model request was sent during this task. Ownership boundaries were respected: A02 remains Matty's, L02/E02 remain Nisha's.

---

## 2. Verdict

**Partially ready.**

The code path from `RunConfig` → `runner.run(..., models=ModelInputs(...))` → `agent_step` → `AgentHarness.run_decision` → `ExecutionController.execute_step` is implemented and passes offline tests with synthetic HTTP. A public hand-example episode (`EP-HAND1`) is available for a paired Plain/Agent development receiving exercise, so D04 materialization is not a prerequisite for that bounded exercise. It remains a prerequisite for the later study run.

Two A02-owned/governance inputs still block live dispatch:

1. **No reviewed production repair or explanation renderers.** Only `dc_sustainability/agent/renderers.py::render_proposal` exists. The harness accepts `repair_messages` and `explanation_messages`, but there are no committed, reviewed prompt files or renderers for those stages.
2. **No A02-specific bounded episode authorization.** A01's two-call transport authorization was consumed and does not authorize an Agent episode.

The correct next step is offline renderer and authorization preparation. No model request should be sent until those artifacts, exact episode identity, limits and runtime identity are frozen.

---

## 3. What is implemented and verified

### 3.1 Code path

| Component | File | Role | Status |
|-----------|------|------|--------|
| F02 schemas | `dc_sustainability/schemas.py` | Strict records, version 1.0.0 | Implemented |
| A02 harness | `dc_sustainability/agent/harness.py` | LangGraph orchestration with proposal/repair/fallback/explain stages | Implemented |
| A02 proposal renderer | `dc_sustainability/agent/renderers.py` | `render_proposal` + template hash | Implemented |
| A01 provider | `dc_sustainability/llm/provider.py` | Ollama REST adapter, attempt ledger, pin verification | Implemented |
| E02 model units | `dc_sustainability/experiments/models.py` | `ModelInputs`, `AgentRenderers`, `new_harness`, `agent_step`, `plain_step` | Implemented |
| E02 runner | `dc_sustainability/experiments/runner.py` | Episode loop, unit execution, resume, budget admission | Implemented |
| E02 registry | `dc_sustainability/experiments/registry.py` | Six-system registry; `agent`/`plain_llm` require explicit model inputs | Implemented |
| E02 config | `dc_sustainability/experiments/config.py` | `RunConfig`, `EpisodeBundle`, `ModelSettings` | Implemented |
| A03 checker | `dc_sustainability/verification/checker.py` | Production schedule checks | Implemented |
| A04 controller | `dc_sustainability/runtime/controller.py` | Execution gate and trace writer | Implemented |
| K02 retrieval | `dc_sustainability/knowledge/retrieval.py` | SPARQL/graph context projection | Implemented |
| S01 simulator | `dc_sustainability/simulator/core.py` | Deterministic episode simulator | Implemented |

### 3.2 Offline tests

All tests pass on Python 3.12.15 after installing `requirements/requirements-core.in`:

```text
$ /usr/bin/python3.12 -m pytest tests/agent -q
24 passed

$ /usr/bin/python3.12 -m pytest tests/experiments -q
45 passed

$ /usr/bin/python3.12 -m pytest tests/runtime tests/verification -q
110 passed

$ /usr/bin/python3.12 -m pytest tests/knowledge tests/contracts -q
243 passed

$ /usr/bin/python3.12 -m pytest -q
1604 passed, 19 subtests passed
```

`git diff --check` reports no whitespace errors.

### 3.3 A01 bounded validation

`docs/handoffs/A01_BOUNDED_PAIRED_VALIDATION_2026-10-30.md` documents a two-request paired validation against Ollama 0.40.5 / qwen3:8b Q4_K_M. That authorization was consumed for A01 and is **not** authorization for an A02 episode. It proves the provider works, but an A02 episode needs its own run authorization.

---

## 4. What is missing for a genuine A02 episode

### 4.1 Materialized study episode bundles

- **Owner:** Reimo (D03/D04 data custody).
- **Evidence:** `data/manifests/d04-development-20261028-v1/manifest.json` contains 40 allocation records, but:
  - `"episode_contents_generated": false`
  - every `"episode_content_sha256": null`
- **Impact:** The planned 40-episode development/study workload cannot run yet. This does not block a bounded receiving exercise on the repository's public `EP-HAND1` fixture.
- **Action needed:** Generate and commit (or place in evaluator custody outside Git) an approved D03/D04 development episode bundle with `PrivateEpisode`, `slot0_utc`, and per-slot `CarbonForecast` facts, then update the run config to reference it.

### 4.2 Reviewed repair and explanation renderers

- **Owner:** Matty (A02).
- **Evidence:** `dc_sustainability/agent/renderers.py` exports only `render_proposal`. The harness accepts `repair_messages` and `explanation_messages`, and `AgentRenderers` has `repair` and `explanation` fields, but no production implementations exist. Tests in `tests/agent/test_harness.py` pass only by supplying synthetic test fixtures.
- **Impact:** A real Agent episode is expected to traverse propose→verify→repair→verify→fallback→verify→explain when the initial proposal fails. Without reviewed renderers, the harness would either fail-closed after a failed proposal or skip explanation.
- **Action needed:** Add reviewed prompt files under `prompts/agent/` and renderers for `repair` and `explanation`, then record the renderer reference in `ModelSettings.agent_renderer_ref`.

### 4.3 A02 run authorization

- **Owner:** Reimo / project governance.
- **Evidence:** `registry.py` marks `agent` as unavailable by default: "needs explicit model inputs: accepted A01 and a run authorization." `models.py::check_inputs` enforces that `agent` requires `AgentRenderers`.
- **Impact:** Even with a bundle and renderers, a separate run authorization is required before the first model dispatch.
- **Action needed:** Obtain explicit A02 run authorization.

### 4.4 Accepted Ollama deployment identity

- **Owner:** Matty / runtime ops.
- **Evidence:** `docs/decisions/Q09_OLLAMA_QWEN3.md` accepts Ollama 0.40.5 and qwen3:8b Q4_K_M, and A01's paired validation recorded an isolated host with that identity. `OllamaProvider._verify_pins` rejects a runtime/model digest mismatch.
- **Impact:** A02 must target the accepted isolated host and re-check its exact identity before dispatch; a different local 0.40.11 installation is not evidence that the accepted pin must change.
- **Action needed:** Record the accepted host and verified model/runtime identity in the A02 authorization manifest. Do not change the accepted pin merely to match another installation.

---

## 5. What was prepared locally

1. Created a clean worktree/branch from `origin/main`.
2. Installed core dependencies from `requirements/requirements-core.in` into the user Python 3.12 environment.
3. Verified the entire test suite passes offline.
4. Confirmed `git diff --check` is clean.
5. Audited the D04 manifest and confirmed no study episode contents are materialized; the public `EP-HAND1` fixture remains available for bounded receiving work.
6. Audited `dc_sustainability/agent/renderers.py` and confirmed only the proposal renderer exists.
7. Did **not** create substitute private data or unreviewed prompts.
8. Did **not** send any model request.

---

## 6. How to reproduce the readiness check

```bash
cd /home/vpatil14/src/ved-issue-18-agent-episode
/usr/bin/python3.12 -m pytest -q
git diff --check
/usr/bin/python3.12 - <<'PY'
import json
from pathlib import Path
manifest = Path("data/manifests/d04-development-20261028-v1/manifest.json")
data = json.loads(manifest.read_text())
print("episode_contents_generated:", data["episode_contents_generated"])
print("null content hashes:", sum(1 for r in data["records"] if r["episode_content_sha256"] is None))
print("total records:", len(data["records"]))
PY
```

Expected output:

```text
episode_contents_generated: false
null content hashes: 40
total records: 40
```

---

## 7. Risks if forced to run now

- **Unfrozen episode input:** dispatching before the public receiving episode is packaged and hashed in the authorization manifest would make the result non-reproducible.
- **Unreviewed prompts:** Supplying ad-hoc repair/explanation renderers would bypass Matty's A02 ownership and could produce unbounded or unsafe model outputs.
- **No authorization:** Running without A02 authorization violates the project's bounded-validation policy.
- **Deployment pin mismatch:** Any host other than the accepted isolated deployment, or any changed runtime/model digest, will fail `_verify_pins` and must not be substituted silently.

---

## 8. Recommended next steps

1. **Matty:** Prepare reviewed repair/explanation renderers and the A02 bounded authorization manifest offline.
2. **Nisha and Matty:** Align the proposed L01 and A02 receiving exercises on the same public `EP-HAND1` episode and shared settings.
3. **Governance:** Issue an explicit A02 run authorization only after exact hashes, limits and runtime identity are frozen.
4. **Runtime ops:** Reuse and re-verify the accepted isolated Ollama 0.40.5 / qwen3:8b Q4_K_M deployment.
5. **Reimo:** Materialize approved D03/D04 development episode bundles for the later study run.
6. **Ved (follow-up):** Re-run downstream acceptance after the production renderers and bounded receiving result are committed.

---

## 9. Sign-off

- No code changes were made to production modules.
- No private data was invented.
- No model request was sent.
- A02 ownership remains with Matty; L02/E02 ownership remains with Nisha.

**Readiness:** Partially ready; offline preparation can proceed, but live dispatch remains blocked pending frozen renderers and explicit authorization.
