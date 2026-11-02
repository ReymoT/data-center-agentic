# Issue 60 manager review

Matty reviewed Reimo's source-evidence and held-out-custody branches against main
`6e653e85c0432ffc135d11194914dade6173e6db`. Both branch histories are retained.
Reimo's evidence distinguishes bounded historical research from authenticated
exporter provenance and correctly leaves B1-B3 unresolved and B4 provisional.
The proposed custody protocol is infrastructure only: actual parameters, private
storage evidence, affected-owner acceptance, metadata selection and scientific
freeze remain pending. Merging does not approve a parameter proposal or source use.

Direct fixes made by Matty:

- Reject Windows junctions along the custody path in addition to symlinks.
- Reject hard-linked custody files so verification does not accept external aliases.
- Flush and fsync the completion marker before returning its checksum.
- Test all 120 committed generic interval rows against the helper, alongside
  junction and hard-link regressions. No source observations or actual study
  selection are needed by these tests.

These checks supplement the documented trusted-parent and caller-authentication
requirements; they do not establish ACL privacy or protection against concurrent
hostile filesystem changes. Windows requires actual access-controlled evaluator
storage. Receipt hashes establish integrity, not human approval or identity.

No maintainer request was sent, no permission was inferred, no actual held-out
allocation was selected and no model or study run was performed. #60 stays open
for authoritative evidence, actual custody receiving and scientific acceptance.
Thank you to Reimo for the detailed evidence boundaries and preparation work.
