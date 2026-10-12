# Repository workflow settings

Matty is the project manager. Formal document/code review and reviewer approval are not required under [his recorded instruction](decisions/Q11_MANAGER_AUTHORITY.md). He explicitly authorizes publishing these documents to main. PRs are optional; they must not replace an authorized publication with a review request.

Technical checks remain applicable. The `bootstrap-offline` job validates package consistency, installs the hashed Windows candidate and runs dependency smoke, offline provider-mock tests, lint, format and compilation checks. Scientific safety and independent evaluation requirements remain in the final proposal.

The workflow uses [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) and [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0), whose action definitions use Node.js 24. These replace the deprecated Node.js 20 actions. GitHub-hosted `windows-latest` supplies the runner; Python remains 3.12 with the existing hashed candidate lock. The action upgrade does not select the provider or additional supported platforms. See [the maintenance handoff](handoffs/DOCUMENTATION_CI_ALIGNMENT.md) for verification and limits.

Use short development branches when useful, preserve existing changes and history, and use normal pushes for ordinary publication. Matty explicitly authorized repository-only setup-history cleanup on 2026-10-10; that operation uses a recoverable backup and force-with-lease to protect against unseen remote work. No protection/access settings are changed. CODEOWNERS remains absent; verify accounts and permissions before enabling optional routing. Keep ordinary CI read-only and free of provider secrets or paid model calls.

Backup/publisher choices, target platforms, license, artifact access/retention and course deliverables remain in Q11/Q13. Tests, published commits and applicable consumer checks supply technical acceptance evidence; formal reviewer approval is not a blocker.
