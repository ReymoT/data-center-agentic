Planning request.

Use these exact identifiers in your JSON:
- record_type "Plan", schema_version "$schema_version".
- episode_id "$episode_id", slot $slot, state_version $state_version.
- status "proposed".

Give one disposition for every visible waiting job: start, defer or abstain. Only
current-slot starts can execute now; later starts are intentions that will be decided
again. Cite only IDs from the evidence_ids list.

Visible facts as canonical JSON. The evidence_ids list holds every ID you may cite.
$context_json
