# RULE-05 editable workflow figures

Reimo Tamme; November 23, 2026. Evidence baseline: main
`91e23b6f85c6240ec22d2a23e14f1eaf924427c4`, instruction 1.30.
[Methods and source evidence](RULE05_FOCUSED_STUDY_METHODS.md) govern both captions.
These Mermaid sources can be reused in the report and #246 demo. Status is written
in each node so grayscale reproduction does not depend on color. Neither figure
is a measured result. Export/layout in the final report remains the assembly owner's work.

## Figure 1. Research workflow

```mermaid
flowchart LR
    E["Permitted public illustration + authored assumptions<br/>Historical cb85 motivation; new A/B inputs"]
    S["R01–R09 rule specification<br/>Design accepted: RULE-01"]
    R["Executable rules-v1 + checked runner<br/>Implemented on main: RULE-02"]
    V["Independent safety / progress verification<br/>202 required traces fully replayed<br/>Independent receiving accepted within scope"]
    T["Isolated synthetic comparison<br/>rules-v1 / Greedy A / Greedy B<br/>Development pair + authored metrics available<br/>Independent accounting / unseen evaluation pending"]
    D["Report and two-scenario demo<br/>RULE-05 methods prepared<br/>Final evidence / integrated demo pending"]
    H["Original source-dependent Agent / Plain study<br/>Historical evidence only; study unperformed"]
    E --> S --> R --> V
    V -->|"Final comparison: whole-study freeze + exact authorization"| T
    R -.->|"Development preparation / retained authored reporting"| T
    T -->|"Actual matched outputs only"| D
    R -->|"Methods and implementation evidence"| D
    H -.->|"Separate context; no matched new-study result"| D
```

Caption: rules are hand-authored, not learned. The November 20 acceptance freezes
the specification design. Implementation and independent harnesses are available;
required bounded verification is complete and independently received within scope;
unseen synthetic findings remain pending. Original INCOMPLETE and host FAIL records
remain preserved. Primary S4 is NOT_RUN; all policies start zero jobs in the 12
infeasible primary cases. Optional extended coverage was not run.
The historical study is separate. Development preparation and saved authored
reporting can proceed before final evaluation; that arrow grants no execution
authority. Arrows describe dependencies, not completed gates.
RULE-04 generation/execution also requires the exact #244 freeze, receiving,
containment and fresh bounded authorization. No such run is authorized by this figure.

## Figure 2. Rules-v1 execution and separate verification

```mermaid
flowchart TB
    I["Visible arrived state + permitted forecasts / constraints<br/>Implemented input boundary"]
    R["R01–R09 deterministic proposals<br/>Implemented: scheduler.py"]
    C{"Production checker<br/>Implemented; unchanged"}
    G["Greedy A fallback proposal<br/>Implemented; unchanged"]
    GC{"Production check of fallback"}
    L{"Latest-state production recheck<br/>Read state + snapshot again<br/>Both reads stable?"}
    A["Approved current-slot starts only<br/>Future placements advisory; recompute later"]
    N["No approved plan: refusal / drain<br/>No new starts; time and running work advance"]
    X["Malformed / out-of-scope rules input or changed live state<br/>Stop without step; reconcile indeterminate effects"]
    M["Simulator<br/>Implemented; no new starts in slots 24–29"]
    T["Immutable trace publication<br/>Stages, checks, state / snapshot, transitions, commitments"]
    O["Independent oracle / checker<br/>Separate standard-library predicates<br/>Legal-action graph for joint feasibility"]
    P["Independent replay of actual policy path<br/>S1–S5 / eligible P1 / P2<br/>Bounded replay complete; received within scope<br/>Primary S4 NOT_RUN; 12 infeasible cases start zero"]
    I --> R --> C
    R -->|"R08 forecast unavailable"| G
    R -->|"R01 / scope rejection"| X
    C -->|"Fail"| G --> GC
    C -->|"Pass"| L
    GC -->|"Pass"| L
    GC -->|"Fail or unavailable"| N
    L -->|"Pass"| A --> M
    L -->|"Recheck refused / constraints changed"| N --> M
    L -->|"Live state changed"| X
    M --> T
    X -->|"Stopped / indeterminate record"| T
    I -.->|"Separately supplied case / records"| O
    O -->|"Eligibility; not production approval"| P
    T -.->|"Authenticated bindings required"| P
```

Caption: this is the rules-v1 candidate/fallback path. The common runner also
checks Greedy A/B proposals; it does not route every failed baseline check through
another Greedy A attempt. Greedy B can choose Greedy A internally when its
forecast is unusable. The production checker gates execution and is not Nisha's independent
oracle. The runner rereads state/snapshot both before and after the recheck; approval applies only to
current starts. Selected empty plans can pass as no-ops. Failed approval drains;
out-of-scope rules input or changed live state instead stops without stepping.
Records/hashes detect changes but do not authenticate their own source. The
independent path establishes no execution permission. Safe refusal is not P1
success when it prevents completion of eligible feasible work. Main's historical
176361a archive is received evidence, not verification of corrected main.

The diagrams reflect merged main through PRs #270/#271. The accepted
[RULE-03 section](RULE03_VERIFICATION_SECTION.md) controls verification counts and
limits; the [RULE-04 review](../handoffs/RULE04_DEVELOPMENT_HANDOFF_REVIEW_NOV23.md)
controls partial authored metric claims. PRs #260/#261 are merged; demo wiring is
available in the [RULE-07 handoff](../handoffs/RULE07_EXECUTABLE_DEMO.md).
See the [RULE-05 demo handoff](../handoffs/RULE05_DEMO_HANDOFF.md) for scenario
interpretations. Diagrams do not establish unseen evaluation or accounting acceptance.
