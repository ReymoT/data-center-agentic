"""E04 claim-review material: blinded cases, annotation records and per-output metrics.

A case is one decision state with two blinded outputs, "X" and "Y". Annotation records
follow the draft extraction rule in ``docs/e04/EXTRACTION_RULE.md``: every F02 Claim
record is one assertion with its own ID, and raters add the checkable assertions they
extract from the summary ("S1", "S2", ...) and limitations ("L1", ...). Labels and
completeness are filled by the human raters; nothing here assigns a label.

Q10 is still partial, so this is development material under a draft rubric, not a
frozen protocol. Metrics follow MASTER_NISHA E04: faithfulness = supported/checkable,
coverage = assertions with a supporting citation/checkable, precision = supporting
claim-citation pairs/all cited pairs; zero denominators stay undefined (None).
Draft 1 (rule §11.6–11.7) adds two optional annotation-only parts, never F02 fields:
a ``reference_kind`` from a closed list on an assertion, and raw-text assertions
("R1", "R2", ...) extracted from the ``raw_response`` of an output without an
explanation. Raw-text assertions are scored separately and never enter the structured
metrics. Human extraction/deduplication, unresolved units and two independent original
ratings remain gates before a frozen real-output review.
"""

import re
from dataclasses import dataclass

from dc_sustainability import schemas as s

RUBRIC_VERSION = "e04-extraction-draft-0"
LABELS = ("supported", "contradicted", "unsupported")
COMPLETENESS = ("decision", "reason", "evidence", "limitations")
OUTPUT_KEYS = ("X", "Y")
_EXTRACTED_ID = {
    "summary": re.compile(r"^S[1-9][0-9]*$"),
    "limitation": re.compile(r"^L[1-9][0-9]*$"),
    "raw": re.compile(r"^R[1-9][0-9]*$"),
}
# Rule §11.6, Ved's closed list (#24): the quantity a numeric assertion describes.
REFERENCE_KINDS = (
    "job_it_energy",  # job IT energy before PUE
    "job_facility_energy",  # job facility energy with PUE
    "job_emissions",
    "schedule_emissions",
    "savings_vs_baseline",
    "carbon_intensity",  # at a slot
    "power_load_capacity",  # at a slot
    "slot_or_duration",
)


@dataclass(frozen=True)
class BlindOutput:
    """A policy output with the system identity removed for blinded review."""

    output_status: str
    plan: s.Plan | None
    explanation: s.Explanation | None
    raw_response: str | None

    @property
    def empty_plan_without_text(self) -> bool:
        """A no-op candidate; its case must also confirm an empty waiting queue."""
        p = self.plan
        return (
            self.output_status == "ok"
            and self.explanation is None
            and self.raw_response is None
            and p is not None
            and not (p.starts or p.deferrals or p.abstentions)
        )


@dataclass(frozen=True)
class ReviewCase:
    case_id: str
    snapshot: s.ConstraintSnapshot
    state: s.VisibleState
    outputs: dict[str, BlindOutput]

    def not_applicable(self, key: str) -> bool:
        """Q10 exempts only an empty-queue no-op, never an omitted waiting-job decision."""
        return not self.state.waiting_jobs and self.outputs[key].empty_plan_without_text


def _blind_output(data: dict, state: s.VisibleState) -> BlindOutput:
    if set(data) != {"output_status", "plan", "explanation", "raw_response"}:
        raise ValueError(f"blinded output fields are {sorted(data)}")
    status = data["output_status"]
    if status not in ("ok", "no_output", "malformed", "error"):
        raise ValueError(f"unknown output_status {status!r}")
    plan = None if data["plan"] is None else s.Plan.from_jsonable(data["plan"])
    if (status == "ok") != (plan is not None):
        raise ValueError("a plan accompanies exactly the 'ok' outputs")
    if plan is not None and (plan.episode_id, plan.slot, plan.state_version) != (
        state.episode_id,
        state.current_slot,
        state.state_version,
    ):
        raise ValueError("plan is bound to a different decision")
    explanation = data["explanation"]
    if explanation is not None:
        explanation = s.Explanation.from_jsonable(explanation)
    raw = data["raw_response"]
    if raw is not None and (not isinstance(raw, str) or not raw):
        raise ValueError("raw_response must be a non-empty string or null")
    return BlindOutput(status, plan, explanation, raw)


