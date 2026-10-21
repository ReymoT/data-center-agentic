# Q03: proposal to expose a time-infeasible arrival for one decision

Status, October 21, 2026: proposed, not adopted. No simulator, policy, context, checker or evaluator behavior changes in this publication. [Nisha proposed option B](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6308222681); [Matty supports its direction and asks for the exact boundary confirmations](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6322088311). Passing checks or Matty's maintenance authorization does not supply the other owners' agreement.

## What current code does

The provisional D03 infeasible scenario assigns one job a deadline equal to arrival plus duration minus one. S01 marks a waiting job missed at the first boundary where no legal start remains, including its arrival boundary. E01 replay independently follows that draft behavior. Thus this job is absent from the policy's waiting queue before the policy can respond. Inspection and actual generation over development seeds 0–9 found exactly one impossible-on-arrival job in each episode, matching the intentional-infeasibility flag. This is generator evidence, not model or integrated-run evidence.

Nisha and Matty support the current-behavior scoring interpretation: a job never presented to the policy is outside decision-level coverage and earns no abstention credit. It still appears in the episode's missed/unfinished outcomes and earns no completion credit. Report missed-on-arrival separately from missed-after-waiting. A slot with no waiting jobs remains an empty-queue no-op. Full protocol agreement and implementation remain explicit gates in the [Q01–Q04 ledger](Q01_Q04_AGREEMENT_STATUS.md).

The present infeasible scenario can demonstrate miss accounting. It cannot, by removing this job before any policy sees it, establish that a model recognized its infeasibility or abstained appropriately. Supplied-state validator fixtures remain unit evidence rather than runtime behavior claims.

## Exact recommended change

1. A job already time-infeasible on arrival is visible as waiting for its arrival decision only. If it cannot start, it becomes missed at the next boundary. This recommendation is about that arrival exception; it does not delay the ordinary miss boundary for jobs that were previously feasible and waited too long.
2. Keep every legal start, deadline, duration, capacity, nonflexible obligation and completion boundary unchanged. The visibility exception never permits an impossible execution.
3. Every system covers every visible waiting job under the agreed Q03 rule. Feasible work continues in a mixed decision. An abstention earns credit only when the independent evaluator confirms its justification; missing evidence is not proof of physical infeasibility.
4. Apply one agreed rule consistently across S01, equivalent graph/flat views, all six policies and fallback, A03/A04, independent E01 replay/scoring and runner records. Do not activate only one side of the comparison.
5. Record the effective protocol version and actual affected-owner agreement before changing code or freezing fixtures/sampling. No F02 schema change is selected; Ved must confirm whether existing records suffice.

## Required affected-owner replies

| Owner | Reply still needed for the exact change |
|---|---|
| Reimo, S01/D03 | Confirm arrival-only exposure and next-boundary miss, with ordinary miss timing preserved. |
| Edison, P01/P02 and learned policies | Confirm coverage, checked fallback and infeasible-job behavior; also supply the outstanding Q01–Q04 response. |
| Ved, F02/K02/O01 | Confirm equivalent context, record compatibility and reference/certification treatment, including joint contention/Q08. |
| Nisha, E01/E02/E03 | Confirm these exact boundaries in independent replay/scoring and runner records. Her original recommendation is recorded; this is the requested implementation boundary confirmation. |
| Matty, A03/A04 | Direction supported in the linked reply; production checks/gate must still reject impossible starts and require actual consumer evidence. |

The [consolidated owner request](https://github.com/ReymoT/data-center-agentic/issues/33#issuecomment-6322132165) asks for agreement, an exact alternative, or a blocker and checkpoint. Silence is not agreement.

## Tests required after agreement

Test an impossible arrival at its arrival and next boundary, mixed feasible/impossible arrivals, ordinary last-start expiration, nonflexible timing, empty-queue transitions and the completion boundary. Reject every illegal execution. Independently verify justified abstention and unchanged missed/unfinished/completion accounting. Check identical policy visibility and preserve real executed records separately from proposed plans. These are future acceptance checks; none is presented as an implemented option B test here.
