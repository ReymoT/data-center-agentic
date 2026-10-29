# E02-a deterministic experiment runner

Task ID / Issue: E02, [issue #18](https://github.com/ReymoT/data-center-agentic/issues/18) (registry, resumable runner and CLI). First increment of the plan posted in #18.
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); Matty for the controller/trace boundary; Edison for the A/B entry point; Reimo for episode materialization (#102).
Objective: run whole episodes for the deterministic systems through the real production path, with frozen configs, stable IDs, atomic results and safe resume. No model calls.
Base commit / branch: base `989ebaf` on main; branch `nisha/e02a-deterministic-runner`.

Changed paths:
- `dc_sustainability/experiments/registry.py` (new): all six systems; Greedy A and B available, the others registered with the reason they are not yet available.
- `dc_sustainability/experiments/config.py` (new): episode bundles, `RunConfig` with config hash and run ID, stable decision IDs, atomic exclusive file publishing.
- `dc_sustainability/experiments/runner.py` (new): the episode loop, per-unit resume and status.
- `dc_sustainability/experiments/__main__.py` (new): `run` and `status` commands.
- `tests/experiments/test_runner.py` (new, 14 tests).
- `docs/handoffs/E02A_RUNNER.md` (this file).

What it does:
- **Unit** = system × episode × trial. Model systems repeat over `model_trials` (default 0, 1, 2); deterministic and trained systems run once, with `trial` None.
- **Episode bundle** (private runner input): the F02 `PrivateEpisode`, its explicit slot-0 UTC time, and the forecasts issued at each slot. Only the simulator and controller receive it. A bundle with no forecasts means forecasts are unavailable, never converted from actuals.
- **Run identity**: `RunConfig` (name, systems, episode IDs with LF bundle SHA256, model trials, code revision with a dirty marker, dependency-lock SHA256) gives a config hash; run ID `RUN-` + 12 hex. The run directory's `manifest.json` is published exclusively and a different config is refused. A bundle that changed after the config was made is refused.
- **Decision IDs**: `DEC-{config hash 10}.{system code}.{episode ID}[.t{trial}].s{slot}`, within the F02 `DecisionId` pattern.
- **Episode loop**: reset the simulator with the bundle's forecasts. For slots 0–23: the policy gets only `VisibleState` and the K02 context (`knowledge.retrieve`); Greedy B's trusted decision time is slot-0 UTC plus the slot index; the output goes through `execute_policy_output`. A policy exception becomes a failed `PolicyOutput` (recorded, advances once) and is listed in `policy_errors.json`. For slots 24–29: a `DecisionRecord` with no selected stage, `final_status` "blocked" and no calls takes the controller's refusal path. After slot 30 the `EpisodeResult` (with the unit's trial) is published atomically.
- **Resume per unit**: a unit with `result.json` is completed and skipped; one with `failed.json` stays failed; one with traces but no result is `needs_reconciliation` (also when the controller raises `IndeterminateExecution`). None is re-run or replaced. Unavailable systems are refused before anything is written.
- **CLI**: `python -m dc_sustainability.experiments run|status --config RUN.json --out DIR`; exit 0 only when every unit is completed.

Tests (real simulator, checker, controller and trace store): 30-slot episodes for A and B with no model calls and blocked completion slots; E01's independent replay of the saved traces agrees with the `EpisodeResult`; B without forecasts keeps its identity and falls back to checked A; a rerun leaves completed files untouched; a leftover trace gives `needs_reconciliation` with nothing added; a failed unit stays failed; a policy exception is a recorded failed decision; an unavailable system is refused before writing; a tampered manifest and a changed bundle are refused; IDs are stable, distinct and F02-valid; the policy receives only `VisibleState` and `Context`; bundle round trip; CLI run and status.
- Mutation check: four deliberate bugs each made tests fail, and the code was restored: re-running every unit, no reconciliation check, deciding in completion slots, not retaining failures.

Input and output contract/config versions: F02 1.0.0, unchanged; run config `e02-run-config-v1`.
Artifact locations and checksums: none committed; runs write under the `--out` directory.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/experiments -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
```

Tests actually run and observed results: Windows 11, Python 3.12.10, hashed lock. Full suite 1,521 tests and 19 subtests passed; Ruff check/format, setup validation and pip check passed.

Defaults to confirm (asked in #18):
1. **Completion slots**: the no-stage, "blocked", no-call `DecisionRecord` through `execute_step` (Matty).
2. **Forecasts**: from the episode bundle's `forecasts_by_slot`; the D04 materialization (#102) or a K/D helper should write bundles in this format.
3. **Decision time**: Greedy B uses bundle slot-0 UTC plus the slot index.

Limitations and next steps:
- No materialized development episodes exist yet, so runs use test fixtures; no study result is claimed.
- Resume is per unit, not mid-episode: an interrupted unit needs reconciliation rather than a partial restart.
- E02-b adds the Plain and Agent adapters (attempt ledger, `unknown` for uncertain sent requests, the bounds agreed in #6) after A01 acceptance and run authorization; E02-c adds C and D after P04; the 300-run matrix config follows for the I02 freeze.

Receiving owner and consumer check: Matty, for the controller/trace use and the three defaults.
