# A02 and L01 EP-HAND1 offline freeze

Owner: Matty Anderson (`MattyAnd`)  
Issue: #18, with #12 as the receiving consumer  
Scope: one public development receiving episode, not a study run

The repository now has the inputs needed to identify one future matched Plain and
Agent receiving exercise without ambiguity. The public `EP-HAND1` bundle, Plain
prompt, Agent proposal prompt, Agent repair prompt and Agent explanation prompt are
all pinned in
`docs/evidence/a02-episode-authorization-preparation-2026-10-30.json` by repository
commit, path and SHA-256 hash.

The earlier A01 bounded transport validation succeeded with two requests, no retry,
normal stops, strict parsing and full 37/37 Arc/Vulkan offload. That evidence shows
that the shared provider can return bounded Plain and Agent-shaped responses. It does
not authorize an A02 episode and it is not a study result.

## What remains blocked

The A02 episode is not ready for dispatch. The following fields deliberately remain
unset:

- maximum Plain requests for the episode;
- maximum Agent requests for the episode;
- the per-request and whole-episode deadlines; and
- an authorization naming those exact limits and this frozen input set.

These values are a separate A02 run decision. They must not be copied silently from
the consumed A01 two-call authorization. Until they are recorded, no model request,
retry, simulator episode or study run is authorized.

The later 40-episode development study still depends on D04 materialization and its
scientific gates. This public receiving exercise does not replace that work.
