# RULE-02 evidence (issue #240, PR #257)

Reviewer-accessible traces and reports for the RULE-02 implementation at commit
`176361ad23ba57940b1576828893ce3a7b1a1666`. Synthetic authored inputs only; model calls: 0.
Scores are artificial `score-kWh` weights, not measured carbon intensity or CO2e.

**What this is not:** not independent RULE-03 verification (issue #241), not Matty's implementation acceptance,
not a scientific freeze, not authorization to run anything. The reader reports `binding_validation: INCOMPLETE`
(see below), so no PASS of the evidence as a whole is claimed.

## Why these traces replace the earlier ones

The earlier sandbox traces bound `code_commit` to `c42376e94e7558cdd980c45a57150ab24c0b09ab`, a SHA that is not in
the published history. The published implementation is `176361a`. Its Git tree (`22b31ab5fb3dcf055cf91f6a7420d2c89660d75c`)
is identical to that of `c42376e`, so the code is the same, but the old traces were neither reviewer accessible nor
bound to a published commit. These traces were regenerated from a clean checkout of `176361a`; no trace metadata was edited.
Every one of the 310 result/decision records carries `bindings.code_commit` = `176361a…`.

## Layout

| Path | Content |
|---|---|
| `MANIFEST.json` | Every file here (except itself) with sha256 and size, the implementation/documentation/base SHAs, per-trace result and case hashes, and the generation commands |
| `traces/<policy>/<case>-<policy>/` | `case.json`, `result.json`, `decisions/` (30 records), `states/`, `snapshots/`, `transitions/` (actual simulator transitions), `.intents/` (runner intent markers) |
| `compat/verify-<policy>.json` | Complete output of `scripts/verify_rule_study.py` (the RULE-03 reader), with `.stdout.txt` and `.exit.txt` |
| `compat/replay-from-saved.json` | Replay of every committed trace from its saved files only (also `.stdout.txt`, `.exit.txt`) |
| `compat/commands.txt` | The exact compatibility and replay commands |
| `meta/environment.txt`, `meta/pip-freeze.txt` | Interpreter, OS, git version, requirements hashes, installed packages |
| `meta/demo.stdout.txt`, `meta/demo.exit.txt` | Output and exit code of the generation command. Its `trace:` lines show the sandbox output directory, not a repository path; the traces were copied here unchanged |
| `tools/replay_from_saved.py`, `tools/build_manifest.py` | Reviewer tools (standard library plus the repo's own package) |

Ten case/policy runs: A, B, B-progress for each of rules-v1, greedy_a and greedy_b, plus B-fault for rules-v1 only.

## What the reader did and did not validate

`scripts/verify_rule_study.py --traces` reads the folders with the merged strict trace reader and checks case content,
the specification hash, decision-list hashes and within-trace consistency, then evaluates S1-S5, P1/P2, R04 arithmetic
(rules-v1 only) and state-hash continuity. It exits 2 (INCOMPLETE) for every policy because external adapter, generator,
environment and code artifacts and raw state/transition bytes are not supplied, so the six bindings cannot be authenticated by the reader.
PASS entries mean "no violation in the supplied records", not that the study or the bindings are accepted.

## Reproduce

See `MANIFEST.json` `generation_commands` and `docs/handoffs/RULE02_IMPLEMENTATION.md`. Check this directory with
`python docs/evidence/rule02/tools/build_manifest.py check`.
A regenerated run is not byte identical (the production checker mints random check ids); its behavior and bindings are the same.
