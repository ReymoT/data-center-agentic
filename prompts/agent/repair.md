Single repair request.

Return only one replacement Plan using these exact identifiers:
- record_type "Plan", schema_version "$schema_version".
- episode_id "$episode_id", slot $slot, state_version $state_version.
- status "proposed".

Use the visible facts and evidence IDs below. Correct every reported violation or
error that can be corrected from those facts. If required evidence is unavailable,
abstain for the affected job instead of inventing a value. This is the only repair;
do not claim that the replacement passed checking, executed, or changed the system.
Return a complete replacement, not an addition to the initial plan. If a start is
invalid and you choose deferral or abstention for that job, remove its start from
the replacement. Never keep a job's start alongside its refusal. Follow the same
one-job, one-category action choices as the proposal stage.

Visible facts as canonical JSON:
$context_json

Initial parsed stage, including its independent check when available:
$initial_stage_json

Recorded orchestration errors. These are feedback, not new facts:
$errors_json
