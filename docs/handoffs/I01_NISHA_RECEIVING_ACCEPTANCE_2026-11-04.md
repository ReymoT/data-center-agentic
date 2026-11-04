# Accepted independent development content receiving

Matty received Nisha's report directly and reviewed it on November 4, 2026.
[Her unchanged supplied report](../evidence/I01_RECEIVING_NISHA_2026-11-03.txt)
has raw SHA-256
`900e67598cdb9c4e8aab6f927d94a4407980a55bc21d52780e1ca890c6c9d588`.
The scoped Git attribute preserves its exact bytes across checkouts. Her
[public acknowledgement](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6623003586)
also records receiving PASS. Her review-script and machine-report hashes are
attestations in the text; those files and the retained initial FAIL were not
supplied to Matty and are not represented as independently inspected artifacts.

## Accepted scope and actual corroboration

Nisha received the original packet, verified its committed digest and all 186
evidence files (six results/180 traces), checked identities and all slots 0–29,
and ran the separately implemented E01 replay with Q03 Option B. Every unit has
zero execution findings and zero EpisodeResult mismatches. Her report records
the exact clean checkout, environment and installed-lock verification. She wrote
E01; this is a separate person's receiving review using the existing independent
evaluation implementation, not a newly independent second replay implementation.

Matty accepts **independent content receiving of these two existing public
development runs**. The packet-transmission/receiving dependency is resolved;
another transfer-route request or another development rating pass is unnecessary.
Nisha reports Slack delivery and authentication against the previously committed
handoff digest. Matty has not claimed to observe the actual upload or receive a
separate digest message.

[Manager corroboration](../evidence/I01_RECEIVING_MANAGER_CORROBORATION_2026-11-04.json)
actually rehashed the archive/all indexed evidence, checked canonical JSON decision-ID
filenames, identities/slots and replayed all six results. It also matched both
original manager-local run manifests against all six unit-index bindings. This
adds the manifest provenance check absent from the packet, as a **manager check**;
it does not change Nisha's narrower report or claim she inspected those manifests.
No originals were modified, model requests dispatched or held-out inputs opened.

## Preserved limitations and corrections

- Nisha's first filename check hashed raw decision-ID bytes. Runtime filenames
  use `sha256_hex(decision_id)`, hashing the canonical JSON string. Her final report
  discloses the correction, fresh-folder rerun and identical extractions. That bug
  was already fixed in her reviewer script; it was not a defect in project traces.
- `completed_work` is absent in all original results. The correct comparison is
  `absent`, not a match. Derived completed IT work is 140 kWh for the five units
  completing J1/J2 and zero for Plain. No original field is filled and no numeric
  precision or savings acceptance is invented.
- Classical trials are null under the deterministic-unit contract. Manager checks
  explicitly verified null for A/B/C/D and trial 0 for Plain/Agent. The historical
  index has no trial field; it was not silently rewritten to add one.
- This structural replay does not certify every energy/emissions total, explanation
  faithfulness, source rights, physical source interpretation or final study result.

The repository correction is to remove stale *current* claims that transfer and
independent content receiving have not happened, while preserving dated preparation
records and the original report unchanged. No repair is required to the final PASS.

## What is now ready and what remains gated

The existing public-receiving candidate `RUN-0f7d9498db6f` can proceed to review of
its exact pending single-use authorization. The accepted receiving report resolves
that preparatory dependency; it does not itself authorize another model request.
The candidate remains one public episode/trial with at most six Plain/eighteen
Agent/twenty-four combined requests and the existing time/stop limits.

Full I01/pre-freeze acceptance remains partial: no fresh unified six-system run
or its independent receiving is claimed. Source B1–B3, B4 suitability, actual
held-out custody and accepted study-forecast/broker/isolation implementation remain
separate gates. I02's manifest stays pre-freeze, with no frozen items or run authority.
Final I04 and held-out reliability #95 are not unblocked by this technical receipt.

[Nisha's CF60-v1 response](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6622770964)
is conditional acceptance within her own scope, with
three concrete custody clarifications: eligibility under the original recorded
index plus both interval hypotheses; reserving legacy and CF60 development
footprints for all forty development episodes; and merging/pinning the new selector
version before any nonce. Her same-hour-shaped option is an additional evaluation
question, not a condition on that acceptance. Other affected-owner responses and
an explicit method decision are still required; nothing is retrained or reselected.
