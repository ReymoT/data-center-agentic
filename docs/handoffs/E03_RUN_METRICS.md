# E03 run-level metrics

Task ID / Issue: E03. Owner: Nisha. Technical contact: Edison.
Objective: score one saved run for accuracy, safety, completion, impact and cost, judged by E01 rather than by the run's own checks.

Changed paths:
- `dc_sustainability/evaluation/run_metrics.py` (new): `run_metrics`, `RunMetrics`, `StageMetrics`, `CostMetrics`.
- `tests/evaluation/test_run_metrics.py` (new, 26 tests).
- `docs/handoffs/E03_RUN_METRICS.md` (this file).

What it does:
- `run_metrics(episode, records, protocol)` replays the run with E01, then re-validates every recorded plan against the replayed state.
- **Accuracy.** Decision accuracy is final-stage valid plans / all recommendations.
- **Stages.** Initial, repaired, fallback and final are reported separately, each with its own denominator and finding counts. An unused stage is not a safe output: it stays out of that stage's denominator. The final stage is the plan the execution gate checked, otherwise the last recorded stage.
- **Executed stage.** Executed starts and E01 replay findings are reported as counts by code. There's no rate, because a capacity finding belongs to a slot rather than to a start.
- **Abstention.** Abstained jobs and justified abstentions are both counted. E01 credits only verified infeasibility or unavailable required evidence.
- **Repair and fallback.** Rates use recommendations where the stage applies, so a system without the stage gets `None`, not 0.
- **Outcomes.** Completed, missed and unfinished jobs (missed and unfinished overlap), completed IT and facility energy, and completed-job emissions. Missing realized carbon gives `None`.
- **Checker comparison.** Production checks are compared with E01 through `compare_with_check`; they never decide a verdict.
- **Cost.** Model calls, latency, tokens and cost. A total is `None` if any record that made calls lacks it, never a partial sum.

Draft definitions to agree before freeze:
1. **Is an omission unsafe?** R05 defines unsafe advice as a proposal the checker would refuse, and the checker refuses omitted jobs. An omission breaks the coverage rule but asks for nothing dangerous, so `unsafe_rate` follows R05 and `unsafe_rate_without_omissions` gives the narrower reading.
2. **What is a recommendation?** A decision slot with waiting work, or with a plan claiming some. Empty-queue no-ops are counted apart, because including them would raise accuracy for doing nothing.
3. **Pending decisions.** They stay in the accuracy denominator and aren't credited, following "valid / all recommendations".

Open items:
- **Agent latency isn't recorded.** The Plain path sets `latency_ms` on its decision records, but the Agent harness doesn't, so Agent latency is `None` from saved records. Tokens are recorded for both. A latency comparison needs the harness to set it, or the saved attempt records.
- Cost in dollars is `None` for local model runs.
- Not wired to `paired.Observation` or a report yet; that comes with E06.

Tests (hand truth): the hand schedule gives 54.5 kg and 140 kWh, with facility energy scaling by PUE. Cases cover no-plan decisions, empty-queue claims, omissions, stage denominators, gate selection, justified and uncredited abstention, checker disagreement, an executed capacity break and cost gaps.
- Mutation check: sixteen deliberate bugs each make tests fail, and the code was restored. Two survived at first, so two tests were added. A third showed dead code, which was removed.

Private receiving check: the metrics ran on the two saved development runs held under the I01 receiving custody. Greedy A and Greedy B emissions match the hand values, and E01 and the production checker agreed on every stage plan. Those records stay private and aren't test inputs here.

Input and output contract/config versions: F02 1.0.0, unchanged.
Artifact locations and checksums: none.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation/test_run_metrics.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
```

No model calls, held-out data or source values were used.

Manager review fixes an empty-queue edge case: a valid final no-op must not hide
an unsafe initial/repair/fallback proposal. A slot is excluded as a no-op only
when every present stage is independently valid and empty. Two regression cases
cover repair and fallback returning a safe final no-op after an unsafe proposal.
The original twenty-six tests above are retained; the reviewed module has twenty-eight.
Both omission measures remain available and explicitly draft; this merge does
not select a primary safety endpoint or freeze the definitions. Agent latency
remains unavailable in original records; it is not imputed as zero or repaired
by rewriting evidence. The harness/accounting follow-up belongs to Matty before
any latency-comparison freeze, not a resubmission request to Nisha.
