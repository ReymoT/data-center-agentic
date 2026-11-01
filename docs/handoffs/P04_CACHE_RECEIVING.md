# Offline P04 cache receiving

Matty tested the actual P04 `build_labeled_corpus` consumer against reference
integration main `84ec86c2f04205e4efde711c9538f65b2a5cb40e`.
This uses labeled synthetic development fixtures, not the real D01 corpus or
held-out contents. Materialization is injected at the test boundary; collection,
feature generation, solver certification, cache persistence, label attachment,
row conversion and C/D classifier fitting use actual implementations.

The pipeline previously did not expose O02's optional LabelCache. It now accepts
`cache=None` by default and forwards an explicit cache to `label_episode`.
No default storage path, scientific setting or CLI flag is introduced.

Receiving results:

- Cached and uncached P04 rows match exactly, including candidate keys, features
  and definite labels. Both positive and negative labels exist in the fixture.
- On the second pass, certified cache hits bypass the solver. Uncertified decisions
  are intentionally recomputed; their labels remain excluded from training.
- Actual decision-tree C and random-forest D fits use the same seed and produce
  identical probabilities from cached versus uncached rows.
- A hindsight-marked solver result is rejected by the actual P04 path before
  a training corpus can be returned.
- Reference and training suites: 130 passed. Setup/link/task validation passed.

Tests: `tests/training/test_cache_receiving.py` plus the existing reference and
training suites. The first cache-bypass assertion was corrected to reflect the
documented certified-only policy; it had incorrectly expected uncertified results
to be cached as well. No production cache acceptance was relaxed.

Edison can pass a private caller-owned LabelCache to `build_labeled_corpus` when
performing authorized development work. Nisha receives actual artifacts only
after the [P04/I01 checklist](I01_TRAINED_RECEIVING_CHECKLIST.md) is satisfied.
This completes offline consumer receiving, not full-corpus training, real artifact
delivery, six-system I01, Q08 scientific acceptance or held-out evaluation.
