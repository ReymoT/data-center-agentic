# October 23: received decisions and remaining agreement

Matty authorized the recommendations and publication through [maintenance issue #46](https://github.com/ReymoT/data-center-agentic/issues/46). This records replies and their scope; it does not freeze an experiment or change a shared schema, runtime, dependency or scientific setting. Earlier dated records remain history where superseded.

## Q10: Ved replied; the exact refinement still needs Nisha

[Ved's response](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6359863305) supplies the missing design/analysis input. [Matty accepts the refinement for his side](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6372045868). Do not continue to list Ved's Q10 reply as missing.

The refined manual-review frame uses only exogenous timing: `latest_start = min(deadline_slot, 30) - duration_slots`, capped at arrival for nonflexible jobs. A slot from 0 through 23 is eligible if it lies in at least one job's temporal start window. This replaces the earlier deadline-not-passed proposal, so Nisha must confirm the exact refinement before selection is frozen. It does not prove capacity feasibility, settle impossible-arrival visibility or change automatic evaluation. Jobs without a permissible window cannot alone make a manual-review slot eligible; the full automatic run set still retains those jobs and outcomes.

Retain the target of 60 pairs, two distinct slots per episode, 20 pairs per trial and manifest strata, with deterministic allocation/ties and achieved counts recorded. Keep selected failures, malformed/missing outputs and one-sided no-ops; report NAs and any shortfall without topping up. Sampling seed 20261019 and analysis seed 20261020, generator/version, extraction/label agreement, paired episode-block bootstrap and whole-date sensitivity remain as described in the replies. Undefined statistics stay undefined. No selection map or rubric is frozen yet. Nisha owns the implementation and boundary tests.

## E01: quantity, units and references

[Ved's contract response](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6360499821), [Nisha's strict-basis confirmation](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6357877299) and [Matty's response](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6372046280) are received. Ved's substantive reply and Nisha's stricter-basis position are no longer missing. These replies are not an implemented or fully accepted E01.

- Keep completed job count and completed IT energy before PUE separate, independently derived by job ID. Background, PUE, missed and unfinished jobs do not enter completed IT energy. Current experimental `completed_work` remains `None`.
- Facility job energy with PUE stays distinct. Edison must still confirm the P01/S02 consumers preserve that distinction. E01 retains independent arithmetic.
- The discussed rules are inclusive absolute 0.05 for kWh/kg and kW/g-per-kWh, and exact integer slot/hour comparisons, with no extra epsilon. Percent is not added to F02 and stays outside automated numeric scoring; manual percentage review is reported separately. Unscored is never counted correct.
- Use the closed reference-kind taxonomy in the development review without a new F02 field. Forecast claims use what the system saw; realized claims use independent private-realized arithmetic. Savings need a named baseline and matching completed sets, horizon and inputs.
- An energy basis must be unambiguous from the text or cited evidence. Do not try both bases and accept whichever matches. An unstated basis is unsupported and recorded as `basis_unstated`; false stated-basis claims are contradicted when their reference is available. Worked examples must establish why the evidence identifies the basis; a numeric match alone cannot choose it.

The optional future `completed_work` comparison needs its own numeric rule. Matty proposes inclusive absolute 0.01 kWh, no relative tolerance or added epsilon, and an explicit retained difference. **This is a proposal requiring Nisha/Ved agreement, not adopted behavior or a new field.** Current records stay `None`; pending optional comparison must not be replaced with the claim tolerance. Nisha can progress the agreed independent quantities, unit checks and rubric work while keeping unresolved details pending. Her checkpoint remains a PR within two working days of the required recorded agreement; confirmation was requested, not invented.

## Q09/A01: Nisha's runtime reply and receiving adoption

[Nisha agrees to 0.40.9 revalidation with additions](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6357889684); [Matty accepts those requirements for his side](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6372046814). Ved's official-tokenizer dependency direction and exact current-runtime revalidation agreement remain pending; his Q10/E01 replies do not decide Q09.

Revalidation must verify the effective temperature 0.2, seed, num_ctx 16384 and num_predict 1536 options, including conflicts with defaults. Record runtime/artifact/template/parameter identities at both run boundaries. Retain a drifted run and mark it invalid as a whole; paired systems must use the same accepted recorded runtime. A replacement run is not a hidden retry: it still needs authorization, available budget, retained failure provenance and any required post-freeze amendment. No update/service change or automatic rerun is configured. The accepted pin remains 0.40.5; the dated October 22 inventory observed 0.40.9. No fresh runtime inventory or inference is claimed for this intake.

Nisha's [instruction 1.21 adoption](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6357932913) includes her full 1022-test/19-subtest pass and six A01 receiving cases. This is received evidence, not a missing request or proof that the intermittent timeout is fixed. Her session's K02/current-maintenance adoption remains separate.

Matty's new ordinary suite retains 1057 passes / 19 passing subtests plus the existing object-plain timeout. A contemporaneous independent synthetic HTTP control again timed out at 23,360/24,001 bytes; the other three controls completed. The two commands ran concurrently, so the observations are timing-sensitive, not a controlled reliability comparison. No reader, protocol, payload, deadline or setting changed; no root cause or timeout fix is established.

## E05 and the other owner inputs

[Nisha's receiving intake](https://github.com/ReymoT/data-center-agentic/issues/42#issuecomment-6357903252) states she has not opened Matty's original labels and sets October 24 for her original ratings and SHA256. [Matty acknowledged the checkpoint](https://github.com/ReymoT/data-center-agentic/issues/42#issuecomment-6372047202). His first pass remains submitted unchanged. After both originals, match assertions, report extraction and label agreement separately, then preserve separate joint adjudication. No paired outcome or completed E05 is fabricated.

[One consolidated owner request](https://github.com/ReymoT/data-center-agentic/issues/46#issuecomment-6372047554) covers remaining Reimo/Ved/Edison arrival/window/Q08 decisions, actual S02 adoption, the upcoming October 25 P02 checkpoint, source/freeze evidence, Reimo/Ved allocations and remaining Q13 positions. Existing course-rubric acknowledgment and completed D06 structural checks are not requested again. Frontier D02 access remains separately deferred. Passing CI is not missing scientific agreement, receiving adoption or full task acceptance.
