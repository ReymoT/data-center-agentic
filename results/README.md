# Results and trace preparation

Nisha owns experiment/scoring manifests. Matty owns per-decision runtime record format. No results are delivered by this scaffold.

Keep initial, repaired, fallback, final and executed outputs/checks separately, with stable run/episode/slot IDs, input/config hashes, actual performed checks, evidence, raw responses, errors, attempts/tokens/cost/timings and status. Null stages are not passing stages. Generated/private run content is ignored; validated permitted manifests link artifacts and hashes. Do not store secrets or sensitive paid-response content in Git.

All 300 planned held-out runs or accounted failures, original outputs, independent ratings/adjudication and scoring inputs must survive reproduction. Save original API outputs because regeneration may differ. Record access/retention through Q13.
