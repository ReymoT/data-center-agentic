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


def response_bounds(state: s.VisibleState) -> ResponseBounds:
    """Return bounds for a visible decision without consulting results.

    The policy layers retain the accepted empty-queue no-call rule.  A zero-entry
    grammar is still defined here so the low-level shared adapter remains total and
    run-budget checks cannot be bypassed by changing the visible queue.
    """

    state = s.VisibleState.model_validate(
        state.model_dump(mode="python", warnings="none"), strict=True
    )
    return ResponseBounds(plan_entries=len(state.waiting_jobs))


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


def bounded_response_schema(
    response_model: type[s.Record],
    state: s.VisibleState,
    *,
    system: str,
) -> tuple[dict, ResponseBounds]:
    """Build the one bounded grammar used by both LLM systems.

    The returned object is a request-local copy.  It pins plan identity to the
    visible decision, permits one plan entry per waiting job in every action
    category, applies identical explanation limits to Plain and Agent, and
    prevents the model from filling ``raw_response`` (the caller retains the
    actual original response separately).
    """

    state = s.VisibleState.model_validate(
        state.model_dump(mode="python", warnings="none"), strict=True
    )
    if system not in {"agent", "plain_llm"}:
        raise ValueError("response bounds apply only to the two LLM systems")
    if response_model not in {s.Plan, s.PolicyOutput, s.Explanation}:
        raise ValueError("response bounds require Plan, PolicyOutput or Explanation")
    limits = response_bounds(state)
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
        for name in ("record_type", "schema_version"):
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
        _bound_text(props["summary"], limits.text_characters)
        props["claims"]["maxItems"] = limits.claims
        props["limitations"]["maxItems"] = limits.limitations
        _bound_text(props["limitations"]["items"], limits.text_characters)
        claim = schema.get("$defs", {}).get("Claim")
        if claim is None:
            raise ValueError("Explanation schema lacks Claim")
        _bound_text(claim["properties"]["text"], limits.text_characters)
        claim["properties"]["claim_id"]["maxLength"] = 16
        _bound_ids(claim["properties"]["evidence_ids"], evidence_ids, limits.evidence_ids)

    if response_model is s.PolicyOutput:
        props = schema["properties"]
        props["system"] = {"const": system, "type": "string"}
        props["output_status"] = {"const": "ok", "type": "string"}
        props["raw_response"] = {"const": None, "type": "null"}

    return schema, limits
