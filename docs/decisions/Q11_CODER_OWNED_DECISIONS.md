# Q11 amendment: coder-owned decisions and 24-hour escalation

Status: accepted workflow instruction from Matty Anderson (MattyAnd), October 24,
2026, America/Phoenix. Effective when published on main as instruction 1.25.
Authorization: Matty explicitly approved the proposed coder-led rule and requested
the announcement first, followed by consistent master updates. [Announcement](https://github.com/ReymoT/data-center-agentic/issues/57).
This workflow amendment does not select an unresolved scientific rule, change a
shared format/setting, transfer a task, or certify implementation acceptance.

## Rule shared by all assistants

<!-- coder-decisions:start -->
The coder responsible for a component owns its internal implementation decisions within the agreed scope and contracts. Routine internal choices do not require prior approval from the technical contact, another teammate or Matty.

For changes to shared interfaces, settings or scientific rules, the coding owner leads the exact proposal and obtains agreement from only the directly affected owners before implementation.

Record the coding decision owner, exact change, directly affected consumers, required tests, request time and response deadline in the Issue or decision record. An unanswered or unresolved shared decision must be escalated by the coding owner to Matty within 24 elapsed hours for a short resolution meeting. Silence is not approval.

Implement, test and publish the agreed independent portions immediately while a disputed portion is pending. Block only the specific affected behavior or acceptance step; do not hold the whole task when other work is ready.

Existing task ownership, main-instruction authority, merge rules, independent scientific evaluation and model-call authorization remain unchanged.
<!-- coder-decisions:end -->

## Existing coding owners

| Decision lead | Existing implementation scope |
|---|---|
| Reimo | Data preparation, episode generation, source mapping and simulator behavior |
| Matty | Provider transport/accounting, production checker, controller, agent and integration |
| Ved | F02 schemas/contracts, ontology/retrieval and reference solver |
| Edison | Impact implementation, greedy/learned policies, fallback and training |
| Nisha | Plain/explanation paths, independent evaluation, sampling, rubric, scoring and runner |

The [50-task checklist](../team/03_RESPONSIBILITY_CHECKLIST.md) retains exact
primary owners, technical contacts and prerequisites. The human coding owner leads
decisions for that assigned component; their assistant implements within existing
authorization. A technical contact is consulted where affected, not added as a
routine approval gate. For a shared change name one lead coder in its Issue; other
component owners confirm only their affected boundary and required consumer tests.
Keep that lead until resolution instead of passing the decision through a chain.

## What the coder can decide immediately

Within agreed contracts and science: private helper structure, names of internal
functions, local algorithm implementation, test organization and a bug fix that
restores already agreed behavior. Implement and test, document the reason in the
PR, and use the existing checks-based merge rule. No extra teammate or manager
approval is required for those internal choices. This does not authorize a change
to another owner's module, public interface, dependency lock or runtime setting.

Examples: Edison can refactor a private greedy-A helper; Nisha can organize the
independent arithmetic implementation; Matty can implement a demonstrated transport
bug fix that preserves agreed public behavior. Source pollutant meaning is an
evidence question, not a value a coder may invent. A change to a simulator's arrival
visibility affects checker/policy/scoring consumers and needs their exact agreement.

## Shared decision record and clock

Use the existing task Issue or decision record. State: one coding decision owner,
the exact proposed behavior/interface/settings change, directly affected consumer
owners, reason, required tests, the request timestamp and response-by timestamp in
UTC. The response deadline is 24 elapsed hours after the exact proposal is posted,
not 24 working hours. Consumers answer with agreement, an exact alternative or an
explicit blocker; the lead keeps ready coding moving.

If unanswered or still unresolved at that deadline, the lead escalates to Matty in
that Issue for a short resolution meeting. Matty coordinates and records the
resolution with affected owners; escalation alone does not waive their agreement.
Existing unresolved shared requests already older than 24 hours should be escalated
using their original timestamps. Do not reset the clock with repeated reminders
or ask again for a reply already received. No automated monitor/meeting is created.

Only the disputed behavior or dependent acceptance is blocked. Develop, test and
publish actual agreed independent portions on existing interfaces/allowed fixtures.
Record partial completion honestly; mocks, stubs, fixed passing verdicts or invented
ratings/results are not completed functionality. Continue to distinguish development,
integration and final scientific acceptance. A pending optional field must not hold
up agreed work that leaves the field unused.

## Verified example motivating the change

E01 issue #24: [proposal](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6352265192)
posted October 22 at 15:01:14 Phoenix (22:01:14 UTC); [agreement and PR checkpoint](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6379718135)
posted October 23 at 21:13:22 Phoenix (October 24, 04:13:22 UTC).
Elapsed: **30 hours, 12 minutes, 8 seconds**. This is coordination elapsed time,
not measured coding effort or proof that anyone was idle. The E01 agreed scope
was confirmed while optional scalar precision remained separate; do not claim all
E01 scientific gates closed. The new rule removes avoidable internal approvals
and bounds escalation of genuine shared questions without inventing agreement.

## Publication and future consistency

AGENTS, PROJECT_MASTER, all five role masters and shared rules carry the exact
same rule. All ten numbered/role headers and changelog advance together to 1.25.
The setup validator checks policy consistency in those files and this record.
Matty still alone authorizes master/instruction changes; main stays authoritative.
Passing checks permits merge, teammate review remains optional, and affected-owner
agreement for shared changes remains required. No account permissions or branch
protections were changed. [Publication handoff](../handoffs/CODER_OWNED_DECISIONS_2026-10-24.md)
records actual checks and the eventual PR/main evidence.
