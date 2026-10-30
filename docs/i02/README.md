# I02 freeze manifest (pre-freeze checklist)

Task: I02. Owner: Nisha. Receiving owner: Matty. Target freeze: **November 13, 2026** ([PROJECT_PLAN](../PROJECT_PLAN.md), MASTER_NISHA item 7).

[`freeze-manifest.json`](freeze-manifest.json) lists everything the held-out runs must freeze: code, locks, fixtures, ontology, models/features, prompts/provider, seeds, references and scoring/rubric. Each item has an owner, a status (`pending`, `blocked` or `frozen`) and, when blocked, the reason. **It is a checklist, not a freeze.** No item is frozen yet, and nothing here authorizes a run.

The manifest also states the planned run matrix, and the validator checks its arithmetic:
- 30 episodes: 24 core (6 dates × 4 scenarios) plus 6 missing-forecast;
- 1 trial each for greedy A, greedy B, decision tree C and random forest D, and 3 each for Plain and Agent: **300 runs**;
- at most 2,160 Plain and 6,480 Agent calls (24 decision slots, with 1 and 3 calls per decision).

A smaller matrix can't pass silently: any reduction must be matched across systems and frozen before execution.

## Commands

```powershell
.venv\Scripts\python.exe scripts/validate_i02_freeze_manifest.py docs/i02/freeze-manifest.json
.venv\Scripts\python.exe scripts/validate_i02_freeze_manifest.py docs/i02/freeze-manifest.json --require-ready
```

The first checks integrity. The second fails, naming each unfrozen item and its blocker, until every item is frozen and the freeze commit is recorded.

## Freezing an item

An item is frozen by its owner's evidence:
- a file artifact (a model, an episode set or an outside file) gets its own SHA256;
- an in-repo path can instead be pinned by the freeze commit.

Status and blockers are as of the `status_as_of` date. Each owner should correct their own rows.