def load_cases(data: dict) -> tuple[ReviewCase, ...]:
    """Validate the case file: F02 records, decision binding and blinded output keys."""
    if data.get("rubric_version") != RUBRIC_VERSION:
        raise ValueError("case file is for another rubric version")
    cases, seen = [], set()
    for raw in data["cases"]:
        snapshot = s.ConstraintSnapshot.from_jsonable(raw["snapshot"])
        state = s.VisibleState.from_jsonable(raw["state"])
        if state.constraint_snapshot_id != snapshot.snapshot_id:
            raise ValueError(f"{raw['case_id']}: state and snapshot differ")
        if state.site != snapshot.site:
            raise ValueError(f"{raw['case_id']}: state site differs from its snapshot")
        if not set(state.constraint_ids) <= {c.constraint_id for c in snapshot.constraints}:
            raise ValueError(f"{raw['case_id']}: visible constraint is absent from its snapshot")
        if raw["case_id"] in seen:
            raise ValueError(f"duplicate case {raw['case_id']}")
        seen.add(raw["case_id"])
        if tuple(sorted(raw["outputs"])) != OUTPUT_KEYS:
            raise ValueError(f"{raw['case_id']}: outputs must be exactly X and Y")
        outputs = {k: _blind_output(v, state) for k, v in raw["outputs"].items()}
        cases.append(ReviewCase(raw["case_id"], snapshot, state, outputs))
    return tuple(cases)


def blank_annotation(case: ReviewCase, key: str) -> dict:
    """The rater's starting record: Claim assertions pre-listed, every judgement empty."""
    output = case.outputs[key]
    claims = output.explanation.claims if output.explanation else ()
    return {
        "case_id": case.case_id,
        "output": key,
        "not_applicable": case.not_applicable(key),
        "explanation_present": output.explanation is not None,
        "assertions": [
            {
                "assertion_id": c.claim_id,
                "source": "claim",
                "text": c.text,
                "label": None,
                "cited_ids": list(c.evidence_ids),
                "supporting_cited_ids": None,
                "restated_in_summary": None,
            }
            for c in claims
        ],
        "completeness": None if case.not_applicable(key) else dict.fromkeys(COMPLETENESS),
        "notes": "",
    }


def validate_annotation(case: ReviewCase, entry: dict, *, complete: bool) -> None:
    """Refuse an annotation that breaks the extraction rule; ``complete`` requires judgements.

    Raises ValueError with the first problem found. It checks structure only and never
    decides whether a label is right.
    """
    key = entry.get("output")
    if entry.get("case_id") != case.case_id or key not in case.outputs:
        raise ValueError("annotation is for another case or output")
    output = case.outputs[key]
    where = f"{case.case_id}/{key}"
    if entry.get("not_applicable") is not case.not_applicable(key):
        raise ValueError(f"{where}: not_applicable must be {case.not_applicable(key)}")
    if entry.get("explanation_present") is not (output.explanation is not None):
        raise ValueError(f"{where}: explanation_present does not match the output")
    assertions = entry.get("assertions")
    if not isinstance(assertions, list):
        raise ValueError(f"{where}: assertions must be a list")
    raw = [a for a in assertions if a.get("source") == "raw"]
    if raw and (output.explanation is not None or output.raw_response is None):
        raise ValueError(f"{where}: raw-text assertions need raw text and no explanation")
    if output.explanation is None and len(raw) != len(assertions):
        raise ValueError(f"{where}: an output without an explanation has only raw assertions")

    claims = {c.claim_id: c for c in output.explanation.claims} if output.explanation else {}
    ids = [a.get("assertion_id") for a in assertions]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{where}: repeated assertions share one ID and appear once")
    listed_claims = [a["assertion_id"] for a in assertions if a.get("source") == "claim"]
    if sorted(listed_claims) != sorted(claims):
        raise ValueError(f"{where}: every Claim record is exactly one assertion")
    for a in assertions:
        _check_assertion(a, claims, complete, where)

    completeness = entry.get("completeness")
    if case.not_applicable(key):
        if completeness is not None:
            raise ValueError(f"{where}: a no-op has no completeness rating")
        return
    if not isinstance(completeness, dict) or set(completeness) != set(COMPLETENESS):
        raise ValueError(f"{where}: completeness rates {', '.join(COMPLETENESS)}")
    for part, value in completeness.items():
        allowed = (0, 1) if complete else (0, 1, None)
        if value not in allowed or isinstance(value, bool):
            raise ValueError(f"{where}: completeness {part} must be 0 or 1")
        if output.explanation is None and value == 1:
            raise ValueError(f"{where}: an empty explanation has 0 completeness")


