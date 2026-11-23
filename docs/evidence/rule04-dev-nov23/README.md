# RULE-04 development handoff — November 23 (Edison, #242)

Retained development-seed files and first metric records for Nisha's independent
accounting receiving. Development only: no final seed was drawn, and no policy,
checker, simulator or model ran to produce these files.

| File | What it is |
|---|---|
| `development.cases.json` | Policy-visible development set, seed 2026111901, 120 cases (40 per stratum). Missing-forecast scores are null |
| `development.accounting.json` | Evaluator-only sidecar: all 30 weights per case, keyed by case ID and full/workload hashes, bound to the case-set hash. Never a policy input |
| `development.case-check.json` | Nisha's case checker on the visible set: overall PASS (one set, so unseen isolation is INCOMPLETE) |
| `development.accounting-check.json` | Nisha's accounting checker on the case/sidecar pair: overall PASS (binding, coverage, identity, weight domain, visibility, hidden profile); binding authentication NOT_ESTABLISHED, study acceptance NOT_ESTABLISHED |
| `authored-first-metrics.json` | First metric records computed from the retained authored native-continuation traces (`docs/evidence/rule03-nov23-native/authored-artifacts.tar.gz`, producer `dbb8e6f`) |
| `SHA256SUMS.txt` | SHA-256 of the five files above |

Producer: main `c047af5` (instruction 1.30), generator source
`ab7950847683a8411e906de06bf12346db9b3fc74cb302718d586399d5df4072` (the pin Nisha
verified), specification `9597931f...a8542bd`. Development report: attempts 63/40/84;
distinct workloads 40/39/40 (two overload cases share a workload and differ in scores).

## Reproduce

```
python scripts/generate_rule_study_cases.py --domain development --out-cases <new> --out-accounting <new>
python scripts/check_rule_study_cases.py --set <cases> --expected rule-study-20261119-v1-development=40 --out <new>
python scripts/check_rule_study_accounting.py --cases <cases> --accounting <accounting> --out <new>
python scripts/rule_study_metrics.py --label <label> --out <new> <extracted authored run folders>...
```

The generator output is byte-deterministic, so regenerated files should match the hashes.

## First metric records: scope and limits

The metrics are the ones accepted in #239: execution violations with checked-decision and
executed-start denominators, completed/missed/unfinished counts, turnaround and start delay
for completed jobs with counts, fallback attempts/selections/blocked decisions, artificial
score-kWh impact (recomputed from the case weights and checked against the producer total)
and equal-work reduction against Greedy A only on matching job-outcome sets.

They cover the 10 retained authored runs (A, B, B-progress for three policies; B-fault for
rules-v1), not the 120 development cases. No policy has been run on the development set:
that is a separate rollout needing its own bounded authorization. Headline: zero execution
violations; in A, rules-v1 and Greedy B report 8,000 versus Greedy A's 12,000 score-kWh
(reduction 1/3, artificial units; an observed authored example, not a measured advantage); B-progress is equal (0); B has no starts for any policy,
so its comparison is unavailable (Greedy A total 0), never zero. Scores are artificial
weights, not g/kWh or emissions. Independent accounting receiving is Nisha's, still pending.
