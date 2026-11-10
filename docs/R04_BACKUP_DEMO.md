# R04 backup demo walkthrough

## Current demo choices — November 9

The latest technical result is RUN-cb85f5a3425c, with 180 records, 17 requests, 532.219 seconds, zero replay findings/mismatches, 39 valid numeric/unit pairs and successful cleanup. Separate-person receiving and explanation faithfulness are still pending. Use the [updated script](report/R04_FIVE_MINUTE_SCRIPT_2026-11-09.txt) and [saved new-run excerpts](report/R04_DEMO_CB85_EXCERPTS.json), which read only selected fields from the actual records.

Option A: keep the existing trace-explorer and screenshots explicitly labelled RUN-fd87c6c8a9cb. That older snapshot has its own 96-character limit, timing and receiving record. Then show the published corrected-run summary separately. Do not change a screenshot caption or claim the explorer displays cb85 when it does not.

Option B: open R04_DEMO_CB85_EXCERPTS.json or the unchanged cb85 receiving packet in a text/JSON viewer. Show slot 0 (failed initial and repair, checked fallback, only J1 starts now) and slot 3 (initial plan passes and J2 starts). The fallback's future J2 intention at slot 2 was not executed at slot 0. Both Agent repairs fail; do not call their presence a success. No model runtime needs to be started for either option.

End with the recorded freshness/impact-support limits and the separate #60 source/CF60 gate. The receiving packet has raw responses for Nisha's scoped review, not new formal blinded ratings. No new model call is authorized by this demo guide. The walkthrough below is archival; its old commits, paths and steps are not the current instructions for either option. Use the current choices above and the updated script.


## Historical walkthrough (archival, not current instructions)

The [working saved-trace explorer](report/UI_VISUALIZATION.md) supplies the actual
UI for this walkthrough. Select the Agent run and recorded fallback filter to show
initial/repair checks, checked fallback and actual starts. It reads saved evidence;
do not call it a live inference demo.

Owner: Matty. Use the saved public EP-HAND1 receiving evidence. This walkthrough
does not dispatch a new request. Prepare screenshots locally after inspecting the
saved artifacts; no screenshot or video is claimed to exist in this document.

## Before the meeting

Open [the development report section](R04_DEVELOPMENT_EVIDENCE.md) and
[receiving record](handoffs/EP_HAND1_RECEIVING_F04_F05.md). Confirm the tested
commit `482842968edd1fe963a647db9ed826bf3a195c40`, authorization and evidence
digests. Locate the private directory `a02-ep-hand1-replacement-2026-10-31` under
the manager's project output. Keep raw requests, responses and runtime logs local.
Do not substitute another run or open held-out material for this demonstration.

Select saved Agent records containing initial/repaired/fallback stages and their
actual checker outcomes. Select a Plain record from the same episode/seed; the
systems' states can differ after earlier actions, so do not claim identical states
at every slot. Show actual IDs, slot/state versions and checks from those records.
Do not invent dialogue, missing fields or a successful repair.

## Latest validation update for deck review

Keep the saved walkthrough tied to its original run. Show the separate
[RUN-fd87c6c8a9cb result](handoffs/I01_ACTION_CHOICE_VALIDATION_RESULT.md)
as development evidence. Six systems completed, with 180 traces and zero replay
findings. Nisha passed evidence receiving. Agent executed J1 via checked fallback
and J2 via its initial model proposal. Plain executed no starts. Both Agent repairs
failed their checks. Seven of ten summaries hit the text cap, and
[completeness scoring is under review](handoffs/I01_EXPLANATION_LENGTH_AUDIT.md).
Study results are still pending.

## Suggested five-minute sequence

1. State the research question and show the public scenario. Explain what the
   policy can see and what remains private. No superiority claim is available yet.
2. Show the architecture: domain graph -> visible context -> proposal -> check ->
   optional repair -> checked fallback -> latest-state gate -> trace/evaluation.
   Explain that LangGraph is the workflow, not the ontology graph.
3. Walk through one saved Agent record. Show the initial check, the recorded
   repair if present, fallback if present, selected outcome and executed starts.
   Explain the difference between proposing a future start and executing now.
4. Show one Plain record and its original output. Explain one call and no
   repair/fallback. An unsafe proposal can be refused by the common gate.
5. Show both 30-slot replay summaries: zero findings and zero result mismatches.
   Show request counts (5 Plain, 12 Agent), recorded repair/fallback stages and
   cleanup confirmation. End with the remaining experiment and source gates.

## Optional classical-policy evidence

Use the existing manager-local `P04_Private_2026-11-02` receiving summary for
`RUN-1f6e4c4c2afb`: A/B/C/D each have 30 traces, two completed jobs and zero replay
findings/result mismatches. Show the published model hashes and selection/counts
from the P04 handoff, not private source values, joblib bytes or training rows.
Label this as a separate development run from the LLM receiving. Do not present
the two exercises as one matched six-system experiment or a measured advantage.

## Screenshot checklist

- Public scenario and visible evidence IDs, without private oracle fields.
- One real Agent stage/check sequence; redact machine-specific paths if needed.
- One real Plain output and gate result.
- Independent replay result and sanitized count/identity/cleanup evidence.
- Remaining-work list with actual owners and artifact prerequisites.

Screenshots demonstrate saved behavior. Label them as public-development replay,
with the run commit and episode. If the private artifacts are unavailable, use
the published receiving summary only and explicitly limit the demonstration to
that summary. Do not call it a live demo.

## Questions to answer accurately

Why an independent evaluator? It avoids simply reusing the production checker
as the only judge. Why fallback? It provides a checked alternative when a candidate
fails; its effectiveness still needs evaluation. Is the agent better? The full
paired study is pending. Are C/D trained? Yes: real development binaries were trained, saved, reloaded and received.
See the [P04 handoff](handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md); final scientific
selection and acceptance remain pending. Does zero replay findings prove faithfulness? No; explanation
support is evaluated separately, including the human annotation protocol.
