# E02-c trained C/D units in the runner (offline preparation)

Task: E02, [issue #18](https://github.com/ReymoT/data-center-agentic/issues/18). Third increment after E02-a (A/B, #110) and E02-b (Plain/Agent, #113). Owner: Nisha. Contacts: Edison for the P04 artifacts and the P03 classifier contract; Matty for the runner and controller boundaries.

**No trained model is loaded or created by this change.** C and D still refuse in the CLI. Tests use a synthetic classifier double.

## What it does

- **Explicit inputs only.** `runner.run(config, out, trained=TrainedInputs({...}))`. For each trained system, the caller supplies a `TrainedPolicy`: the SHA-256 of Edison's P04 artifact, and `classifier_for(state, context)`, which returns a P03 classifier (`selection_probability(job, start_slot)` in [0, 1]) for one decision. Nothing in the package builds them.
- **Frozen identity.** `RunConfig.trained = TrainedSettings(((system, artifact_sha256), ...))` is required exactly when C or D is listed, and pins exactly those systems. It's part of the run identity only then, so A/B and model run IDs are unchanged, and a retrained model gives a different run ID.
- **Refusals before anything is written:**
  - no trained inputs;
  - a listed system without its input;
  - an artifact hash that differs from the config;
  - trained inputs for a run without trained systems.
- **Same execution path as Greedy A/B.** Per decision: K02 flat context, then `classifier_for`, then P03 `schedule_from_probabilities`, then `execute_policy_output` (real checker, controller and trace store). One unit per episode, with no trials and no model calls.
- **Failures are recorded, never substituted.** A classifier exception or an out-of-range probability becomes a failed output: the decision is blocked, and the error goes to `policy_errors.json`. Empty-queue slots need no classifier and execute the no-op plan.

## Tests

`tests/experiments/test_trained_units.py` (6), on the frozen EP-HAND1 bundle:
- whole episodes for C and D, all 30 slots, J1 and J2 completed, and E01 replay agreeing;
- the classifier sees only the `VisibleState` and flat context, with no private keys and no unarrived jobs;
- a raising or out-of-range classifier blocks slots 0–4 with recorded errors and executes nothing;
- the refusals;
- the settings' validation and run identity.

`test_runner.py`'s unavailable-system test now gives a valid C config and checks the runtime refusal.

Six deliberate bugs each made tests fail:
1. the artifact hash isn't checked;
2. the inputs are never checked;
3. the trained path isn't used;
4. the artifact isn't in the run identity;
5. the registry refuses trained inputs;
6. trained settings aren't required.

## P05 alignment (November 2)

After #155 merged Edison's P05 learned inference, the runner's C/D units use it, so the study has **one definition of C and D**:

- **Inputs.** `TrainedPolicy` now carries a `LearnedArtifact` from `policies.learned.load_verified`, which hashes the exact bytes it deserializes. It replaces the claimed hash plus classifier factory. `check_inputs` compares that **measured** hash, and the artifact's own system, with the run config. A wrong system, an unverified object, a hash mismatch, or a missing or extra input is refused before anything is written.
- **Decisions.** Each decision calls `learned.propose` with the trusted slot clock (`slot0_utc + slot hours`, as for Greedy B). When forecasts cover the decision, P03 probabilities choose; when they don't (missing, stale, partial, future or beyond horizon), P05 returns a checked Greedy A plan. `execute_policy_output` records it as the **fallback stage** under the C/D identity, the same as Greedy B. A policy error is still a recorded failed output, not a substitute.
- **Tests** (`test_trained_units.py`, 6), using small real tree and forest artifacts built the way the P05 tests build them:
  - C and D on EP-HAND1, choosing from probabilities, with E01 replay agreeing;
  - a withheld-forecast bundle where both take the checked Greedy A fallback stage, keep their identity, and replay agrees;
  - the policy sees only the visible state and flat context, with the trusted clock;
  - a policy failure blocks the decision, with recorded errors and no fallback;
  - the refusals above;
  - the settings and run identity.

  Five deliberate bugs each made a test fail:
  1. the measured hash isn't checked;
  2. the artifact's system isn't checked;
  3. the old path without P05 fallback;
  4. a wrong decision clock;
  5. an unverified artifact accepted.

## Open

- **Done (P05 alignment above):** the runner now loads Edison's P04 artifacts through P05. The real development hashes (`7e9e5769…` for C, `37149e53…` for D) go into `TrainedSettings` and the I02 manifest at the freeze.
- The 300-run matrix config and the held-out custody loader follow for the I02 freeze.
