# Nisha contribution statement — development draft

Nisha Mahadev Kolekar (nkolekar-nk) owns the plain-LLM comparator, explanation
rendering, independent evaluation, experiment running, reliability reporting and
report assembly (L01-L02, E01-E04, E06-E07, I02, R05). This expands her section of
the private Overleaf draft.

**Comparator and explanations (L01-L02).** Built the plain-LLM comparator on the
shared Ollama adapter, including the empty-queue no-op without a model call, and the Agent explanation renderer (#124, #127).

**Independent evaluation (E01, E03).** Wrote the decision validator, claim reference
and episode replay separately from the production checker, with arrival option B
(#85, #87); the equal-work savings comparison and the block on savings when replay
findings invalidate execution (#89, #106); and the run-level metrics, paired
episode/date resampling and forecast-tie rate (#171, #174, #175).

**Experiment running (E02, I02).** Built the deterministic and Plain/Agent runner
units, fail-closed model attempts, trained C/D units and the public EP-HAND1 bundle
(#110, #113, #128), the checked 300-run matrix, and the I02 pre-freeze checklist and
validator with its refreshes (#119, #169, #194).

**Faithfulness review and reliability (E04, E07).** Drafted the claim-extraction
rule and its clarifications through rules 11.6-11.9, the blinded development cases
and calibration packet, review sampling and the abstention-boundary stratum, the
blinded study packets (rule 11.10, #215) and the LaTeX table renderer (#216, E06).
Supplied original development ratings, the agreement statistics and the development
inter-rater reliability report (#91, #92, #104, #193); the joint adjudication
record is kept separate from the original labels.

**Receiving.** Reviewed development runs as the separate-person receiver
and reports independent 26-check receiving of the November 12 metadata-only
held-out date selection. Matty accepted the authenticated public handoff without
receiving the private metadata/report or rerunning those checks. These scoped
checks do not establish operational custody, source-read permission, episode
content materialization or scientific acceptance.

**Report (R05).** Wrote the evaluation, introduction/problem and related-work drafts
and the report outline, and assembles the final report in the IEEE Overleaf project.
Held-out ratings, reliability and findings remain future work.

Project-written evaluator, runner, rules and analysis code are distinct from
third-party components: Ollama/Qwen3 8B and the pinned Python packages keep their
own terms. AI coding assistants were used. The cited merged PRs provide the available
review and validation history; this statement does not certify every individual
change as independently reviewed or tested. This is a contribution/evidence statement, not a license
grant.
