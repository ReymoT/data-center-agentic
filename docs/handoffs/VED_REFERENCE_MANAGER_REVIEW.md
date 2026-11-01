# Ved reference integration review

Matty reviewed and integrated `ved/f02-downstream-acceptance`,
`ved/o02-label-cache` and `ved/o03-hindsight-export` against main
`5b9183664081b223ff53b0152fc544a0451e7747`.
The manager authorized direct fixes instead of returning defects to the owner.

The older F02 branch conflicted with already integrated safeguards. Current
main solver/label safeguards and downstream tests were preserved. Its proposed
secondary tie optimization is not adopted: the branch explicitly tolerated
choosing a more expensive schedule below its numerical resolution. Scientific
Q08 tie handling remains unresolved rather than being silently certified.

Cache integration fixes: keys retain explicit UTC time and complete input/config
identity; collected features are compared by value before labels attach; cache
files are located from keys rather than untrusted stored paths. Result and label
checksums detect corruption; visible/context checks reject hindsight or wrong
context results. Write collisions propagate instead of being mistaken for
identical entries. Cache schema/implementation identities invalidate earlier entries.
The new import path exposed a cycle through training.dataset; its type-only
LabeledDecision import is now deferred.

Hindsight fixes: background load is included in individual candidate feasibility;
a capacity-blocked timing-feasible job cannot silently disappear from the objective.
The matching-work boundary continues to exclude intrinsically impossible timing
windows, as in the supplied hand fixture; it is not a reference for all-work
completion or an accepted scientific Q08 matching decision. Results retain explicit
matching-work IDs. Actual elapsed time and configured budget are recorded; invalid
budgets are refused. The result describes stable backend candidate order rather
than claiming an unimplemented lexical optimization. Export uses exclusive links
instead of rename-overwrite behavior. The optional plain-policy import of the
offline solver was removed: strict F02 Context validation already rejects extra
private fields, and policies must not depend on offline hindsight modules.

Windows cannot establish POSIX 0600 privacy through chmod. The platform test checks
that mode only on POSIX; callers must use an access-controlled private directory
on Windows. No claim of Windows ACL enforcement is made.

No held-out contents, model calls, generated study references or source acceptance
are included. Q08 scientific solver/tie/matching acceptance remains separate.
O03 provides infrastructure, not final O04 held-out references.
