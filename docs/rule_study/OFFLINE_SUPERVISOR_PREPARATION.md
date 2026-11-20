# RULE-06 offline timeout preparation — November 20

Matty prepared a dummy-only rehearsal around the existing Windows Job Object
supervisor. It checks real process containment without loading the verifier,
scheduler, case generator, source data or model. It does not run the rule study.

The child waits for a one-byte release gate. The parent first assigns it to a
kill-on-close job, then releases it. The existing supervisor starts its deadline
before process creation, refuses a late release, and terminates remaining child
processes on timeout, failure or interruption. Cleanup has a separate bounded
allowance. Windows process creation itself cannot be preempted. This is wall-time
and process-tree containment, not a memory, disk or network sandbox.

## Reproduce the preparation

On Windows with the repository environment:

```
python -m pytest tests/runtime/test_rule_study_supervisor.py -q
python scripts/rehearse_rule_study_supervisor.py --mode timeout --limit-seconds 0.7 --out <new-dummy-output-directory>
```

The CLI allows only four built-in dummy modes: success, failure, timeout and
descendant. It cannot accept a module, executable or user command. Each run uses a
new directory; existing directories are refused before launch. Partial worker
evidence and the supervision report are retained. A rehearsal passes only if the
expected status occurs, the child was released and cleanup was verified. CLI exit
zero means the expected dummy behavior was observed, including an intentionally
failed or timed-out worker; it never means a scientific property passed.

The tests exercise all four modes, including a real child that leaves a sleeping
descendant. They independently check that recorded process IDs have exited. They
also check invalid limits, arbitrary-command refusal, output preservation and
refusal on platforms without this containment. The 13 local tests passed.
Windows CI must repeat them on the exact PR and merged commit.

## Actual run remains pending

This rehearsal does not authenticate inputs, consume a single-use authorization
or contain an actual verifier invocation. Do not substitute its output for a
verification report. The real dispatcher remains to be wired after Ved supplies
the adapter and Nisha receives its exact trace/state/hash semantics. Any actual
verifier worker must wait for containment before importing adapter code or
spawning children, preserve its real reports and fail closed on containment loss.

Before launch, bind the accepted specification, rule/adapter/verifier/generator
code and environment; record the actual input identities, unused authorization
ID, new output destination, combined counters and stop conditions. Obtain the
exact bounded manager authorization. The prospective 600-second verification
ceiling is not granted by the rehearsal's five-second dummy limit. Actual run
failure and incomplete bindings remain failures/incomplete, never inferred PASS.

## Current handoffs

- Ved accepted proposal-1 in #239; his actual RULE-02 implementation is pending.
- Nisha's independent harness is merged in #250. Actual frozen-scheduler
  verification and external artifact authentication remain pending in #241.
- Edison still owes exact review-2 generator/result acceptance in #239. Generator
  preparation can proceed; the final synthetic set waits for the agreed freeze.
- Reimo supplies methods/diagrams; Edison and Ved build the two-scenario demo.
- #16 retains the November 20 checkpoint for remaining official course guidance.

No masters, shared settings, F02 contracts or scientific limits change here.