def _check_assertion(a: dict, claims: dict, complete: bool, where: str) -> None:
    aid, source = a.get("assertion_id"), a.get("source")
    if source == "claim":
        claim = claims.get(aid)
        if claim is None or a.get("text") != claim.text:
            raise ValueError(f"{where}: {aid} does not match its Claim record")
        if a.get("cited_ids") != list(claim.evidence_ids):
            raise ValueError(f"{where}: {aid} cited IDs must be the Claim's evidence IDs")
        restated = a.get("restated_in_summary")
        if type(restated) is not bool and not (restated is None and not complete):
            raise ValueError(f"{where}: {aid} restated_in_summary must be true or false")
    elif source in _EXTRACTED_ID:
        if not isinstance(aid, str) or not _EXTRACTED_ID[source].match(aid):
            raise ValueError(f"{where}: {source} assertion IDs look like S1, L1 or R1")
        if not isinstance(a.get("text"), str) or not a["text"].strip():
            raise ValueError(f"{where}: {aid} needs the extracted text")
        if a.get("cited_ids") != [] or "restated_in_summary" in a:
            raise ValueError(f"{where}: {aid} has no citations or restatement flag")
    else:
        raise ValueError(f"{where}: unknown assertion source {source!r}")
    if "reference_kind" in a and a["reference_kind"] not in (None, *REFERENCE_KINDS):
        raise ValueError(f"{where}: {aid} reference_kind must be one of {REFERENCE_KINDS}")
    label = a.get("label")
    if label not in LABELS and not (label is None and not complete):
        raise ValueError(f"{where}: {aid} label must be one of {', '.join(LABELS)}")
    supporting = a.get("supporting_cited_ids")
    if supporting is None:
        if complete:
            raise ValueError(f"{where}: {aid} needs supporting_cited_ids (may be empty)")
    elif not isinstance(supporting, list) or not set(supporting) <= set(a["cited_ids"]):
        raise ValueError(f"{where}: {aid} supporting IDs must be among its cited IDs")
    elif len(supporting) != len(set(supporting)):
        raise ValueError(f"{where}: {aid} supporting IDs must be unique")


@dataclass(frozen=True)
class OutputScore:
    checkable: int
    supported: int
    faithfulness: float | None
    coverage: float | None
    precision: float | None
    completeness: float | None
    # Raw-text assertions (rule §11.7), kept apart from the structured metrics above.
    raw_checkable: int = 0
    raw_supported: int = 0

    @property
    def raw_faithfulness(self) -> float | None:
        return self.raw_supported / self.raw_checkable if self.raw_checkable else None


def score_annotation(case: ReviewCase, entry: dict) -> OutputScore | None:
    """Per-output metrics from one rater's complete annotation; None for a no-op."""
    validate_annotation(case, entry, complete=True)
    if entry["not_applicable"]:
        return None
    raw = [a for a in entry["assertions"] if a["source"] == "raw"]
    assertions = [a for a in entry["assertions"] if a["source"] != "raw"]
    n = len(assertions)
    supported = sum(a["label"] == "supported" for a in assertions)
    covered = sum(bool(a["supporting_cited_ids"]) for a in assertions)
    cited = sum(len(a["cited_ids"]) for a in assertions)
    pairs = sum(len(a["supporting_cited_ids"]) for a in assertions)
    parts = entry["completeness"]
    return OutputScore(
        checkable=n,
        supported=supported,
        faithfulness=supported / n if n else None,
        # An empty explanation has 0 coverage (MASTER_NISHA E04), not undefined.
        coverage=covered / n if n else (0.0 if not entry["explanation_present"] else None),
        precision=pairs / cited if cited else None,
        completeness=sum(parts.values()) / len(COMPLETENESS),
        raw_checkable=len(raw),
        raw_supported=sum(a["label"] == "supported" for a in raw),
    )


def render_packet(cases: tuple[ReviewCase, ...]) -> str:
    """Markdown packet for raters: decision facts and both outputs, no system or answers."""
    lines = [
        "# E04 development cases: rater packet",
        "",
        f"Rubric `{RUBRIC_VERSION}`. Synthetic pilot cases written for rubric development; "
        "they are not model outputs. Rate each output independently using "
        "[EXTRACTION_RULE.md](EXTRACTION_RULE.md) and `annotation_template.json`, before "
        "discussing with the other rater or opening the case generator script.",
        "",
    ]
    for case in cases:
        lines += [f"## {case.case_id}", ""] + _facts(case) + [""]
        for key in OUTPUT_KEYS:
            lines += [f"### Output {key}", ""] + _output(case.outputs[key]) + [""]
    return "\n".join(lines).rstrip() + "\n"


