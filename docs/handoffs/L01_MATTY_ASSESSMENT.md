# Matty's L01 preparation assessment and candidate fix

Date: 2026-10-18. Assessor/agent-adapter contact: Matty Anderson (MattyAnd).
L01 implementation owner: Nisha Mahadev Kolekar (nkolekar-nk); context contact: Ved.
Matty authorized completion of the PR assessment and coordination actions. Nisha's
published branch and main remain untouched by this candidate branch.

Reviewed [PR #11](https://github.com/ReymoT/data-center-agentic/pull/11) at exact head
`93529bf1b113051afe7764c141e78b4c3862cf38`, based on main `0cc1f5e`.
Candidate branch: `matty/l01-preparation-assessment`, with that PR head as parent.
Instruction deployment remains 1.10; F02 remains 1.0.0. No master, contract, prompt,
provider, generation setting, dependency lock or scientific decision changes here.

## Assessment outcome

The ordinary path uses the existing shared provider and settings, preserves the
original response and performs no tool call, checker feedback, repair, retry or A
fallback. Completion slots are blocked. Synthetic HTTP tests confirm these claims;
they do not establish inference, K02 adoption or an integrated development episode.

Matty accepts reusing `prompts/shared/task_rules.md` and
`prompts/shared/explanation_rules.md` as common development-draft instructions for
the future agent. Both LLM paths should receive the same scheduling, evidence and
explanation rules; plain one-response instructions and agent routing stay separate.
No agent implementation is delivered by that choice. Q01-Q04 still control the
unresolved wording before freeze. A draft prompt is not an accepted scientific rule.
Ved must still confirm the temporary ContextContent JSON and later K02 equivalence.

One substantive finding was reproduced: the set-based context/state comparison did
not revalidate the F02 Context. `model_copy` could replace a capacity constraint
while keeping the old content hash, or duplicate waiting jobs while recomputing the
hash. The original F02 validators reject both inputs, but the reviewed plain path
sent one synthetic chat request and returned `ok` for each. The first case recorded
a context hash that did not match the actual prompt facts. This compromises evidence
integrity/comparability; it does not establish a successful runtime execution.

The candidate fix revalidates both existing F02 state/context records strictly
before rendering, recording the request or dispatching. It changes no shared format
or agreed policy behavior. The two regression cases reject both bad contexts before
any HTTP request or provider attempt. Existing valid behavior remains covered.

## Verification

- Original PR: 758 tests and 19 subtests passed locally; lint/format (43 Python files),
  compile, setup and pip consistency passed. Its already-completed hosted CI is
  [39007613899](https://github.com/ReymoT/data-center-agentic/actions/runs/39007613899).
- Both new regression cases failed on the unmodified PR (`DID NOT RAISE ValueError`),
  agreeing with separate synthetic HTTP probes. No real model call occurred.
- Candidate: 760 tests and 19 subtests passed locally; lint/format (44 Python files),
  compile, setup and whitespace passed. The only subsequent source change sorted
  imports in the regression file; lint/format/compile/setup were rechecked.
- Windows CPython 3.12.14, existing hashed candidate environment. No installation,
  driver/service change, source download, live-model or held-out run.

Run from this candidate checkout with the existing project environment:

```powershell
python -m pytest tests -q
python -m ruff check dc_sustainability scripts tests
python -m ruff format --check dc_sustainability scripts tests
python -m compileall -q dc_sustainability scripts tests
python scripts/validate_setup.py
python -m pip check
git diff --check
```

The candidate is published for Nisha to incorporate into PR #11 and verify through
that PR's CI. The original PR's green CI belongs to its original SHA and is not
candidate hosted-CI evidence. This branch is not a full L01 or main-merge claim.
No required formal teammate-review gate is introduced.

## Coordination completed and outstanding

[L01 issue #12](https://github.com/ReymoT/data-center-agentic/issues/12) is assigned
to Nisha as requested. [Q01-Q04 follow-up](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6257249665)
asks all affected owners for explicit agreement and names critical S01, K01/K02,
P01/P02 and E01 work. [D06 source follow-up #13](https://github.com/ReymoT/data-center-agentic/issues/13)
is assigned to Ved, with Reimo contacted separately on source evidence/access.
The October 16 target being past is not proof of source failure or permission to
invent validation results; the owner must provide evidence or record the proposal's
applicable synthetic fallback and narrower conclusions.

Full L01, A01/A03, A02/A04 and integration remain dependent on the documented pins,
context/token handling, Q01-Q04 agreement, source evidence and real consumer/module
handoffs. Nisha owns fix adoption and L01 delivery; Ved owns context confirmation and
D06 evidence. Sending follow-ups is not a teammate response or accepted decision.
