# October 31 manager integration of ready runner and reference work

Manager: Matty Anderson. Source owners: Nisha for E02/I02 and Ved for F02/O02.

This integration preserves the exact teammate commits from these branches:

- `ved/f02-downstream-acceptance` at `f79bafa1f1e8efc034876ddcd3be59a8cab12f47`;
- `nisha/e02c-trained-units` at `e82608859c5f81c3e0ae050f3b137ddb603e0b2f`;
- `nisha/e02-matrix-config` at `66111454e3dbb2a7105f851ae7284f0b615fdfb7`;
- `nisha/i02-manifest-refresh` at `d0db3434779203c2f9513bf56a73e9505bd9c817`.

The separate `nisha/e02-admission-ledger-cap` change is already implemented and
tested on main through PR #133. Its documentation is synchronized here; its older
conflicting PR does not replace the merged implementation.

## Manager corrections

- The visible reference solver fails closed when the authoritative freshness
  constraint is missing. It no longer treats missing evidence as unlimited age.
- Replay/audit label generation requires an explicit trusted UTC decision time.
  Production code no longer derives time from a test fixture.
- The solver minimizes the physical emissions objective without a numerical
  tie-break perturbation. Stable candidate order plus the pinned backend is
  repeatable for bounded development, but the final Q08 scientific tie-break stays
  an explicit freeze item.
- Trained C/D inputs must exactly match the systems and artifact hashes pinned in
  the run config. Unfrozen extra policies are rejected before output is written.
- The 300-run matrix checker rejects core bundles with no forecasts and any
  forecast issued after its decision time. It remains a structural pre-freeze
  checker, not authorization to open held-out data or dispatch a model request.

## Run-setting decision

The planned full matrix arithmetic is retained: 30 held-out episodes, 300 units,
seeds 101/102/103, 480 seconds per model decision, at most 2,160 Plain requests and
6,480 Agent requests, an 8,640 global attempt budget and a 72-attempt per-unit
ledger cap. These values are exact maxima derived from 24 decision slots and the
one-call Plain / three-call Agent limits. They define a future frozen configuration;
they do not authorize inference. Every actual model exercise still needs its own
recorded authorization and accepted frozen inputs.

## Honest remaining work

- Edison must produce the real P04 C/D artifacts and their hashes. The merged C/D
  tests use a clearly labeled synthetic classifier and do not claim trained models.
- The full private development corpus still needs collection and O02 labeling for
  P04. The bounded D04 receipt proves the interface path only.
- Held-out allocation, custody, no-overlap evidence and scientific freeze remain
  unavailable. No held-out content was opened or created here.
- The exact EP-HAND1 bounds are agreed, but no model call is made by this change.

