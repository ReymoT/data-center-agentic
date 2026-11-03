# Development candidate card

Public facts for the development decision-tree and random-forest refits. Counts, hashes, and the recorded time come from [Real development C/D artifacts and receiving](../docs/handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md). The positive rule comes from [Q07 training decision](../docs/decisions/Q07_TRAINING_OCT27.md).

## Support

There are 6046 definite rows. 1411 are positive and 4635 are negative.

Held-out support subtracts each fold's published training count from those definite totals. Those counts are not a measured confusion table.
Here held-out means a blocked development validation partition, not the private final held-out cohort.

| Fold | Training positive | Training negative | Held-out positive | Held-out negative |
| --- | ---: | ---: | ---: | ---: |
| 0 | 840 | 2765 | 571 | 1870 |
| 1 | 1009 | 3363 | 402 | 1272 |
| 2 | 973 | 3142 | 438 | 1493 |

## Selection

| System | max_depth | n_estimators | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| decision_tree_c | 8 | none | 7e9e5769771f045241317d976f142b936f328399df58b040f9bbf67ba77a8f0b |
| random_forest_d | 10 | 100 | 37149e530ef8e026b08279bedae1dd95170f70c279dd59d566637f43df94cf6a |

The development script seed is 20261031. Total materialization, labeling, selection, refit, and reload time is 101.375 seconds.

## Features and custody

Artifact schema `p04-artifact-v1`. Positive threshold 0.5.

Feature names, in model order:

- `delay_slots`
- `deadline_margin_slots`
- `duration_slots`
- `power_kw`
- `available_capacity_kw`
- `queue_load_count`
- `carbon_mean_g_per_kwh`
- `carbon_min_g_per_kwh`

Carbon source SHA-256 `e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.

Content receipt `d04-development-content-112-v2`.

Manager-local custody label `P04_Private_2026-11-02`. The label names storage outside this repository.

## Candidate metrics

Validation-fold precision, recall, and F1 are unpublished because the fifteen fold models were not serialized and the frozen joblib is the full-data refit.

## Intended use and limitations

These full-data refits support development receiving only. Candidate classification scores are separate from scheduling outcomes and do not establish accuracy, faithfulness, safety or superiority in the final study. Source rights and physical semantics remain unresolved in issue #60. No final held-out study acceptance or redistribution permission is implied.
