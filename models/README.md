# Model artifacts preparation

Owner: Edison. P04 development training lives in `dc_sustainability.training`
(`train`, `select`, `pipeline`) and `scripts/train_p04_development.py`.

Mandatory C/D need certified visible-state labels (O02), blocked development folds
(D04 fold map), validated features (Q07), and frozen seeds/settings under Q06-Q08.

## Development freeze command

With an authorized local pinned D01 carbon CSV:

```bash
PYTHONPATH=. python scripts/train_p04_development.py /path/to/AZPS_NG_\&_avgCI.csv
```

This writes gitignored binaries under `models/artifacts/p04-development/` plus JSON
manifests recording feature order, fold map, selected depths, seeds, class counts,
rollout fold results, and artifact SHA-256 digests for Nisha's `TrainedSettings`.

## Tracking rule

Track validated artifact manifests containing model/feature versions, training input
hashes, fold groups, hyperparameters, selection evidence, class counts, timings and
artifact checksums. Actual generated binaries under `artifacts/` and joblib/pickle
files are ignored by default. Record permitted artifact access under Q13; do not
commit a binary merely because a loader can read it.
