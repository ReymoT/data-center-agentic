# A02 episode-authorization preparation

This checklist prepares one paired Plain/Agent development receiving exercise on the
public `EP-HAND1` fixture. It sends no request and grants no authorization. Stop when
an item is unresolved; do not copy limits from A01's consumed two-call authorization.

## Offline freeze

- [ ] Package the same `EP-HAND1` episode input for Plain and Agent; record its path
      and SHA-256 in the preparation manifest.
- [ ] Freeze the exact commit and proposal, repair and explanation renderer hashes.
- [ ] Confirm Nisha's L01 episode uses the same episode, settings and evidence view.
- [ ] Record the exact per-system request ceilings, per-request deadline and combined
      deadline. These fields are intentionally blank until decided.
- [ ] Confirm zero retries and that every sent/uncertain request consumes its budget.
- [ ] Run the complete offline tests and validate every manifest field.

## Fresh authorization

- [ ] Reverify the accepted isolated Ollama 0.40.5, Qwen3 8B model digest, settings,
      Arc/Vulkan backend and 37/37 layer offload without dispatching a model request.
- [ ] Record a new authorization naming the exact commit, episode hash, renderers,
      request limits, deadlines, seed, stop conditions and cleanup controls.
- [ ] Change `ready_for_dispatch` only through a reviewed preparation update after all
      fields and the authorization reference exist. A passing test is not authorization.

## Run boundary

- [ ] Use fresh ledgers and retain raw response/error evidence for both systems.
- [ ] Run serially and stop on any identity drift, unknown outcome, persistence failure,
      deadline, response bound, call cap, CPU fallback or cleanup failure.
- [ ] Never open held-out data, run the study suite, or treat this development receiving
      result as an accuracy, faithfulness or safety finding.
