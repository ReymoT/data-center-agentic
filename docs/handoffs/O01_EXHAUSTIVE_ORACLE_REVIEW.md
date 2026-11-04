# O01 tiny exhaustive-oracle receiving

Matty reviewed Ved's PR #167 against main
`87621d879ea48b02ecf8b6306516a4bcc774cf83`, instruction 1.28.
The oracle enumerates complete start combinations, checks capacity with background
and running occupancy, and computes job energy/carbon from fixture inputs without
the production MILP builder or feasibility helpers.

The review corrected the joint-capacity case: both jobs now fit individually,
but their only start windows jointly overload capacity. The oracle separately
filters starts with complete fresh carbon, so an early missing-carbon candidate
does not hide a later usable one. Missing all candidate evidence is distinct from
physical infeasibility. Independence is tested with production solver entry points
replaced by forbidden functions while the hand-derived 48.4 objective is computed.

Coverage includes one/multiple jobs, overlapping capacity, running/background
load, arrival/deadline/nonflexible restrictions, genuine infeasibility, equal-cost
optima, partial/missing carbon and independent objective computation. Feasible
comparisons require membership in the enumerated optimum set and objective
agreement within absolute 1e-6; the oracle groups exact-cost ties within 1e-9.
Equal-cost cases accept any optimum and impose no scientific secondary rule.

Validation: `python -m pytest tests/reference -q` passed 82 tests on the manager's
Windows environment. Full hosted offline CI is required before merge and exact
main CI before branch deletion. Production solver, labels/cache, source mappings,
model binaries and shared settings are unchanged. The oracle is for deliberately
tiny synthetic cases, not study-scale reference generation. Q08's final scientific
tie rule and held-out O04 acceptance remain separate open freeze items.
