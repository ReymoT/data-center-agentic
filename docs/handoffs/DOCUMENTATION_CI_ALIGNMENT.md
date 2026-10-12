# Documentation alignment and CI maintenance

Owner: Matty Anderson, GitHub MattyAnd. Date: 2026-10-12.

Matty authorized both independent maintenance tasks. This work uses instruction package 1.4 and starts from published commit `eaa397afbcfbe9e5590a0d34fdf4c0a8fe79dd35` on branch `matty/documentation-ci-alignment`. No prerequisite implementation is required for these documentation and CI changes.

## Deliverables

The README, architecture document and generated SVG/PNG now show the exact research question: Does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?

They identify `agent` versus `plain_llm` as the main comparison. Greedy A/B and trained decision tree C/random forest D are additional scheduling references. Workload scheduling remains the experimental setting, with conclusions limited to the evaluated scenarios. The related-system review and architecture rationale remain in the README. Teammate names and roles retain equal formatting, with Matty and Nisha together.

The [offline workflow](../../.github/workflows/bootstrap.yml) replaces checkout v4 and setup-python v5 with [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) and [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0). Their tagged action definitions were checked and both use Node.js 24. The existing workflow uses compatible `pull_request` and main `push` triggers and only the supported `python-version` input. Hosted Windows, Python 3.12, the candidate dependency lock, read-only workflow permissions and offline checks remain the same.

Changed paths: root README; `docs/ARCHITECTURE.md`; architecture README, SVG and PNG; `scripts/render_architecture.py`; `.github/workflows/bootstrap.yml`; `docs/REPOSITORY_SETTINGS.md`; this handoff.

## Reproduction and verification

Run from the repository root in the existing Windows candidate environment:

```powershell
.venv\Scripts\python.exe scripts/render_architecture.py
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts/smoke_dependencies.py
.venv\Scripts\python.exe -m pytest tests/llm/test_provider_mocks.py -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
git diff --check
```

Local verification passed: setup validation of all 50 task records and links; dependency consistency; SHACL/SPARQL, certified tiny MILP, both classifier save/load and bounded LangGraph smoke checks; all 13 offline-provider-mock tests; Ruff lint/format (25 files); compilation; and whitespace checks. The SVG was parsed, the PNG was verified, and the regenerated diagram was visually inspected for readability. Workflow syntax and retained triggers, permissions, Python version and run steps were checked against the previous published workflow.

The first local smoke attempt encountered this desktop sandbox's temporary-directory write restriction. It passed with `TEMP` and `TMP` pointed to the writable workspace `tmp` directory. This is a local runtime setting; no repository or hosted-runner change was needed. Publication evidence will be reported with the resulting commit and workflow run; local checks alone do not establish hosted-action compatibility.

## Limits and receiving work

This is documentation and CI maintenance, not completion of the full F03/F05 implementation tasks or experimental acceptance. Scientific choices Q01-Q13 remain unresolved where already recorded. Shared schemas and upstream simulator, retrieval, calculations and evaluation interfaces are still needed for dependent implementation. The provider and budget remain Q09. No paid calls, scientific runs or teammate-owned implementation were added. Formal review is waived by Matty; applicable technical verification remains required.
