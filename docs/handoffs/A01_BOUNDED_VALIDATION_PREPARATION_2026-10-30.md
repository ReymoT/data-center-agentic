# A01 bounded-validation preparation

Owner: Matty Anderson (`MattyAnd`). Issue: [#6](https://github.com/ReymoT/data-center-agentic/issues/6).

This offline preparation adds a machine-checkable manifest, a no-network validator
and a plain-language operator checklist. It starts no runtime, loads no model and
sends no request.

The checked-in manifest pins the already accepted runtime/model/template/parameter
identity, generation settings, Arc/Vulkan host requirements, response-bound evidence,
two-request order and stop/evidence requirements. It records the proposed 150-second
request and 330-second paired limits as pending, not accepted. Nisha and Ved agreement,
a future exact commit and prompt/renderer freeze, and a fresh Matty authorization are
all explicitly absent. `ready_for_dispatch` is false.

`scripts/validate_a01_bounded_manifest.py` validates integrity without any network or
process capability. The ordinary check accepts a valid blocked preparation record.
`--require-ready` fails until every dispatch gate is recorded with exact references.
Tests deliberately try to create false readiness, identity drift, a third request,
retries and changed response measurements; all are rejected.

The operator checklist covers agreement, authorization, identity/offload checks,
Plain-first order, the Agent gate, evidence retention and exact-process cleanup. It
does not include an inference launcher. Any later live request still requires the
currently pending owner agreement and a new bounded authorization.
