# F03, F04 and F05 maintenance handoff

Owner: Matty Anderson (MattyAnd). Technical contacts: Edison for F03, Nisha for F04, Ved for F05.
Instruction deployment: 1.8, 2026-10-12. [Task/defect issue #5](https://github.com/ReymoT/data-center-agentic/issues/5).
Base: 5b8788b50046df2908ebc71dc08c7863423047b2. Branch: matty/f03-f04-f05-maintenance.

Matty explicitly requested the ready work after the dependency audit. Publication to main is authorized without formal review. This handoff reports maintenance evidence; it does not declare a working agent or completed scientific integration.

## Delivered scope and remaining acceptance

| Task | Delivered current maintenance | Remaining task-level requirements |
|---|---|---|
| F03 | All existing offline tests in PR/main CI, clean installation of the existing hashed Windows candidate, dependency/format/lint/compilation checks and setup guidance | Final provider-inclusive lock and actual SDK consumer behavior await recorded Q09 versions/settings; other supported platforms await Q13. Full F03 environment freeze is not complete. |
| F04 | Corrected stale interface/status references across current instructions, plan and readiness; deployment 1.8/changelog; setup checks for aligned versions and canonical contract location; explicit real-implementation evidence rule | Ongoing maintenance and receiving-session refresh/adoption evidence; no teammate session is assumed refreshed. |
| F05 | Plain-language README/architecture with current implementation boundaries, verified offline commands, source-inspection help and updated diagram | Continue updating as modules are implemented; experiment/demo commands and integration evidence still need actual code. |

Task definitions, owners and dependencies are unchanged. Checklist boxes are not an assertion that partial maintenance has completed the whole project.

## Preserved teammate work and contract migration

F02 contract 1.0.0, schemas, tests and all 17 examples remain unchanged. Reimo's D01 loader/tests/manifests remain unchanged. All upstream commits remain in history.

Ved's implemented specification was copied intact to the established `docs/INTERFACES.md` location. The superseded draft is recoverable in Git history. `docs/Interfaces F02` is a short compatibility pointer, preserving older links without another editable contract. This moves documentation, not data formats or scientific settings.

The preserved specification's checked-out Windows SHA-256 was `739380d3109a7a1398b00edbfe2765cf395e517369b1135f7cbe581cc82fd199` before and immediately after relocation. File-byte hashes can differ across Git line-ending conversions. The canonical specification's Git blob matches the original exactly: `41ab733816ac171fa283f75c5252c658025c124d`.

Unchanged checked-out Windows candidate lock SHA-256: `ea912edd99927b6bf9d1b9623f5c61d5aa2378e149a929e14ea22b6673254d25`. Schema version and instruction deployment version remain separate.

## Commands actually run and evidence

A new isolated environment was created under the workspace's tmp directory using 64-bit CPython 3.12.14. The existing lock was installed with `--require-hashes`; no global packages or locks were changed. Initial ensurepip bootstrapping hit a sandbox SSL-proxy permission error; the same isolated bootstrap/install succeeded with approved execution. TEMP/TMP were set to the writable workspace tmp directory.

The clean interpreter ran:

```powershell
python -m pip check
python scripts/smoke_dependencies.py
python -m pytest tests -q
python -m ruff check dc_sustainability scripts tests
python -m ruff format --check dc_sustainability scripts tests
python -m compileall -q dc_sustainability scripts tests
python -m dc_sustainability.data.carbon_source --help
```

Observed: no broken dependencies; 16 direct imports passed; SHACL valid/invalid cases and SPARQL passed; the tiny integer program was certified; both classifiers fit/save/load with matching predictions; the bounded LangGraph route passed without a model call. Pytest: 193 tests and 19 subtests passed. Ruff lint/format and compilation passed; the source command displayed real help. These are dependency and implemented-component checks, not project algorithm or live-model acceptance.

Setup/link/policy/version checks passed. In an isolated repository-file copy, the validator accepted the unmodified state and correctly rejected a mismatched role deployment, contract/schema version mismatch and replacement of the compatibility pointer with competing content. The actual checkout was untouched by those rejection checks.

Ignore-pattern checks confirmed exclusion of local environment secrets, credentials, private data, generated model/run artifacts and virtual environments. SVG/PNG were regenerated together; the PNG was visually inspected for legibility and the implementation-status footer. Whitespace checks passed. Publication evidence is recorded in issue #5; GitHub CI must pass for the exact published commit before this maintenance is marked complete there.

## Limits and next handoff

The seven-file merge and instruction-authority rules are unchanged. Q01-Q13 remain open where unresolved; Q09 retains local Ollama/Qwen3 8B Q4_K_M and temperature 0.2 without inventing missing pins.

GPU/VRAM, runtime/SDK/model-digest pins, exact matched trial seeds, agreed output projections, context/warm-up/accounting rules and measured resource/run authorization remain required before live readiness. Source pollutant/interval/license and consumer-adoption blockers remain. No new mock, production stub, fabricated response/trace/result, provider adapter, inference, experiment or shared-schema change was added.

Refresh note for affected sessions: fetch main while preserving local work; read deployment 1.8, canonical INTERFACES, the role master and this handoff before resuming. This is a note for the human to relay; no direct teammate message or session-adoption confirmation is claimed.
