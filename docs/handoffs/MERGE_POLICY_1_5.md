# Instruction deployment 1.5 handoff

Owner: Matty Anderson (MattyAnd). Date: 2026-10-12. Base: `6df7d009af188c667f6ce2010678c8425736727a`. Branch: `matty/merge-policy-consistency`.

Matty explicitly fixed the merge rule and authorized sending Nisha his open-source LLM requirement and Ollama recommendation. The request is [issue #2](https://github.com/ReymoT/data-center-agentic/issues/2), assigned to her verified account `nkolekar-nk`. Delivery means the GitHub issue was created; no reply or agreement is claimed.

AGENTS.md, the new PROJECT_MASTER.md and all five role files contain the identical rule: a PR may merge once its checks pass, teammate review is welcome but optional, and shared-format or settings changes need affected teammates' agreement first. Numbered files 00-04 and the related current workflow records are aligned and versioned 1.5. Setup validation now checks all seven required copies. Historical handoffs retain their original deployment versions.

Matty's earlier direct document publication authorization remains applicable. This change updates instructions, not GitHub access/protection, schemas, shared runtime settings or task allocations. Q09 records the open-source requirement and Ollama recommendation but leaves the exact model/license, runtime adoption, hardware, SDK, settings and resource budget open for agreement. Independent scientific evaluation remains required.

Reproduce verification from the existing candidate environment:

```powershell
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pytest tests/llm/test_provider_mocks.py -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
git diff --check
```

Local checks passed: setup validation of 50 task records, matching role inventories, acyclic dependencies, links and the seven identical merge-rule copies; all 13 offline provider-mock tests; Ruff lint/format (25 files); compilation; and whitespace validation. Current-commit publication CI must also pass before completion. The resulting commit and CI run will be reported with publication. Nisha's recommendation remains pending; no waiting is required to publish this explicit manager instruction.
