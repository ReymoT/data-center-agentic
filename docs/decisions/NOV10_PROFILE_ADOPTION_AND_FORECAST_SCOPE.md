# Prospective response-profile adoption and v2 forecast scope

Date: November 10, 2026 (Arizona). Decision owner and authorizing manager: Matty Anderson (MattyAnd). Matty explicitly authorized recording both decisions in this chat. Reviewed main: fda701d9cbebc7df954b0f15e80610d4a83d3aeb. This records prospective study configuration, not a complete I02 scientific freeze or permission to execute.

## 1. Adopted prospective response profile

Matty adopts explanation-profile-256-4096-v1 for the future exact study configuration, after the directly affected owners confirmed it without changes:

- [Ved's context/retrieval and budget agreement](https://github.com/ReymoT/data-center-agentic/issues/185#issuecomment-6779877050).
- [Nisha's E04/L01 agreement and cap-handling confirmation](https://github.com/ReymoT/data-center-agentic/issues/185#issuecomment-6782827619).

| Setting | Adopted prospective value |
|---|---|
| Each explanation summary, claim text and limitation | Maximum 256 characters |
| Output allowance, both Plain and Agent | 4096 tokens |
| Context | 16384 tokens |
| Prompt ceiling | 12288 tokens |
| Claim grammar | Number plus existing allowed unit, or null value plus null unit; both fields required |
| Plan deferral/abstention detail | Existing 96-character limit |
| Action arrays / shared fact and instruction treatment | Unchanged |
| Plain comparator | One request, no feedback, repair or fallback |
| Rule 11.9 | Pass --cap-limit 256 for runs generated with this profile; flag each field exactly at the cap, review visible cut-offs, report by system/field |

Existing count bounds, model/temperature/seeds, prompt text, plan rules, execution gates and request/decision/wall-time bounds are unchanged. Character/token limits are bounds, not guarantees that a model will finish or state truthful claims. Old 96-character outputs keep their original cap treatment; never rescore them as if they used 256. No original run/config ID, rating or failed outcome changes.

This adopts the protocol choice, not a global runtime-default migration. Existing deployment defaults remain unchanged; the future reviewed run configuration must explicitly set these fields, bind exact prompt/schema/code/model/environment hashes and pass I02 acceptance. The tested opt-in implementation already exists. No server startup, model request or single-use authorization is supplied by this record.

## Evidence and issue scope

The corrected public RUN-cb85f5a3425c passed bounded technical validation and Nisha's separate-person receiving, with the transferred ZIP hash confirmed. It contains 39 paired claims and 0 of 73 fields at 256, maximum length 226. Real cut-off behavior at the cap was not exercised. Existing rule 11.9 tests and handling remain necessary.

The [saved-content assessment](../evidence/cb85-content-assessment-2026-11-10.json) and Nisha's response retain contradicted capacity/missing-forecast claims, unsupported rationale and citation applicability problems. Adopting bounds does not fix these findings or establish a positive research result. Original human ratings and IRR are unchanged. Formal held-out annotations follow the agreed protocol; no additional human scores are invented here.

The bounded #185 work is resolved once this record is published: cap assessment, preserved evidence, scoring treatment, technical candidate validation/receiving, saved-content findings and affected-owner/manager profile adoption. Full I01/I02/I04 and known faithfulness limitations remain separate. Closing #185 records this scoped completion, not the truth of all generated explanations or a completed study.

## 2. Forecast-method limit for the pinned v2 selector

Matty confirms Nisha's [v2 condition](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6782772091): the current selection protocol permits legacy preceding-row persistence or CF60, with recorded scoring and both interval hypotheses covered by the reserved footprint. Same-hour-yesterday and every longer-lookback alternative are outside this v2 protocol and are no longer live candidates for this selection. This limits the candidate set; it does not scientifically adopt either method, choose an interval interpretation or certify source semantics/rights.

A longer-lookback proposal requires a new exact footprint/eligibility amendment, versioned selector and affected-owner agreement before any nonce/selection. Never add it after selection, redraw a cohort based on outcomes, or silently reuse v2 as sufficient coverage. If the protocol is reopened later, stop and explicitly resolve preservation/blinding implications before any action; this record grants no reselection permission.

Pinned selector: commit fda701d9cbebc7df954b0f15e80610d4a83d3aeb; version d04-held-custody-v2-forecast-union; algorithm sha256-rank-greedy-fixed-development-forecast-union-v2; held_out_custody.py LF SHA256 2eec2778b4957f6bad3755467e9ab5adc517a2eab3fed151aacf018eb9914bfd. Existing 40 development records remain unchanged.

Nisha [reports B5 storage ready](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6783459234): outside sync/Git, restricted ACL, deny test passed and BitLocker on, with her record held privately. This is her authenticated report, not an additional storage test performed by Matty. No nonce, selection or held-out metadata exists according to that reply.

Remaining order: Reimo confirms the exact restricted v2 parameter record; Nisha authenticates required agreements and privately creates the nonce/selection, independently checks isolation and posts only the receiving locator/digest; permitted development ingestion then needs source-use evidence and Matty's fresh exact bounded authorization. Source B1-B3 remain unresolved and B4 provisional. Actual extract/comparison, O02/C/D compatibility, forecast adoption, I02 freeze and held-out execution remain gated. #60 stays open.

## Validation and unchanged work

No production code, operational config, master policy, original evidence/rating, source input, nonce or allocation is changed by this decision. Existing offline tests/technical receiving support the profile; this documentation change runs repository/local-link and pre-freeze-manifest validation plus ordinary CI. No model, source ingestion, solver, training, rollout or held-out execution occurs.
