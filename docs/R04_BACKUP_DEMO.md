# R04 backup demo walkthrough

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
