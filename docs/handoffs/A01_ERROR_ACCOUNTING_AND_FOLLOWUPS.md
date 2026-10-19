# A01 failed-response accounting and decision follow-ups

Owner: Matty Anderson (MattyAnd). Date: October 19, 2026.
Base: `5a75b50f83decc2cc781b3e4b46ecddfc23ed7fc`.
Branch: `matty/a01-accounting-and-decision-followups`.
Instruction deployment remains 1.13; F02 remains 1.0.0.

Matty explicitly requested the independently identified A01 bug fix, a Q11/Q12
follow-up if none existed, and recommendations for Q10 and Q13. This resumes only
the bounded bug fix within A01. The remaining Q09 deployment/inference work still
waits for affected-member agreement and the documented technical inputs.

## A01 fix

An excessively nested JSON response previously raised `RecursionError` after the
chat request had been sent. The per-decision reservation was consumed, but control
left before the `Attempt` was appended. The run cap uses the recorded attempts,
so another episode/slot could bypass that cap after such a failure.

The response-error handler now catches `RecursionError` alongside the existing
parse/validation failures. It records the failed spent attempt with the complete
received bytes, HTTP status and error, keeps unavailable usage as `None`, and
returns no parsed proposal. Both the existing run cap and per-decision caps remain
effective. No retry, response repair, approval or extra model call is added.

Six regression cases use the real loopback HTTP transport with explicitly synthetic
deeply nested arrays/objects. They cover both agent and plain systems, retained raw
evidence, a run cap enforced on a different valid visible state, and the existing
three-agent/one-plain per-decision caps. They are transport/accounting evidence,
not Ollama inference or integrated system acceptance.

```powershell
.venv\Scripts\python.exe -m pytest tests/llm/test_ollama_provider.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
git diff --check
```

The focused transport suite passed 45 tests after the fix. The full local suite
passed 816 tests and 19 subtests. Ruff lint/format (49 Python files), compilation,
dependency consistency, setup/version/link/policy checks and whitespace passed.
Hosted publication results are recorded in [A01 issue #6](https://github.com/ReymoT/data-center-agentic/issues/6)
after verification. Use writable workspace TEMP/TMP for this Windows checkout;
loopback tests need the environment's scoped network permission. Ordinary CI stays
offline and uses its local synthetic server.

## Requested follow-ups

All existing Issue bodies/comments were checked for Q11/Q12 follow-ups; none was
found. The published manager/merge/authority rules were already settled, so the
new request concerns only remaining coordination and task-allocation choices.

| Request | Published record | Acceptance boundary |
|---|---|---|
| Q11/Q12 | [Issue #21](https://github.com/ReymoT/data-center-agentic/issues/21), owned by Matty and addressed to all four teammates | Proposes Matty as integration coordinator/summary publisher, Nisha as backup if she agrees, and confirmation of the existing 50-task allocations. No role is transferred or summary template activated by this request. |
| Q10 | [Issue #22](https://github.com/ReymoT/data-center-agentic/issues/22), owned by Nisha with Matty/Ved participating | Gives concrete recommendations for blinded review, sampling and paired analysis. They are project-specific proposals requiring agreement and a later frozen record, not a selected protocol or generated labels. |
| Q13 | [Recommendation in existing issue #16](https://github.com/ReymoT/data-center-agentic/issues/16#issuecomment-6278023544) | Recommends environment/reproduction targets, a code-only license, access/retention and submission packaging. Course facts, contributor rights and affected-member agreement remain prerequisites. No license file, platform lock, permissions or retention setting is applied. |

The proposals and their rationale live in those Issues until accepted. Primary
statistical/licensing references are linked there; they do not establish this
project's sampling size, course requirements or third-party rights.

## Preserved scope

No shared format, generation setting, accepted seed, budget ceiling, prompt,
dependency lock, source data, instruction policy or task assignment changed.
The decision follow-ups are sent under Matty's explicit request and do not create
general messaging authority or an automatic monitoring service. Presentation
preparation and the separate Frontier D02 access follow-up remain outside this work.
The Q01-Q04 urgent message is still Matty's unsent draft.

Full A01 and Q09 are not Done. Q10-Q13 choices remain open pending the required
facts and agreements; absence of a reply is not acceptance. Final main/CI and
task-branch cleanup evidence belongs in issue #6 after publication.
