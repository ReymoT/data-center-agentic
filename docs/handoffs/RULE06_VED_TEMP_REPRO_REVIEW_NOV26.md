# Ved temporary reproduction branch: direct review and integration

Matty reviewed Ved's `ved-temp-repro` at
`ac262126a4647d5836800e1ec569d451df2b7279`, based on producing source
`e77077997bb8ffde18f5b6d8d053c10a3b92f7b2`. The only commit is described as
"temp file holding". This record does not interpret a temporary upload as a
claimed scientific PASS by Ved.

## Actual findings

All 17,295 submitted files are byte-identical to their originals in the supplied
November26 handoff archives. There are no changed/new scripts, receiving results,
reproduction commands or reviewer verdicts. The expanded package should contain
27,975 files across the outer package and expanded inner receiving archive.

The expansion omits 10,680 records: 5,340 under `.completed` and 5,340 under
`.intents`. Both sets contain per-decision JSON markers. These files remain intact
in the original nested ZIP, whose raw hash also matches. No underlying scientific
output was lost from that archive. The omission mechanism is not established.
Windows Git path-length warnings were observed during review; those warnings alone
do not prove why the hidden records were omitted.

The complete original branch is preserved in a verified private Git bundle, with
base prerequisite `e77077997bb8ffde18f5b6d8d053c10a3b92f7b2`. Its raw SHA-256 is
`0eab5152876af805225362a646711f351484198777575d5c63ecd7debc987706`.
The bundle and original packages stay outside the checkout. This is preservation,
not a claim that already uploaded GitHub objects or caches have been erased.

## Corrections made directly

- Integrate this sanitized receipt and an archive-only integrity tool through a
  clean branch based on main, keeping the raw package commit out of main's ancestry.
  No original branch history is rewritten and no submitted work is discarded.
- Ignore the named root-level private ZIPs and extraction directories so ordinary
  `git add` does not accidentally stage them again. Public reviewed evidence paths
  and source files remain eligible for tracking.
- Verify the exact original archives without extraction, including nested raw
  manifests, CRCs, hidden marker counts, safe names and bounded expanded sizes.
  This avoids relying on a partial extraction or its path-length behavior.

From the repository, using ordinary Python:

```
python scripts/verify_rule06_handoff_archive.py --package <original-Ved-package.zip>
```

The package's expected raw SHA-256 is
`71b8c0a6e7e3781be49a6d81c5e1c75674ae54404eeaa9fb1a7394852fc041e1`.
The tool reads data only: it never extracts a file, executes an embedded verifier,
calls a policy/simulator, performs a scientific replay or consumes authorization.
It checks the outer package, new receiving archive and accepted parent archive.
AI assistance is welcome. Its PASS means archive integrity only.

## Remaining scientific gates

Matty's separately authorized continuation completed178/178 pairs with verified
cleanup. Read-only combined accounting covers360/360 development pairs; original
failures, different producer commits and unavailable cross-source case20 comparison
remain preserved. No scientific code or data is changed in this branch review.

Nisha's new-output/union receiving and Ved's actual clean-environment/static report
remain pending. The temporary branch does not establish that either was performed.
The exact proposed scope, unused ID, absent output, bounds and fresh authorization
are still required before any new scientific execution. Do not reuse the consumed
parent or continuation IDs. Do not create a favorable verdict on Ved's behalf.

Keep #244 open for actual reproduction and final audit, with #242/#223/#231
retaining their remaining acceptance gates. The candidate deadline remains
November28 at18:00 America/Phoenix. Ready independent work should proceed now.
