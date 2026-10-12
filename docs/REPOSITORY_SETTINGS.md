# Repository workflow settings

Matty is the project manager. [His recorded instruction](decisions/Q11_MANAGER_AUTHORITY.md) fixes the rule:

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

Record affected teammates' agreement in the Issue or decision record before changing shared formats or settings. This documents merge eligibility; it does not change repository permissions or protection settings. Matty's earlier authorization to publish project documents directly to main still applies.

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

Passing checks does not authorize instruction changes. Link Matty's explicit authorization for the specific change in its Issue, decision or authorized-session handoff. The offline setup check detects missing or inconsistent rule text across the seven core files; it does not prevent unauthorized writes or authenticate permission. GitHub reports MattyAnd has write access but not admin access. Actual access restrictions require repository-owner action; none were enabled by this publication.

Technical checks remain applicable. The `bootstrap-offline` job validates package consistency, installs the hashed Windows candidate and runs dependency smoke, offline provider-mock tests, lint, format and compilation checks. Scientific safety and independent evaluation requirements remain in the final proposal.

The workflow uses [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) and [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0), whose action definitions use Node.js 24. These replace the deprecated Node.js 20 actions. GitHub-hosted `windows-latest` supplies the runner; Python remains 3.12 with the existing hashed candidate lock. The action upgrade does not select the provider or additional supported platforms. See [the maintenance handoff](handoffs/DOCUMENTATION_CI_ALIGNMENT.md) for verification and limits.

Use short development branches when useful, preserve existing changes and history, and use normal pushes for ordinary publication. Matty explicitly authorized repository-only setup-history cleanup on 2026-10-10; that operation uses a recoverable backup and force-with-lease to protect against unseen remote work. No protection/access settings are changed. CODEOWNERS remains absent; verify accounts and permissions before enabling optional routing. Keep ordinary CI read-only and free of provider secrets or paid model calls.

Backup/publisher choices, target platforms, license, artifact access/retention and course deliverables remain in Q11/Q13. Tests, published commits and applicable consumer checks supply technical acceptance evidence; formal reviewer approval is not a blocker.
