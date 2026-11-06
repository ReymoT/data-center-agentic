# Proposed PR title

D05 #60: implement restricted CF60-v1 production forecast broker

# Proposed PR body

CF60-v1 previously had a conditional specification and synthetic proof but no
production broker restricting actual row access. This adds an opt-in issue-scoped
broker with copied, immutable three-candidate capabilities, hourly trusted-clock
validation, conditional start/end mapping, explicit missingness and the existing
24-slot F02 projection. Privileged full-CSV checksum/structural validation remains
a separate acquisition operation and is explicitly not described as restricted.

Receipts pin algorithm/implementation, code bundle, source, authorization locator,
interpretation, every attempted/successful read and forecast output commitments,
without exposing source values. A separate receiving harness independently derives
eligibility, probes all year keys at every issue under both hypotheses, detects
unauthorized-access fault injection, and reserves recorded/legacy plus both CF60
development footprints across all forty fixed records.

Validation: 18 broker tests; 155 focused tests. Full offline suite, lint/format,
setup, compilation, dependency and Git results and exact hashes are in
`docs/evidence/cf60-production-validation.json`. See
`docs/handoffs/CF60_PRODUCTION_BROKER.md` for commands and Nisha's receiving procedure.

Original development allocations/content commitments, legacy forecasts, labels,
models, F02/Q04 and shared instructions are unchanged. No real-source comparison,
held-out selection/access or model call occurred. Nisha's independent receiving,
real-source execution authorization, versioned custody amendment and scientific
compatibility/adoption remain separate gates. Python capabilities do not replace
OS/principal custody controls against hostile same-process code.

This is implementation for independent review, not scientific adoption or C/D
compatibility certification. Reimo authorized commit/push/draft PR publication.
Merge and automatic comments remain unauthorized; this file is the PR body template.
