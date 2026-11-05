Single repair request.

Return only one replacement Plan using these exact identifiers:
- record_type "Plan", schema_version "$schema_version".
- episode_id "$episode_id", slot $slot, state_version $state_version.
- status "proposed".

Use the visible facts and evidence IDs below. Correct every reported violation or
error that can be corrected from those facts. If required evidence is unavailable,
abstain for the affected job instead of inventing a value. This is the only repair;
do not claim that the replacement passed checking, executed, or changed the system.

Visible facts as canonical JSON:
$context_json

Initial parsed stage, including its independent check when available:
$initial_stage_json

Recorded orchestration errors. These are feedback, not new facts:
$errors_json
