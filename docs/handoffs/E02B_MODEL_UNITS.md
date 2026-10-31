# E02-b model units in the runner (offline preparation)

Task ID / Issue: E02, [issue #18](https://github.com/ReymoT/data-center-agentic/issues/18) (Plain and Agent adapters). Second increment of the plan posted in #18, after E02-a (#110).
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); Matty for the A01 provider, A02 harness and controller boundaries; Ved for A01 settings agreement.
Objective: let the runner drive whole Plain and Agent episodes through the shared A01 provider, the A02 harness and the A04 controller, with persisted attempts, an attempt budget and unknown outcomes, so the study can run as soon as A01 is accepted and a run is authorized. **No model request is made by this change.** Tests use a synthetic loopback responder only.
Base commit / branch: base `231293c` on main; branch `nisha/e02b-model-units`.

Changed paths:
- `dc_sustainability/experiments/models.py` (new): model inputs, the Plain receiving path, the agent step, ledger/budget/unknown handling.
- `dc_sustainability/experiments/config.py`: `ModelSettings` (seeds, per-decision deadline, run attempt budget, deployment pins, plain prompt hash, agent renderer reference) as part of `RunConfig` identity. A/B-only identities are unchanged.
- `dc_sustainability/experiments/registry.py`: Plain and Agent run only when explicit model inputs are passed.
- `dc_sustainability/experiments/runner.py`: model units, budget admission, `unknown.json`, `attempts.json`, halting.
- `tests/experiments/test_model_units.py` (new, 7 tests); `tests/experiments/test_runner.py` (the unavailable-system test now uses `decision_tree_c`).
- `docs/handoffs/E02B_MODEL_UNITS.md` (this file).

