# Administrator review checklist

Proposed settings only. No repository settings were changed by this bootstrap. Q11 selects the authorized administrator/merge actors; Q12 accepts review routing.

- Protect `main` using reviewed PRs, at least one independent human approval, resolved discussions and refreshed approval after relevant edits.
- After the workflow has run successfully, require its exact job name `bootstrap-offline`; do not require an unobserved status name.
- Keep direct main pushes and shared-history force pushes restricted.
- Confirm all GitHub handles and write permissions before activating CODEOWNERS. The previously deleted file is not restored here.
- Use read-only workflow permissions for ordinary CI. No provider secrets or live model calls in PR CI.
- Confirm Issue statuses and one owner/session per task; activate the single coordination publisher only after Q11.
- Confirm supported operating systems, code license, artifact access/retention and course deliverables through Q13.

A human merges until an accepted policy says otherwise. Reviewer approval, CI execution and post-merge consumer verification remain required; local checks are not substitutes.
