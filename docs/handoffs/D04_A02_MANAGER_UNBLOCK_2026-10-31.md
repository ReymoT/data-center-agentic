# October 31 manager unblock: D04 receiving and A02 portability

## Why this work moved now

The project deadline is close and two independently reproduced technical defects
were holding ready work. Matty made the narrow manager decision to implement the
safe, testable fixes now while preserving Reimo's delivered D04 materialization
and Nisha's receiving findings. This does not turn silence into scientific
agreement and does not authorize a model or study run.

## D04 development forecast decision

The development-only adapter uses persistence. At decision slot `t`, it reads
only the source row immediately before the row associated with slot `t`. That
prior value is issued at the current row's timestamp and projected through the
visible horizon. Therefore, a policy never receives the realized value for slot
`t` or any later slot. Realized carbon remains private and is used separately for
outcome scoring.

This is the smallest causal adapter that lets P03 create candidate rows without
inventing a forecasting model or exposing future realized values. It is
provisional development evidence only. Source interval meaning, pollutant/system
boundary, data rights, Arizona suitability, held-out isolation and the Q05/Q06
scientific freeze remain unresolved.

The exact 40 allocation IDs, scenarios, seeds, windows and 16/12/12 folds are
unchanged. A new v2 public receipt records the newly materialized persistence
episode hashes; Reimo's v1 receipt remains as historical evidence.

## Receipt verification correction

Episode bytes and code hashes remain strict. The verifier now excludes the
recorded Python/dependency environment from equality because two machines can
produce identical episode bytes with different patch or package versions. The
environment is still required and retained for provenance. Tests prove that an
environment-only difference passes while a changed code hash fails.

Windows hosts without symlink privilege skip only the symlink fault case instead
of failing before the verifier can be exercised. Other corruption, missing-file,
extra-file and receipt mutations remain failures.

## Actual bounded receiving evidence

Using the exact pinned source in private local custody and a newly regenerated
40-episode corpus:

- 40 F02 round trips passed.
- All 40 episodes completed 30-slot S01 replay.
- P03 collected 120 representative decisions and 813 candidate rows.
- Bounded O02 checks returned certified-optimal results for one decision in each
  scenario and produced 30 usable training rows in total: 10 infeasible, 4
  limited, 15 normal and 1 spike.
- No source CSV, complete episode, realized-carbon array or held-out artifact was
  committed.

These numbers show interface readiness only. They are not trained-model results,
study outcomes or scientific source acceptance.

## A02 portability and admission corrections

The EP-HAND1 freeze now uses the repository's LF-stable bundle hash, matching the
experiment runner on Windows, Linux and macOS. The authorization test calls the
same LF hash function as the runner.

Model-unit admission now reserves the smaller of the system's slot/call-cap worst
case and the provider ledger's strict per-unit cap. This preserves the global
budget while allowing the proposed EP-HAND1 configuration (`24` combined and
`18` per unit) to admit the Agent after Plain. A regression test runs Plain and
Agent under those exact caps with a synthetic loopback responder. This is offline
test evidence, not inference.

## Remaining gates

- Ved must still explicitly respond to the proposed single-use EP-HAND1 bounds.
- Matty must record fresh authorization before any model request.
- Edison must run the full P03/O02/P04 development pipeline on the accepted
  materialized corpus; the bounded checks here do not replace that work.
- Q05/Q06, held-out allocation/isolation, full experiments and final evaluation
  remain open.