What it does:
- **Explicit inputs only.** `runner.run(config, out, models=ModelInputs(provider_factory, agent_renderers))`. Nothing in the package builds a provider, deployment or renderer, and the CLI passes none, so the CLI still refuses Plain and Agent.
- **Frozen settings.** `ModelSettings` has no defaults: one seed per model trial (Plain and Agent share a trial's seed), `decision_seconds`, `max_total_attempts`, the A01 `Deployment` pins without the address, the plain prompt-template hash and the agent renderer reference. They are part of the config hash, so a changed setting is a different run. Before anything is written, the run refuses changed plain prompt files, missing agent renderers and a provider whose pins differ.
- **One ledger per unit.** The provider caps attempts per (system, episode, slot), and the harness pins one (run, trial, seed), neither keyed by trial. So each unit (system × episode × trial) gets a fresh `OllamaProvider` and, for the agent, a fresh `AgentHarness`. `deployment.max_run_attempts` therefore bounds one unit.
- **Plain decision.** It uses the flat K02 context and one `PlainLLMPolicy.propose` call. Every new ledger attempt is persisted with `record_attempt` before execution. The output is checked once as the initial stage, then the controller decides. There is no repair or fallback (`not_applicable_stages` = repaired, fallback). The original response, explanation, call count, latency and tokens are recorded. An empty queue makes no call.
- **Agent decision.** `AgentHarness.run_decision`, with the real Greedy A as its checked fallback. The harness persists its own attempts and calls the controller.
- **Run attempt budget.** A model unit starts only if the attempts already spent in the run directory, plus the smaller of its call-cap worst case (24 × 1 for Plain, 24 × 3 for Agent) and the matched per-unit provider ledger cap, fit `max_total_attempts`. Spent attempts are the saved artifacts plus the unsaved attempts listed in `unknown.json`. Otherwise the unit stays pending with the reason. A restart counts spent attempts, so neither a restart nor a lost artifact gives back budget.
- **Unknown or unsaved attempts.** Each of these stops the unit as `needs_reconciliation`:
  - an attempt that is uncertain (sent, with no reliable outcome);
  - an attempt whose artifact could not be saved.

  For the Agent, the harness treats either as fatal, so the decision is traced as blocked with no further dispatch. For Plain, a failed save raises before anything executes. `unknown.json` records each attempt's `outcome` and `saved`. While any model unit needs reconciliation, no model unit starts, in this call or later ones. Deterministic units still run. Nothing is retried. If the run directory itself can't be written, `unknown.json` can't be either: `run` then raises and stops, and the run must be reconciled by hand.
- **Completion slots** 24–29 use the E02-a drain record with zero calls, as for A/B.
- **On completion** a unit also publishes `attempts.json` (slot, trace ID, outcome `ok`/`failed`/`unknown`, error). The lossless attempt files stay in `traces/provider-attempts/`.

Tests (real provider over loopback HTTP, real harness, checker, controller, trace store and simulator; the responder is synthetic):
- **Whole episodes:** Plain and Agent for two trials. All 30 slots are traced, with zero calls in completion slots and calls within caps. Trial 1 is not blocked by trial 0. Saved attempts = `attempts.json` = the record call counts = HTTP requests. Seeds are per trial. E01's independent replay agrees with each `EpisodeResult`.
- **Plain** gets one call, with no repair or fallback, and its original response is kept.
- **Agent** goes through the failed initial and repaired stages to the real Greedy A fallback, within three calls.
- **Uncertain request:** the unit stops as `needs_reconciliation` and the other trial is halted. The deterministic unit completes. One request total, and a later call still sends nothing.
- **Budget:** counts persisted attempts across calls.
- **Refusals before writing:** no model inputs, no renderers, changed pins, changed prompt files.
- **Settings:** required exactly with model systems, validated, and part of the run ID.

Mutation check: six deliberate bugs each made a test fail, and the code was restored:
- the budget ignores persisted attempts;
- one provider is shared by all units;
- an unknown outcome is not raised;
- Plain attempts are not persisted;
- an earlier reconciliation does not halt;
- Plain call counts are not recorded.

Input and output contract/config versions: F02 1.0.0, unchanged. Run config `e02-run-config-v1`, with an optional `model` block present only when a model system is listed.
Artifact locations and checksums: none committed.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/experiments -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
```

Tests actually run and observed results: Windows 11, Python 3.12.10, hashed lock. The full suite passed 1,548 tests and 19 subtests (after both fail-closed fixes). Ruff check/format, setup validation and pip check passed. No model request was made.

Owner decisions (Matty, #18 and the PR #113 review, 2026-10-29):
1. **Unit = A01 run: accepted.** One fresh provider ledger and Agent harness per unit (system × episode × trial).
2. **Unknown outcome: stop the unit** as `needs_reconciliation`. It is not an ordinary failed decision followed by continued execution.
3. **After an uncertain Agent attempt: fail closed.** Implemented in `AgentHarness._call`: a newly persisted attempt with `uncertain_outcome` makes the decision fatal, so no repair, explanation or further provider dispatch follows, the fallback is not run, its output is not used, and no stage is selected. The controller records the blocked decision and the runner then stops the unit. Regressions: `tests/agent/test_harness.py::test_uncertain_proposal_fails_closed_with_repair_fallback_and_explanation_configured` and `tests/experiments/test_model_units.py::test_uncertain_agent_proposal_sends_nothing_more_and_needs_reconciliation` (exactly one request, no selected stage, unit needs reconciliation). Both fail with the guard disabled.

4. **Attempt-storage failure (PR #113 review): fail closed for both systems.** An attempt whose artifact could not be saved stops the unit for reconciliation, halts later model units and stays in the run budget (`saved: false` in `unknown.json`). Regression: `tests/experiments/test_model_units.py::test_unsaved_attempt_stops_the_unit_halts_model_units_and_keeps_budget[plain_llm|agent]` (exactly one request, no later slot or unit dispatch, no result, budget 1).

Open note: a unit is admitted on the strictest enforceable worst case (the smaller of 24 × the call cap and its matched ledger cap), which is conservative because empty-queue decisions make no call.

Limitations and next steps:
- PR #116 supplies request-local response bounds. The single-use EP-HAND1 limits
  are agreed and regression-tested, and the future full-matrix maxima are recorded
  in `experiments/matrix.py`; neither record authorizes a model request. Every actual
  exercise still needs accepted frozen inputs and a separate recorded authorization.
- Reviewed proposal, repair and explanation renderers and the plain prompt are on
  main and remain explicit run inputs pinned by hashes/references.
- Resume is per unit, not mid-episode, as in E02-a.
- E02-c and the structural 300-run matrix checker are on main. Real P04 C/D
  artifacts, the private held-out custody loader and the I02 scientific freeze remain.

Receiving owner and consumer check: Matty, for the provider/harness/controller use and questions 1–3.
