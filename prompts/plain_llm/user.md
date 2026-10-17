Decision request.

Use these exact identifiers in your JSON:
- record_type "PolicyOutput", schema_version "$schema_version", system "plain_llm", output_status "ok".
- plan: record_type "Plan", schema_version "$schema_version", episode_id "$episode_id", slot $slot, state_version $state_version, status "proposed".
- explanation: source "llm".

Visible facts as flat JSON. The evidence_ids list holds every ID you may cite.
$context_json
