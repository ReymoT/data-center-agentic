"""Request-local output bounds shared by the plain and agent LLM paths.

The F02 records remain unchanged.  These limits only narrow the JSON schema sent
to Ollama for one visible decision.  They are derived from policy-visible state
and fixed constants, never from model output or evaluation results.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from dc_sustainability import schemas as s


@dataclass(frozen=True)
class ResponseBounds:
    """Auditable constants and the one state-dependent plan-entry allowance."""

    plan_entries: int
    claims: int = 4
    limitations: int = 4
    text_characters: int = 96
    evidence_ids: int = 2
    explanation_characters: int = 96


def response_bounds(state: s.VisibleState, *, explanation_characters: int = 96) -> ResponseBounds:
    """Return bounds for a visible decision without consulting results.

    The policy layers retain the accepted empty-queue no-call rule.  A zero-entry
    grammar is still defined here so the low-level shared adapter remains total and
    run-budget checks cannot be bypassed by changing the visible queue.
    """

    state = s.VisibleState.model_validate(
        state.model_dump(mode="python", warnings="none"), strict=True
    )
    if type(explanation_characters) is not int or explanation_characters not in (96, 256):
        raise ValueError("explanation length must be 96 or the explicit 256-character candidate")
    return ResponseBounds(
        plan_entries=len(state.waiting_jobs), explanation_characters=explanation_characters
    )


def _visible_evidence_ids(state: s.VisibleState) -> tuple[str, ...]:
    ids = {"FACT-SITE-BG", "FACT-SITE-PUE", "FACT-SITE-SLOTH"}
    ids.update(f"FACT-JOB-{job.job_id}" for job in state.waiting_jobs)
    ids.update(f"FACT-JOB-{view.job.job_id}" for view in state.running_jobs)
    ids.update(f"FACT-JOB-{view.job_id}" for view in state.completed_jobs)
    ids.update(f"FACT-JOB-{job_id}" for job_id in state.missed_job_ids)
    ids.update(fact.fact_id for fact in state.carbon_facts)
    ids.update(state.constraint_ids)
    return tuple(sorted(ids))


def _definition(schema: dict, name: str) -> dict | None:
    if schema.get("title") == name:
        return schema
    return schema.get("$defs", {}).get(name)


def _string_branch(node: dict) -> dict | None:
    if node.get("type") == "string":
        return node
    return next((item for item in node.get("anyOf", ()) if item.get("type") == "string"), None)


def _bound_text(node: dict, maximum: int) -> None:
    branch = _string_branch(node)
    if branch is None:
        raise ValueError("expected a string response-schema field")
    branch["maxLength"] = maximum


def _bound_ids(node: dict, allowed: tuple[str, ...], maximum: int) -> None:
    node["maxItems"] = min(maximum, len(allowed))
    if allowed:
        node["items"] = {"enum": list(allowed), "type": "string"}
    else:
        node["maxItems"] = 0


def _bound_job_id(node: dict, job_ids: tuple[str, ...], *, nullable: bool = False) -> None:
    target = _string_branch(node) if nullable else node
    if target is None:
        raise ValueError("expected a job-id response-schema field")
    target.clear()
    target.update({"enum": list(job_ids), "type": "string"})


def _paired_claim(claim: dict) -> dict:
    """Return the request-local Claim as two coherent object branches.

    F02 ``Claim`` rejects a value without a unit and a unit without a value, but
    that model validator is not part of the generated JSON schema.  Two independent
    nullable fields therefore let constrained generation emit ``value: null`` with a
    unit (RUN-bc420d3e8d72, Agent slot 2).  The union keeps the base field bounds
    and allows only:

    * nonnumeric: ``value`` and ``unit`` both null;
    * numeric: a JSON number and an allowed unit.

    Both branches require the same five keys, so the converter emits them in one
    fixed order and the branch is chosen only at the ``value`` token; an optional
    key would be moved after the required ones and could lock a claim into the
    nonnumeric branch.  Generation therefore always writes explicit nulls and an
    explicit (possibly empty) evidence list.  The stored F02 contract is unchanged:
    omitted fields remain valid there.

    Only ``anyOf``, ``type``, ``enum``, ``properties``, ``required`` and
    ``additionalProperties`` are used.  The pinned Ollama 0.40.5 runtime converts
    schemas with llama.cpp b11669, which compiles ``anyOf`` as a grammar alternation
    and does not read ``if``/``then``, ``not`` or ``dependentRequired``.  F02
    validation of the parsed response remains the final gate.
    """

    properties = claim["properties"]
    number = next(item for item in properties["value"]["anyOf"] if item.get("type") == "number")
    unit = next(item for item in properties["unit"]["anyOf"] if item.get("type") == "string")
    base = {name: deepcopy(properties[name]) for name in ("claim_id", "text", "evidence_ids")}
    base["evidence_ids"].pop("default", None)
    keys = ["claim_id", "text", "evidence_ids", "value", "unit"]

    def branch(value: dict, unit_schema: dict) -> dict:
        return {
            "additionalProperties": False,
            "properties": {**deepcopy(base), "value": value, "unit": unit_schema},
            "required": list(keys),
            "type": "object",
        }

    return {
        "anyOf": [
            branch({"type": "null"}, {"type": "null"}),
            branch(deepcopy(number), deepcopy(unit)),
        ],
        "title": claim.get("title", "Claim"),
    }


def bounded_response_schema(
    response_model: type[s.Record],
    state: s.VisibleState,
    *,
    system: str,
    explanation_characters: int = 96,
) -> tuple[dict, ResponseBounds]:
    """Build the one bounded grammar used by both LLM systems.

    The returned object is a request-local copy.  It pins plan identity to the
    visible decision, permits one plan entry per waiting job in every action
    category, applies identical explanation limits and the paired claim
    value/unit rule to Plain and Agent, and prevents the model from filling
    ``raw_response`` (the caller retains the actual original response separately).
    """

    state = s.VisibleState.model_validate(
        state.model_dump(mode="python", warnings="none"), strict=True
    )
    if system not in {"agent", "plain_llm"}:
        raise ValueError("response bounds apply only to the two LLM systems")
    if response_model not in {s.Plan, s.PolicyOutput, s.Explanation}:
        raise ValueError("response bounds require Plan, PolicyOutput or Explanation")
    limits = response_bounds(state, explanation_characters=explanation_characters)
    schema = deepcopy(response_model.model_json_schema())

    if issubclass(response_model, s.Versioned):
        required = list(schema.get("required", ()))
        for name in ("record_type", "schema_version"):
            if name not in schema.get("properties", {}):
                raise ValueError("response model lacks the required F02 version envelope")
            if name not in required:
                required.append(name)
        schema["required"] = required

    job_ids = tuple(job.job_id for job in state.waiting_jobs)
    evidence_ids = _visible_evidence_ids(state)

    plan = _definition(schema, "Plan")
    if plan is not None:
        props = plan["properties"]
        required = list(plan.get("required", ()))
        for name in ("record_type", "schema_version", "starts", "deferrals", "abstentions"):
            if name not in required:
                required.append(name)
        plan["required"] = required
        props["episode_id"] = {"const": state.episode_id, "type": "string"}
        props["slot"] = {"const": state.current_slot, "type": "integer"}
        props["state_version"] = {"const": state.state_version, "type": "integer"}
        props["status"] = {"const": "proposed", "type": "string"}
        for name in ("starts", "deferrals", "abstentions"):
            props[name]["maxItems"] = limits.plan_entries
        _bound_ids(props["evidence_ids"], evidence_ids, limits.evidence_ids)

        for name in ("PlannedStart", "Deferral", "Abstention"):
            entry = schema.get("$defs", {}).get(name)
            if entry is None and schema.get("title") == "Plan":
                entry = schema.get("$defs", {}).get(name)
            if entry is None:
                raise ValueError(f"Plan schema lacks {name}")
            _bound_job_id(entry["properties"]["job_id"], job_ids, nullable=name == "Abstention")
            if name in {"Deferral", "Abstention"}:
                _bound_text(entry["properties"]["detail"], limits.text_characters)
                _bound_ids(entry["properties"]["evidence_ids"], evidence_ids, limits.evidence_ids)
            if name == "Abstention":
                constraint_ids = tuple(sorted(state.constraint_ids))
                _bound_ids(
                    entry["properties"]["constraint_ids"],
                    constraint_ids,
                    limits.evidence_ids,
                )
        schema["$defs"]["PlannedStart"]["properties"]["start_slot"]["maximum"] = 29

    explanation = _definition(schema, "Explanation")
    if explanation is not None:
        props = explanation["properties"]
        props["source"] = {"const": "llm", "type": "string"}
        _bound_text(props["summary"], limits.explanation_characters)
        props["claims"]["maxItems"] = limits.claims
        props["limitations"]["maxItems"] = limits.limitations
        _bound_text(props["limitations"]["items"], limits.explanation_characters)
        claim = schema.get("$defs", {}).get("Claim")
        if claim is None:
            raise ValueError("Explanation schema lacks Claim")
        _bound_text(claim["properties"]["text"], limits.explanation_characters)
        claim["properties"]["claim_id"]["maxLength"] = 16
        _bound_ids(claim["properties"]["evidence_ids"], evidence_ids, limits.evidence_ids)
        schema["$defs"]["Claim"] = _paired_claim(claim)

    if response_model is s.PolicyOutput:
        props = schema["properties"]
        props["system"] = {"const": system, "type": "string"}
        props["output_status"] = {"const": "ok", "type": "string"}
        props["raw_response"] = {"const": None, "type": "null"}
        # A successful model output must explicitly carry its plan. F02's optional
        # field remains useful for non-model failure records and is unchanged.
        props["plan"] = {"$ref": "#/$defs/Plan"}
        if "plan" not in schema["required"]:
            schema["required"].append("plan")

    return schema, limits


def validate_explicit_actions(content: str, response_model: type[s.Record]) -> None:
    """Reject omitted model action fields before F02 can supply empty defaults.

    This checks shape only, never action quality or a nonempty schedule. The raw
    provider response is retained by the caller even when this validation fails.
    """
    if response_model is s.Explanation:
        return
    import json

    value = json.loads(content)
    plan = (
        value.get("plan") if response_model is s.PolicyOutput and isinstance(value, dict) else value
    )
    if not isinstance(plan, dict):
        raise ValueError("model output requires an explicit plan object")
    for name in ("starts", "deferrals", "abstentions"):
        if name not in plan or not isinstance(plan[name], list):
            raise ValueError(f"model plan requires an explicit {name} array")
