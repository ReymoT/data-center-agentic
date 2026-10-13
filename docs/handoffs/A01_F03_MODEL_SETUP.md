# A01/F03 model setup handoff

Owner: Matty Anderson (MattyAnd). Technical contacts: Nisha for A01, Edison for F03;
Ved remains the shared-contract contact. Date: 2026-10-12. Instruction deployment 1.9.
Base: 883a809. Branch: matty/a01-f03-model-setup. User authorization: “get done A01/F03,”
following the independent model-installation and identity-recording recommendation.

Delivered: accepted `qwen3:8b` installed locally, full API digest/quantization/license
verified, all six stored blob hashes/sizes independently checked, reproducible
read-only inventory tool and public metadata records. [Setup instructions](../OLLAMA_SETUP.md)
describe the actual installation and remaining inputs. Existing model and teammate
code/history/contracts/locks are preserved. Weights remain outside the Git repository.

The local inventory was collected and then compared against an independent fresh
read. Both matched. `ollama ps` was empty after inspection; zero model calls were made.
No service environment, driver, SDK, seed, shared output projection or scientific
decision was changed. Installation is not an experiment freeze or live-inference test.

Verification commands:

```powershell
ollama pull qwen3:8b
ollama --version
ollama list
.venv\Scripts\python.exe scripts/inspect_ollama.py --compare docs/evidence/ollama-qwen3-8b.json
ollama ps
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe -m pip check
git diff --check
```

Installed runtime 0.40.3; full API digest
`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
[Inventory](../evidence/ollama-qwen3-8b.json) and [blob evidence](../evidence/ollama-qwen3-storage.json)
retain precise values and separate original/API manifest identity from the local wrapper.
Offline negative tests use labeled synthetic metadata; they do not claim model calls.
Local verification passed 264 tests and 19 subtests, lint, formatting (36 Python
files), compilation, pip consistency, setup validation and whitespace checks. Six
new inventory tests cover identity, metadata extensions, missing models, incomplete
digests, changed quantization, unverified licenses and mismatched saved artifacts.
Hosted CI and the published commit are recorded in [A01 issue #6](https://github.com/ReymoT/data-center-agentic/issues/6)
after publication; offline CI does not install or call the model.

The independent setup deliverable is complete after publication checks. Full A01/F03
acceptance still needs the Q09/Q13 deployment, context, projection, seed, measured
resource and environment/integration evidence; task checklist boxes remain pending.
No teammate message or consumer adoption is claimed by publishing this handoff.
