# Bootstrap review request draft

Task: F01 repository foundation, with initial F03/F04/F05 scaffolding.
Owner: Matty Anderson (`MattyAnd`). Primary F01 reviewer: Reimo (proposed Q12).
Base: `3dabb97` on current main when cloned. Branch: `matty/f01-repository-bootstrap`.
Issue: not assigned or created in this session; reading open Issue metadata hit the unauthenticated GitHub API rate limit. PR: not posted. Intended state: local preparation for In review; no Issue status was changed.

Prepare the repository for the final six-system scheduling study. The previous README was empty. The new README opens with teammates/roles, explains reviewed systems and design rationale, and gives executable foundation checks. Preserve the historical architecture image and existing ignore rule. Add directories, source provenance, architecture, project plan, full team package, a single proposed interface document, decision/handoff templates, environment candidate, secret exclusions and offline CI.

Review requests: Reimo for F01, Edison for F03, Nisha for F04, Ved for F05 and contract relocation, all consumers for the proposed interfaces. No task is marked Done. Q11 account/permission/publisher decisions, Q12 allocations and Q13 target platforms/license remain open. Provider/model/budget awaits Q09. CI is prepared locally, not observed on GitHub.

Master-package adaptation: source package kept unchanged outside this repository. Selected deployed files are version 1.1, with [changelog](team/CHANGELOG.md). Relocation preserves the proposed contract without adopting it. Original dependency references remain byte-identical. No scientific rule or role allocation was changed.

Acceptance evidence and exact observed checks: see [F01 handoff](handoffs/F01.md). Before merge, obtain independent approvals, run current-base CI and record the assigned Issue/PR. After merge, receiving owners verify main and record acceptance; then mark the applicable tasks Done.
