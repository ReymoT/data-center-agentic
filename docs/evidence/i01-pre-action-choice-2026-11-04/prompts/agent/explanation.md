Explanation request for episode_id "$episode_id", slot $slot, state_version $state_version.

Return one Explanation with source "llm", a summary, claims and limitations. Give
each claim a short claim_id such as "C1". Cite only IDs from the evidence_ids list.

The plan below passed one independent schedule check, shown after it. You may say
that this check passed. It has not executed: a final check at execution time decides
what runs, so do not say that any job started, that emissions were saved, or that any
other check, tool, repair or source was used. Do not say how the plan was produced.

Plan to explain:
$plan_json

Its independent check:
$check_json

Visible facts as canonical JSON. The evidence_ids list holds every ID you may cite.
$context_json