def _facts(case: ReviewCase) -> list[str]:
    st, snap = case.state, case.snapshot
    visible = set(st.constraint_ids)
    cons = [c for c in snap.constraints if c.constraint_id in visible]
    cap = [c for c in cons if c.constraint_type == "capacity"]
    lines = [
        f"Decision slot {st.current_slot} (episode {st.episode_id}). Site {st.site.site_id}: "
        f"background {st.site.background_kw:g} kW, PUE {st.site.pue:g}, "
        f"{st.site.slot_hours:g} h per slot. "
        + (
            f"Capacity {cap[0].limit_value:g} kW ({cap[0].constraint_id})."
            if cap
            else "No capacity constraint is on record."
        ),
        "",
        "| Job | State | Arrival | Duration (slots) | Power (kW) | Deadline | Flexible |",
        "|---|---|---|---|---|---|---|",
    ]
    rows = [(j, "waiting", None) for j in st.waiting_jobs]
    rows += [(r.job, f"running since slot {r.start_slot}", None) for r in st.running_jobs]
    for j, label, _ in rows:
        lines.append(
            f"| {j.job_id} | {label} | {j.arrival_slot} | {j.duration_slots} | "
            f"{j.power_kw:g} | {j.deadline_slot} | {'yes' if j.flexible else 'no'} |"
        )
    for c in st.completed_jobs:
        lines.append(
            f"| {c.job_id} | completed (slots {c.start_slot}–{c.end_slot - 1}) | | | | | |"
        )
    for j in st.missed_job_ids:
        lines.append(f"| {j} | missed | | | | | |")
    lines += [
        "",
        "Visible constraints: "
        + (
            ", ".join(
                f"{c.constraint_id} ({c.constraint_type} {c.limit_value:g} {c.unit})" for c in cons
            )
            or "none"
        )
        + ".",
    ]
    if st.carbon_facts:
        issued = {f.issued_at_utc for f in st.carbon_facts}
        lines += [
            "",
            f"Carbon forecasts ({st.carbon_facts[0].forecast_kind}, issued "
            + ", ".join(sorted(t.isoformat() for t in issued))
            + "):",
            "",
            "| Slot | g/kWh | Fact ID |",
            "|---|---|---|",
        ]
        lines += [f"| {f.valid_slot} | {f.value:g} | {f.fact_id} |" for f in st.carbon_facts]
    else:
        lines += ["", "No carbon forecasts are visible."]
    if st.missing_carbon_slots:
        lines += ["", f"Missing forecast slots: {_ranges(st.missing_carbon_slots)}."]
    return lines


def _ranges(slots) -> str:
    slots, out, start = sorted(slots), [], None
    for i, v in enumerate(slots):
        start = v if start is None else start
        if i + 1 == len(slots) or slots[i + 1] != v + 1:
            out.append(str(v) if start == v else f"{start}–{v}")
            start = None
    return ", ".join(out)


def _output(o: BlindOutput) -> list[str]:
    lines = [f"Status: `{o.output_status}`."]
    if o.plan is not None:
        p = o.plan
        parts = [f"start {x.job_id} at slot {x.start_slot}" for x in p.starts]
        parts += [f"defer {d.job_id} ({d.reason})" for d in p.deferrals]
        parts += [
            f"abstain from {a.job_id or 'all waiting jobs'} ({a.reason})" for a in p.abstentions
        ]
        lines.append("Plan: " + ("; ".join(parts) if parts else "no action (no-op)") + ".")
    if o.raw_response is not None and o.explanation is None:
        lines += ["", "Raw response:", "", "```", o.raw_response, "```"]
    if o.explanation is None:
        lines += ["", "No explanation."]
        return lines
    e = o.explanation
    lines += ["", f"Summary: {e.summary}", ""]
    if e.claims:
        lines += ["| Claim | Text | Value | Evidence |", "|---|---|---|---|"]
        for c in e.claims:
            value = "" if c.value is None else f"{c.value:g} {c.unit or ''}".strip()
            lines.append(f"| {c.claim_id} | {c.text} | {value} | {', '.join(c.evidence_ids)} |")
    else:
        lines.append("No claim records.")
    lines += [""] + (
        [f"Limitations: {'; '.join(e.limitations)}"]
        if e.limitations
        else ["No limitations listed."]
    )
    return lines
