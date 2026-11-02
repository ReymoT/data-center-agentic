# I01 lock, P05 integration and private replay preparation

Matty implemented Nisha's [independent review correction](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6588937100)
and prepared the remaining independent work without another teammate assignment.

## Corrected candidate

The [offline candidate](../evidence/i01-offline-config-2026-11-02.json) now pins
LF-normalized lock bytes, matching the runner CLI:
`38562754e7ff8c500933a48f8c497799e1ac6af0fa7602d3df312195cef9034c`.
Its production-code revision is `f309256be966107d6dd4ae3297ba66a409012920`,
including P05-to-E02 integration. Its new identity is `RUN-3d6ec9e70279`.
The old offline candidate is retained under `superseded_offline_candidate`.
Original completed runs and the six-unit/180-trace evidence index are unchanged;
their Windows checkout-byte lock hashes remain historical provenance.
No model request is authorized by this correction or by the candidate's bounds.

## Actual P05 runner receiving

E02 now calls the same P05 proposal factory as the standalone adapter. Both paths
validate state/context and the trusted current time before forecast assessment.
Missing/stale/future/partial coverage selects Greedy A, which traverses the real
checker/controller and is retained as a fallback stage under the requested C/D
system. A classifier exception or invalid probability remains an error, never a
substitute-policy retry. Run configuration and F02 records are unchanged.

Both actual manager-host P04 binaries were reloaded with digest verification and
run through E02 on public EP-HAND1 and a public test variant with forecasts removed.
This is development receiving, not a study cohort or held-out experiment.

| Mode | Run | Per C/D system result |
|---|---|---|
| Original public forecasts | `RUN-48c79fa7c73e` | 30 traces, 2 completed jobs, 0 fallback records |
| Forecasts removed for test | `RUN-a59b2c3bbd77` | 30 traces, 2 completed jobs, 3 checked fallback records |

All four units have zero independent E01 Option B replay findings and zero
EpisodeResult mismatches. No LLM calls or held-out access occurred. These runs
do not replace earlier receiving records or establish a unified six-system result.

## Prepared private development replay packet

Nisha's index review is independent structural verification, not content replay.
Matty prepared `development-replay-packet.zip` under manager-local custody label
`I01_Private_Receiving_2026-11-02`, outside Git. It contains the six original result
files and all 180 original traces, plus a relative-path/SHA-256 inventory.
Every source file and every ZIP member was verified against the published index.
The packet excludes model binaries, training labels, source data, runtime logs,
human originals and all held-out material. The public EP-HAND1 bundle is already
committed and is the replay input.

Archive SHA-256:
`2434b3a0fb8d595f1e864755ba1172a230e17101fbae580d9960cbc32d7ff12f`.
No packet was transferred, no recipient access was tested and no receiving PASS
is inferred. Before a transfer, authenticate the evaluator/destination and permitted
channel, verify the archive digest out of band, unpack into a fresh restricted
directory, verify all 186 entries and independently replay all six results against
the indexed public bundle. Retain PASS/FAIL, exact code and environment. Do not
reuse this manager/training-host location for held-out custody.

## B5 offline preparation and remaining limits

[Nisha's custody conditions](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6588980217)
are received: no outcome-driven seed search/retry and isolation must cover
forecast history. The new offline `data.forecast_isolation` utility checks scoring
overlap and both directions of history-to-scoring leakage under explicit start/end
hypotheses. It requires explicit dates and history length, refuses empty window
sets and year wrapping, and reads no source observations or allocation metadata.
Tests cover generic day-14/15 tails, separated scoring windows with history leakage,
month/year edges and both interval hypotheses. No actual cohort is passed to it.

A continuous lookback is a conservative envelope, not an adopted forecast method.
The actual study forecast, exact restricted parameter receipt, storage ACL/deny
checks, authoritative B1-B3 source evidence and independent custody acceptance
remain unresolved. No nonce was generated, real cohort selected, private path
approved or source/scientific freeze declared. #60 and #95 remain open.
