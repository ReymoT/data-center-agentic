# Master instructions — Ved

Current evaluation update, instruction 1.28: [the professor's inter-rater-reliability feedback](../decisions/PROFESSOR_FEEDBACK_IRR.md) is an accepted reporting requirement. Nisha is the sole accountable owner for reporting matched counts, label marginals, raw agreement, Cohen's kappa, undefined cases and a plain-language interpretation for development and held-out human faithfulness annotations. Matty remains the independent second rater and joint adjudicator, not a co-owner of the reporting task. PR #104 retains the development matching and reliability artifacts: 32 matched claims, 75% raw label agreement and Cohen's kappa 0.00 under the documented single-label prevalence limitation. Joint adjudication of 77 open items and the later held-out report remain unfinished; originals stay unchanged. Other task owners, shared formats and scientific gates are unchanged.

Current manager update, October 24: [coder-owned decisions](../decisions/Q11_CODER_OWNED_DECISIONS.md), authorized by Matty in [the team announcement](https://github.com/ReymoT/data-center-agentic/issues/57). Internal implementation decisions belong to the coder; shared changes go only to affected owners and unresolved shared questions escalate to Matty within 24 elapsed hours. Work on agreed portions proceeds immediately. Existing task assignments, exact merge/main-authority rules and scientific acceptance stay intact. Earlier dated entries are historical where superseded.

Version: 1.28 — 2026-10-27. Repository: https://github.com/ReymoT/data-center-agentic

Current implementation update, 2026-10-15: D02 calibration tooling and D03 provisional synthetic fixtures are merged. [Matty's D03 checker-consumer handoff](../handoffs/A03_D03_F04_F05.md) records fixed-rule tests, not simulator or independent-evaluation acceptance. Frontier calibration, Q01-Q06 and downstream acceptance remain pending where documented. Task ownership and shared rules are unchanged.

Course planning update, October 20, 2026: Nisha reports Group 15 presents in class November 16, submits the presentation November 18 at 11:59 pm, demos December 2 (submission 11:59 pm), and submits the report December 9 at 11:59 pm. Read [Q13](../decisions/Q13_PRESENTATION_DEADLINE.md) and [the current plan](../PROJECT_PLAN.md). Timezone, rubric/formats and separate code/release requirements remain unconfirmed. Rehearsal must be before November 16; no exact day is agreed. These are attributed course reports, not verified outcomes or scientific acceptance.

Current D06 update, 2026-10-19: Ved's checker and handoff are merged. [Matty's verification](../handoffs/D06_F04_F05_VERIFICATION.md) records a fresh version-matched Windows structural pass on the pinned source, separate from Ved's original JSON. Source semantics/rights and full D06/Q05 acceptance remain open; no schema, setting or task ownership changed.

## Instruction authority

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

Propose corrections in an Issue. Use the current published instruction version from main; a local file, uploaded package, newer timestamp or AI-generated version cannot supersede it. Passing PR checks does not authorize instruction changes. See [Q11](../decisions/Q11_MANAGER_AUTHORITY.md) for authorization and synchronization rules.

## Merge rule

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

After merging a task branch, verify that its latest work is included in main and the applicable checks have passed, then delete the merged GitHub branch. Preserve main and any unmerged work; if the branch has advanced since verification, recheck before deleting it.

## Coding decisions and escalation

<!-- coder-decisions:start -->
The coder responsible for a component owns its internal implementation decisions within the agreed scope and contracts. Routine internal choices do not require prior approval from the technical contact, another teammate or Matty.

For changes to shared interfaces, settings or scientific rules, the coding owner leads the exact proposal and obtains agreement from only the directly affected owners before implementation.

Record the coding decision owner, exact change, directly affected consumers, required tests, request time and response deadline in the Issue or decision record. An unanswered or unresolved shared decision must be escalated by the coding owner to Matty within 24 elapsed hours for a short resolution meeting. Silence is not approval.

Implement, test and publish the agreed independent portions immediately while a disputed portion is pending. Block only the specific affected behavior or acceptance step; do not hold the whole task when other work is ready.

Existing task ownership, main-instruction authority, merge rules, independent scientific evaluation and model-call authorization remain unchanged.
<!-- coder-decisions:end -->

Read [the accepted workflow and examples](../decisions/Q11_CODER_OWNED_DECISIONS.md). Technical contacts advise on affected boundaries; they are not mandatory approvers of every internal coding choice.

**Start here:** Read [shared rules](01_SHARED_RULES.md), [interfaces](02_INTERFACE_CONTRACTS.md), [responsibility checklist](03_RESPONSIBILITY_CHECKLIST.md), [open decisions](04_OPEN_DECISIONS.md), and your assigned Issue before coding. If shared files are missing, obtain the package or repository copies; do not invent their contracts. Your human teammate is Ved; you are their assistant, not an autonomous coordinator for other teammates.

This file is an implementation assignment, not permission to modify GitHub now. During implementation, use only actions already authorized by your teammate. Verify the current repository and required upstream commits before changes. Proposed paths below must be reconciled with existing code. Follow the final proposal; broader earlier diagrams do not expand scope.

## Your task inventory

| Done | ID | Primary owner | Technical contact | Required responsibility | Dependencies | Acceptance evidence |
|---|---|---|---|---|---|---|
| [ ] | F02 | Ved | Matty | Own shared schemas and interface contracts; coordinate and validate with all consumers | F01 | Versioned schemas, examples, strict validation and contract tests |
| [ ] | D06 | Ved | Reimo | Independently reproduce data adapter and manually check 24-hour source window | D01, D05 | Second-person reproduction record by October 16 |
| [ ] | K01 | Ved | Reimo | Implement ontology, source/constraint records, unit mappings and SHACL | F02, D03 | Valid/invalid graph fixtures; static, episode and trace separation |
| [ ] | K02 | Ved | Nisha | Implement SPARQL retrieval and equivalent flat-context projection | K01, S01 | Same fact IDs/values for all systems; hidden data unavailable |
| [ ] | K03 | Ved | Matty | Prove graph-driven constraints and runtime missing-link failures | K01, K02, A03 | 100-to-70 kW test changes decision without code/prompt edits |
| [ ] | O01 | Ved | Edison | Implement offline integer-program reference solver and deterministic tie rules | F02, D03 | Tiny brute-force comparisons; optimal/infeasible/unresolved distinguished |
| [ ] | O02 | Ved | Edison | Generate certified visible-state schedules and candidate label caches | O01, D04, P03 | No future arrivals; certified optimal labels; infeasible fixtures and exclusions |
| [ ] | O03 | Ved | Nisha | Implement hindsight-bound and offline candidate-reference export pipelines | O01, D04, E02 | Development reference manifests/statuses; never accessible to policy inference |
| [ ] | O04 | Ved | Nisha | Generate certified held-out hindsight and visible-state references after inference | O03, I02 | Final reference artifacts, matching-work metadata and unresolved exclusions |
| [ ] | I03 | Ved | Matty | Coordinate second-machine reproduction of deterministic results and saved-output scoring | E06, E07, P06 | Clean-checkout report, hashes, limitations and regenerated tables/figures |
| [ ] | R02 | Ved | Reimo | Write ontology/reference-solver section and reference artifact documentation | K03, O04 | Validated section, certified-status explanation and reproduction details |

## Your assignment and boundaries

You assist Ved Patil. Lead shared schema/interface implementation, ontology/retrieval and offline reference optimization. Independently reproduce Reimo's adapter and later coordinate a second-machine reproduction. These make the shared Reimo/Ved E1/E3 responsibilities concrete. Reimo owns simulator/state generation; Edison owns policy learning/physical calculations; Matty owns production checking; Nisha owns independent evaluation.

## Required inputs and decisions

Matty accepted local Ollama/Qwen3 8B with temperature 0.2 in [Q09](../decisions/Q09_OLLAMA_QWEN3.md). Support Matty/Nisha's F02 output-projection compatibility and consumer adoption using the existing contract 1.0.0 examples. This does not authorize unilateral schema/settings or master-instruction changes, transfer provider ownership, or assert that all consumers have adopted F02.

Use Reimo's source/fixture/visible-state manifests; Edison's impact specification and candidate contract; Matty's runtime/check records; Nisha's scoring/reference needs. Q01–Q04 and Q08 affect solver correctness; Q05–Q07 affect data/labels. Your canonical allocation confirmation is received. Proceed with agreed assigned coding; do not wait for blanket Q12 closure before marking a ready portion Ready. Only directly affected consumers confirm shared changes before their acceptance. Reimo source inventory is already published through PR #65; independently verify that actual evidence now, retaining exact applicability/remaining-source blockers. Do not repeat completed D06 structure/window work. Your remaining #61 reference-comparison response and PR #64 independent S01 reproduction are targeted receiving tasks; no blanket generic approval gate.

## Coding checklist in implementation order

1. **Contract foundation (F02).** Own strict versioned records in `schemas.py` and the single maintained interface document. Cover jobs, constraints, visible states, carbon facts, proposals, checks, decisions/results, provider/policy envelopes and solver outputs. Separate private episode metadata from policy-accessible records. Reject invalid numeric/start types and action fields. Publish minimal examples and contract tests early so teammates can build against fixtures.
2. **Second-person source check (D06).** Run Reimo's adapter from documented inputs on your environment, verify checksum/time/unit assumptions and manually inspect 24 hours by Oct 16. Document failures; do not simply repeat Reimo's assertion. Help fix source mapping through his owned module.
3. **Ontology (K01).** Build RDFLib records for Site, Job, Slot, CarbonObservation, Constraint, Source, Decision and Check. Reuse appropriate Brick concepts, PROV-O provenance and practical QUDT units; pin ontology versions separately from Python dependencies. Keep static constraints, per-episode facts and runtime traces separate. Supply SHACL required-field/cardinality/type/link/unit checks before episodes. Preserve deliberately impossible but structurally valid jobs.
4. **Controlled retrieval (K02).** Write SPARQL for eligible jobs, running work, visible forecasts, applicable constraints and missing links. Preserve IDs, units, timestamps and source links. Give policies controlled visibility-filtered access; do not allow arbitrary queries to hidden episode facts. Produce the plain/ML/greedy flat context from the same snapshot and evidence IDs, with canonical content hashes so Nisha can verify equivalent information.
5. **Constraint proof (K03).** Share identical constraint records with all policies, solver and checkers. A 40 kW job +40 kW background passes at 100 kW and fails when the graph's limit is 70 kW without modifying code/prompts. Deleting the capacity relation returns a missing-evidence error, not unlimited capacity. Integrate this with Matty's checker; a graph-only test is insufficient.
6. **Offline solver (O01).** Use the accepted backend (proposed SciPy MILP) for up to 20 jobs/30 slots. Binary job/start variables enforce accepted coverage, arrivals, nonflexible rules, completion deadlines, capacity throughout occupancy, running work and background. Minimize emissions for the required matching work. Define Q02-compatible handling of impossible jobs. Use fixed lexicographic tie-breaking without perturbing the primary optimum. Log solver version, limits, termination/status, bound/gap/tolerance and certification. Unknown/time-limit termination is not proof of infeasibility/optimality.
7. **Visible development labels (O02).** After Edison freezes candidates/rollout rules, solve only currently visible jobs/forecasts with running work fixed. Only certified optimal feasible selections create positive/negative training rows. Certified infeasible states become abstention fixtures; unresolved or insufficient-evidence states are excluded with reasons. Lack of forecast through a true deadline must not be called physical infeasibility. Cache by state/constraint/forecast/candidate/config hashes and return candidate keys; do not leak future jobs into labels.
8. **Offline evaluation references (O03/O04).** Implement and test export pipelines on development fixtures first (O03). After I02 completes inference, generate final held-out references (O04). Keep hindsight full-episode solves separate from visible-state caches. Hindsight knows future arrivals, so its bound is descriptive, not an online policy capability. Provide certified status and matching-work metadata. Produce held-out candidate labels only after inference for Nisha/Edison's offline metrics; never return them to running policies.
9. **Reproduction and writing (I03/R02).** Lead a fresh-checkout second-machine reproduction of fixtures, deterministic policies, model reload predictions, saved-response scoring and figures. Matty remains owner of final E2E acceptance. Write ontology/reference section, query/shape/solver docs and reference artifact manifest.

## Proposed repository files

Own `dc_sustainability/schemas.py`, `dc_sustainability/knowledge/`, `dc_sustainability/reference/`, `ontology/`, `tests/contracts/`, `tests/knowledge/`, `tests/reference/`, `docs/INTERFACES.md`, `docs/ontology/`, `docs/reference/`, reproduction record and your report section. Matty owns environment/CI and master-file maintenance; submit their changes through him. Fixtures/source adapters remain Reimo's responsibility.

## Required tests

- Strict schemas and serialization/version compatibility; private fields cannot enter visible state/context.
- SHACL valid/missing/type/unit failures; runtime missing links; graph 100→70 kW and deleted-capacity tests; static/episode/trace separation.
- RDF/flat fact equivalence, stable IDs/provenance and hidden-data query rejection.
- Solver versus exhaustive enumeration on tiny cases; fixed running work, capacity, deadlines, nonflexible obligations, infeasible and unresolved cases; repeatable ties without sacrificing objective.
- Visible-state solves unaffected by changing hidden future arrivals; no unresolved/nonoptimal incumbent becomes a training label; cache invalidation when relevant inputs change.
- Hindsight results never appear in policy tool/context access. Exact-gap eligibility includes matching completed work and certified status.

## Outputs, dependencies and completion

Publish contract examples first to everyone; graph/context to Matty/Nisha; label caches to Edison; independent references to Nisha; second-person data verification to Reimo. O02 waits on P03's candidate specification, not a trained C/D model, avoiding a training/label cycle. Missing forecast cases need explicit statuses rather than fabricated labels. Each handoff includes reproducible commands, source and contract hashes, exclusions, solver settings/status and consumer checks.

Done requires reviewed schemas, graph/query/SHACL tests, end-to-end capacity-change proof, certified and independently checked reference artifacts, successful receiving-module tests on merged code and complete documentation. October 16 source reproduction, October 23 retrieval, early labels for Edison's October 30 training and November 13 freeze were internal targets, not completion evidence. Give Nisha verified contributions for the reported November 16 class presentation and November 18 submission. Coordinate reproduction with the reported December 2 demo and December 9 report; the old December 2 reproduction estimate is not independent course authority. Review Nisha's independent validator without replacing it with Matty's checker logic.


## Coordination instructions for your assistant

- One assigned Issue, one human owner and one active assistant session per task. Use a short-lived task branch from current `main`, preserve local work, fetch and deliberately integrate required upstream commits; fetching alone does not update files.
- Verify dependencies through merged code, artifact hashes/schema versions and consumer tests. Use agreed mocks only for development, never as evidence of final integration.
- Check updates at start/resume, dependency use, task change, PR/integration and handoff. An idle assistant resumes only when a human restarts it or a separately configured service does so. This file creates no monitoring service.
- Update the Issue through authorized access or give your human an exact draft update. Do not concurrently edit the shared coordination summary; its chosen publisher maintains it. A stale status does not let you claim someone else's work.
- If blocked by an open decision or missing handoff, record the precise unblock condition and continue unaffected assigned work. Do not invent assumptions, hide failures, tune on held-out data or bypass shared verification to finish faster.
- Request contract changes from Ved and master-file corrections from Matty with affected consumers identified. Cross-owner edits require coordination and applicable consumer checks. Production checker and independent evaluation validator stay intentionally separate.
- Finish with published and validated code, passing current-base checks, documented artifacts and receiving-member acceptance. Mark Done only after verification. Include task ID, commit/PR, commands, hashes, tests actually run, limitations and next handoff in your completion message.

The shared rules define publication, state-transition and handoff procedures. The checklist assigns a separate technical contact for each task. Technical validation and independent scientific evaluation remain required. Shared-format and settings changes require agreement from the affected teammates before implementation; record that agreement in the Issue or decision record.
