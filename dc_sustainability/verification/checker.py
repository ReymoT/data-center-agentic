"""A03 fixed-rule checks using F02 records; unresolved Q01-Q04 cannot approve execution.

This is production logic, independent of the evaluation validator. It returns actual
subcheck results, not an execution permit. Until coverage/partial-infeasibility rules
are agreed, an otherwise feasible proposal returns an explicit error, never a pass.
"""

from uuid import uuid4

from dc_sustainability import schemas as s


def check_schedule(
    plan: s.Plan, visible_state: s.VisibleState, constraints: s.ConstraintSnapshot
) -> s.CheckResult:
    """Check immutable visible inputs without simulator access or reference answers.

    Invalid F02 inputs raise ValueError before a check can be bound to their identity.
    Cross-record mismatches produce an error result. Known physical violations are
    rejected independently of the unresolved rules. No approvals are issued here.
    """
    # Pydantic model_copy/model_construct can bypass validation: revalidate boundaries.
    plan = s.Plan.model_validate(plan.model_dump(mode="python", warnings="none"), strict=True)
    state = s.VisibleState.model_validate(
        visible_state.model_dump(mode="python", warnings="none"), strict=True
    )
    snapshot = s.ConstraintSnapshot.model_validate(
        constraints.model_dump(mode="python", warnings="none"), strict=True
    )
    performed = [s.PerformedCheck(name="schema", outcome="pass")]
    violations: list[s.Violation] = []
    errors: list[str] = []
    skipped = [s.SkippedCheck(name="freshness", reason="Q04 issue-time and freshness rule pending")]
    evidence: list[s.EvidenceItem] = []

    def result() -> s.CheckResult:
        return s.CheckResult(
            check_id=f"CHK-{uuid4().hex}",
            episode_id=plan.episode_id,
            slot=plan.slot,
            state_version=state.state_version,
            plan_hash=plan.plan_hash,
            status="error" if errors else "fail",
            violations=tuple(violations),
            performed=tuple(performed),
            skipped=tuple(skipped),
            evidence=tuple(evidence),
            impact_claim_support=(
                "unsupported"
                if not state.carbon_facts
                or state.missing_carbon_slots
                or any(
                    f.semantics.pollutant_basis == "unresolved"
                    or f.semantics.slot_mapping_status != "agreed"
                    for f in state.carbon_facts
                )
                else "not_assessed"
            ),
            errors=tuple(errors),
        )

    if (plan.episode_id, plan.slot, plan.state_version) != (
        state.episode_id,
        state.current_slot,
        state.state_version,
    ):
        errors.append("proposal episode/slot/state version does not match the visible state")
        performed.append(s.PerformedCheck(name="ids", outcome="error"))
        return result()
    try:
        context = s.Context.build(state, snapshot, representation="flat")
    except ValueError as exc:
        errors.append(f"inconsistent authoritative evidence: {exc}")
        performed.append(s.PerformedCheck(name="evidence", outcome="error"))
        return result()

    available = set(context.content.evidence_ids)
    cited = set(plan.evidence_ids)
    for entry in (*plan.deferrals, *plan.abstentions):
        cited.update(entry.evidence_ids)
    for abstention in plan.abstentions:
        cited.update(abstention.constraint_ids)
    missing = sorted(cited - available)
    if missing:
        violations.append(
            s.Violation(
                violation_type="missing_evidence",
                message=f"unknown/unavailable citations: {missing}",
            )
        )
    performed.append(s.PerformedCheck(name="evidence", outcome="fail" if missing else "pass"))
    jobs = {job.job_id: job for job in state.waiting_jobs}
    mentioned = {item.job_id for item in (*plan.starts, *plan.deferrals)}
    mentioned.update(a.job_id for a in plan.abstentions if a.job_id is not None)
    unknown = sorted(mentioned - jobs.keys())
    for job_id in unknown:
        violations.append(
            s.Violation(
                violation_type="unknown_job",
                job_ids=(job_id,),
                message="job is not waiting; running/completed/missed work cannot be rescheduled",
            )
        )
    performed.append(s.PerformedCheck(name="ids", outcome="fail" if unknown else "pass"))

    horizon = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
    outcomes = {name: "pass" for name in ("timing", "deadline", "nonflexible")}
    related = {name: set() for name in outcomes}

    def reject(name, kind, job_id, slot, message):
        outcomes[name] = "fail"
        ids = tuple(sorted(related[name]))
        violations.append(
            s.Violation(
                violation_type=kind,
                job_ids=(job_id,),
                constraint_ids=ids,
                slot=slot,
                message=message,
            )
        )

    for start in plan.starts:
        job = jobs.get(start.job_id)
        if job is None:
            continue
        job_constraints = [
            c for c in context.content.constraints if job.job_id in c.applies_to_jobs
        ]
        related["timing"] = {
            c.constraint_id for c in job_constraints if c.constraint_type == "arrival"
        }
        related["deadline"] = {
            c.constraint_id for c in job_constraints if c.constraint_type == "deadline"
        }
        related["nonflexible"] = {
            c.constraint_id for c in job_constraints if c.constraint_type == "nonflexible"
        }
        if start.start_slot < job.arrival_slot:
            reject(
                "timing",
                "start_before_arrival",
                job.job_id,
                start.start_slot,
                "start precedes arrival",
            )
        if start.start_slot < state.current_slot:
            reject(
                "timing", "start_before_current", job.job_id, start.start_slot, "start is backdated"
            )
        end = start.start_slot + job.duration_slots
        if end > job.deadline_slot:
            reject(
                "deadline",
                "deadline",
                job.job_id,
                start.start_slot,
                f"finish {end} exceeds deadline {job.deadline_slot}",
            )
        if end > horizon:
            reject(
                "timing", "other", job.job_id, start.start_slot, "work exceeds the 30-slot episode"
            )
        if not job.flexible and start.start_slot != job.arrival_slot:
            reject(
                "nonflexible",
                "nonflexible_start",
                job.job_id,
                start.start_slot,
                "nonflexible work must start at arrival",
            )
        if start.start_slot >= s.PROPOSED_DECISION_SLOTS:
            errors.append(f"Q01 completion-slot start unresolved for {job.job_id}")
    for name, outcome in outcomes.items():
        ids = tuple(
            c.constraint_id
            for c in context.content.constraints
            if c.constraint_type
            == {"timing": "arrival", "deadline": "deadline", "nonflexible": "nonflexible"}[name]
        )
        performed.append(s.PerformedCheck(name=name, outcome=outcome, constraint_ids=ids))

    capacity_constraints = snapshot.constraints_of("capacity")
    cap_ids = tuple(c.constraint_id for c in capacity_constraints)
    evidence.extend(
        (
            s.EvidenceItem(
                kind="capacity", status="available" if cap_ids else "missing", ids=cap_ids
            ),
            s.EvidenceItem(kind="constraints", status="available", ids=tuple(state.constraint_ids)),
            s.EvidenceItem(
                kind="jobs", status="available", ids=tuple(f"FACT-JOB-{j}" for j in jobs)
            ),
            s.EvidenceItem(
                kind="carbon",
                status=(
                    "missing"
                    if not state.carbon_facts
                    else "partial"
                    if state.missing_carbon_slots
                    else "available"
                ),
                ids=tuple(f.fact_id for f in state.carbon_facts),
            ),
        )
    )
    if not cap_ids:
        errors.append("required authoritative capacity evidence is missing")
        performed.append(s.PerformedCheck(name="capacity", outcome="error"))
    else:
        capacity = snapshot.capacity_kw
        overloaded = False
        # Check background and running work even if no new work was proposed.
        for slot in range(state.current_slot, horizon):
            occupying = [
                start.job_id
                for start in plan.starts
                if start.job_id in jobs
                and start.start_slot <= slot < start.start_slot + jobs[start.job_id].duration_slots
            ]
            running = [
                r.job.job_id for r in state.running_jobs if r.start_slot <= slot < r.end_slot
            ]
            load = state.site.background_kw + state.running_job_load_kw(slot)
            load += sum(jobs[job_id].power_kw for job_id in occupying)
            if load > capacity:
                overloaded = True
                violations.append(
                    s.Violation(
                        violation_type="capacity",
                        job_ids=tuple(sorted(occupying + running)),
                        constraint_ids=cap_ids,
                        slot=slot,
                        message=f"IT load {load:g} kW exceeds authoritative capacity {capacity:g} kW",
                    )
                )
        performed.append(
            s.PerformedCheck(
                name="capacity", outcome="fail" if overloaded else "pass", constraint_ids=cap_ids
            )
        )
    if not violations:
        errors.append(
            "Q02/Q03 partial-infeasibility, coverage and deferral rules pending; no execution approval"
        )
    return result()
