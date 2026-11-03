# Recomputed development-fold candidate metrics

Actual new computation on the saved 6,046 definite development rows, using the unchanged 40-episode blocked allocation. Five existing grid configurations were refitted on each training partition and scored only on its disjoint validation partition. Fifteen new fold refits remain manager-local; frozen C/D policy binaries are unchanged. No held-out data, reference solving or LLM requests were used.

These are post-selection descriptive classification scores, not unbiased final performance, scheduling outcomes or evidence that Model D improves the research endpoints. Selection was not changed. Original excluded-candidate counts are unavailable from the saved definite-row corpus; zero exclusions in these scoring tables does not mean zero original exclusions.

## Pooled confusion-count metrics

Sum the three validation confusion tables before deriving precision, recall and F1. Each configuration scores every definite row once: 1,411 positives and 4,635 negatives. Threshold 0.5; existing development seed 20261031.

| Configuration | TP | FP | TN | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| decision_tree_c:depth=3 | 766 | 684 | 3951 | 645 | 0.528276 | 0.542877 | 0.535477 |
| decision_tree_c:depth=5 | 845 | 975 | 3660 | 566 | 0.464286 | 0.598866 | 0.523058 |
| decision_tree_c:depth=8 | 816 | 1254 | 3381 | 595 | 0.394203 | 0.578313 | 0.468831 |
| random_forest_d:trees=100:depth=5 | 853 | 960 | 3675 | 558 | 0.470491 | 0.604536 | 0.529156 |
| random_forest_d:trees=100:depth=10 | 872 | 1042 | 3593 | 539 | 0.455590 | 0.618001 | 0.524511 |

The existing rollout-selected C depth 8 and D depth 10 remain selected; higher classification F1 elsewhere is not a new selection criterion.

## Evidence and reproduction

[Full aggregate/fold record](development_fold_metrics_2026-11-02.json) contains source-corpus/scorer hashes, code revision, per-fold support and confusion counts, measured fit/scoring times and private refit binary hashes. The source corpus, episode contents and binaries stay private. The earlier model cards record the initial publication and remain historical; this record supplies the later measured fold scores.

Run on the trusted manager-produced corpus only (joblib is executable input):

```text
python scripts/score_p06_folds.py --corpus <private-corpus.joblib> --expected-sha256 <authenticated-corpus-hash> --out <new-private-directory>
```

No default corpus path or overwrite is supplied. The CLI verifies the input hash before deserialization and requires the exact published development fold map. Source rights, interval meaning and scientific freeze remain open in #60.
