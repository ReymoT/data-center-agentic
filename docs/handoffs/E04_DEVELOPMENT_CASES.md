# E04 development cases and draft extraction rule

Task ID / Issue: E04, under Q10 in [issue #22](https://github.com/ReymoT/data-center-agentic/issues/22) (Nisha and Matty accepted full summary-assertion extraction there; Ved's sampling/analysis agreement is still pending and doesn't affect this material).
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); technical contact Ved (vedp3705); Matty as independent second rater (E05).
Active assistant session / instruction version: one Claude Code session for Nisha; instruction deployment 1.18.
Objective: Prepare the development material for the statement-extraction rule: a draft rule with worked examples, at least ten paired development cases, a blank annotation template, and structural checks for annotations.
Base commit / branch / PR: base `f926128` on main; branch `nisha/e04-development-cases`; PR to be opened.

Changed paths:
- `docs/e04/EXTRACTION_RULE.md` (new): draft rule `e04-extraction-draft-0`, covering what counts as a checkable assertion, IDs (Claim records keep their IDs; summary S1..., limitations L1...), duplicates, labels, outputs without an explanation, completeness, metrics and four worked examples that are not rating cases.
- `docs/e04/development_cases.json`, `docs/e04/RATER_PACKET.md`, `docs/e04/annotation_template.json` (new, generated): 11 cases (10 reviewable pairs plus one empty-queue no-op pair) with outputs blinded as X and Y.
- `scripts/build_e04_cases.py` (new): the case definitions and generator; `--check` fails when the committed files are stale.
- `dc_sustainability/evaluation/review.py` (new): `load_cases`, `blank_annotation`, `validate_annotation`, `score_annotation` and `render_packet`.
- `tests/evaluation/test_review.py` (new, 22 tests).
- `docs/handoffs/E04_DEVELOPMENT_CASES.md` (this file).

Cases: all on the hand-example fixture (J1, J2, J3; 40 kW background; 100 kW capacity; forecasts for slots 0–6), covering the Q10 categories: ordinary (2), missing evidence (2: no forecasts, no capacity record), abstention (2), unsupported or contradicted claims (3) and a malformed output (1), plus an empty-queue no-op pair. Every explanation is hand-written. **None is a model output.** The rater packet says so.

Blinding and independence:
- The packet, case file and template contain no system identity or case category, and a test enforces that. X/Y order is fixed by seed 20261022, which is not a Q10 sampling seed.
- `scripts/build_e04_cases.py` holds each case's category and which output stands for which system, so **raters should rate from `RATER_PACKET.md` before opening that script**.
- Nisha (and this session) wrote the cases, so her development ratings are not blind to the case design. Matty's ratings, made from the packet alone, are the independent ones. This limits the pilot only; held-out review uses real saved outputs under the Q10 blinding.
- No labels or ratings are filled in anywhere. The scoring tests use a separate small case built in the test, so the test file doesn't reveal expected labels for the development cases.

Behavior:
- `load_cases` validates every snapshot, state, plan and explanation as F02 records and refuses plans bound to another decision, plans on failed outputs, and outputs other than X/Y.
- `validate_annotation` enforces the rule's structure: every Claim record exactly once with its own text and evidence IDs; S/L IDs unique and well formed; no citations on S/L assertions; supporting IDs among cited IDs; labels from supported/contradicted/unsupported; completeness 0/1 for each of decision, reason, evidence and limitations; no assertions or ratings on a no-op; 0 completeness when there is no explanation. With `complete=False` it accepts the empty template.
- `score_annotation` gives per-output faithfulness, coverage, precision and completeness as defined in MASTER_NISHA E04. Zero denominators stay undefined, except that an output without an explanation has 0 coverage.

Input and output contract/config versions: F02 1.0.0 unchanged. No schema, setting, prompt or other owner's module changed. Draft unit tolerances for kW, g/kWh, slot and h follow the open proposal in issue #24 and are not adopted here.
Artifact locations and checksums: `docs/e04/*`, regenerated exactly by `scripts/build_e04_cases.py` (checked by a test).

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe scripts/build_e04_cases.py --check
.venv\Scripts\python.exe -m pytest tests/evaluation/test_review.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pip check
```

Tests actually run and observed results: Windows, Python 3.12.10, hashed lock. 1008 tests and 19 subtests passed (986 on main before, 22 new). Ruff check/format, compileall, setup validation, pip check and the generator `--check` passed. Case facts (54.5 and 48.4 kg, 22.0/26.4/38.0/16.5 kg per job, 80/110 kW loads, slot timings) are hand-derived from the fixture, matching the existing E01 hand checks.

Limitations and open decisions:
- Draft rule only. It is frozen after both raters have used it on these cases and Q10 is complete. Ved still needs to confirm sampling/analysis and eligibility.
- Synthetic cases can't show how real LLM explanations fail. Real development outputs should be added once an authorized probe or development run exists.
- Agreement statistics (extraction agreement, percent agreement and Cohen's kappa) are not implemented yet. That comes next, once there are two rating files.
- One-sided empty queues can't occur in these pairs, because both outputs share one state.

Receiving owner and consumer check: Matty, to rate the 11 cases from `RATER_PACKET.md` with the template before reading the generator script (E05 development ratings); Ved, to comment on the rule's unit and reference wording alongside issue #24.
Next checkpoint: Nisha's and Matty's independent development ratings, then agreement statistics and adjudication, then freeze the rule with the agreed Q10 record.
