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

Rule §11.9 (#185) adds an optional ``cap_review``: the code lists every summary,
limitation and claim text that reached the request's length limit (a cap hit), and
raters decide only whether each one is visibly unfinished, recording the cut-off tail.
A summary sentence or limitation that is only that tail takes the ``cut_off`` text
decision, never an assertion. The limit is an input, never assumed.
"""

import re
from collections.abc import Iterable
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
    """One decision shown to raters with two blinded outputs.

    Development cases share one ``state``. Study cases set ``states`` instead: the two
    systems follow different trajectories, so each output is judged against the visible
    state its own system faced at that slot (``state`` is then None).
    """

    case_id: str
    snapshot: s.ConstraintSnapshot
    state: s.VisibleState | None
    outputs: dict[str, BlindOutput]
    states: dict[str, s.VisibleState] | None = None

    def state_for(self, key: str) -> s.VisibleState:
        return self.states[key] if self.states is not None else self.state

    def not_applicable(self, key: str) -> bool:
        """Q10 exempts only an empty-queue no-op, never an omitted waiting-job decision."""
        return not self.state_for(key).waiting_jobs and self.outputs[key].empty_plan_without_text


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
        if ("state" in raw) == ("states" in raw):
            raise ValueError(f"{raw['case_id']}: give exactly one of 'state' or 'states'")
        if "states" in raw:
            if tuple(sorted(raw["states"])) != OUTPUT_KEYS:
                raise ValueError(f"{raw['case_id']}: states must be exactly X and Y")
            states = {k: s.VisibleState.from_jsonable(v) for k, v in raw["states"].items()}
            shared = None
        else:
            shared = s.VisibleState.from_jsonable(raw["state"])
            states = None
        for state in states.values() if states else (shared,):
            if state.constraint_snapshot_id != snapshot.snapshot_id:
                raise ValueError(f"{raw['case_id']}: state and snapshot differ")
            if state.site != snapshot.site:
                raise ValueError(f"{raw['case_id']}: state site differs from its snapshot")
            if not set(state.constraint_ids) <= {c.constraint_id for c in snapshot.constraints}:
                raise ValueError(
                    f"{raw['case_id']}: visible constraint is absent from its snapshot"
                )
        if states and len({(x.episode_id, x.current_slot) for x in states.values()}) != 1:
            raise ValueError(f"{raw['case_id']}: both states must be the same episode and slot")
        if raw["case_id"] in seen:
            raise ValueError(f"duplicate case {raw['case_id']}")
        seen.add(raw["case_id"])
        if tuple(sorted(raw["outputs"])) != OUTPUT_KEYS:
            raise ValueError(f"{raw['case_id']}: outputs must be exactly X and Y")
        outputs = {
            k: _blind_output(v, states[k] if states else shared) for k, v in raw["outputs"].items()
        }
        cases.append(ReviewCase(raw["case_id"], snapshot, shared, outputs, states))
    return tuple(cases)


def blank_annotation(
    case: ReviewCase, key: str, *, text_review: bool = False, cap_limit: int | None = None
) -> dict:
    """The rater's starting record: Claim assertions pre-listed, every judgement empty.

    With ``cap_limit`` the computed cap hits are listed for the rater's §11.9 decision.
    """
    output = case.outputs[key]
    claims = output.explanation.claims if output.explanation else ()
    entry = {
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
    if text_review:
        entry["text_review"] = {
            source: [{"text": text, "decision": None, "assertion_ids": []} for text in texts]
            for source, texts in review_units(output).items()
        }
    if cap_limit is not None:
        entry["cap_review"] = {
            "limit": cap_limit,
            "units": [
                {"field": f, "unit": u, "unfinished": None, "cut_off_text": None}
                for f, u in cap_hits(output, cap_limit)
            ],
        }
    return entry


def review_units(output: BlindOutput) -> dict[str, list[str]]:
    """Stable review units: summary/raw sentences and each whole limitation."""

    def sentences(text):
        return [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part]

    explanation = output.explanation
    return {
        "summary": sentences(explanation.summary) if explanation else [],
        "limitation": list(explanation.limitations) if explanation else [],
        "raw": sentences(output.raw_response) if output.raw_response and not explanation else [],
    }


CAP_FIELDS = ("summary", "limitation", "claim")


def cap_hits(output: BlindOutput, limit: int) -> list[tuple[str, str]]:
    """Explanation texts whose length reached ``limit`` (rule §11.9), in source order.

    Each hit is (field, unit): ("summary", "summary"), ("limitation", "<index from 0>")
    or ("claim", "<claim ID>"). Computed by code, so both raters see the same list.
    """
    if type(limit) is not int or limit < 1:
        raise ValueError("the length limit must be a positive integer")
    e = output.explanation
    if e is None:
        return []
    hits = [("summary", "summary")] if len(e.summary) == limit else []
    hits += [("limitation", str(i)) for i, t in enumerate(e.limitations) if len(t) == limit]
    hits += [("claim", c.claim_id) for c in e.claims if len(c.text) == limit]
    return hits


def _cap_text(output: BlindOutput, field: str, unit: str) -> str:
    e = output.explanation
    if field == "summary":
        return e.summary
    if field == "limitation":
        return e.limitations[int(unit)]
    return next(c.text for c in e.claims if c.claim_id == unit)


def _validate_cap_review(output: BlindOutput, entry: dict, complete: bool) -> None:
    record = entry["cap_review"]
    if not isinstance(record, dict) or set(record) != {"limit", "units"}:
        raise ValueError("cap_review has exactly limit and units")
    hits = cap_hits(output, record["limit"])
    units = record["units"]
    if (
        not isinstance(units, list)
        or [(u.get("field"), u.get("unit")) if isinstance(u, dict) else None for u in units] != hits
    ):
        raise ValueError("cap_review units must be exactly the computed cap hits, in order")
    for u in units:
        if set(u) != {"field", "unit", "unfinished", "cut_off_text"}:
            raise ValueError("invalid cap_review unit")
        unfinished, tail = u["unfinished"], u["cut_off_text"]
        if unfinished is None and not complete and tail is None:
            continue
        if type(unfinished) is not bool:
            raise ValueError("every cap hit needs an unfinished decision (true or false)")
        if not unfinished and tail is not None:
            raise ValueError("a finished cap hit has no cut-off text")
        text = _cap_text(output, u["field"], u["unit"])
        if unfinished and not (isinstance(tail, str) and tail.strip() and text.endswith(tail)):
            raise ValueError("cut_off_text must be the exact non-empty end of the capped text")


def _cut_off_units(units: dict[str, list[str]], entry: dict) -> set[tuple[str, int]]:
    """Text-review positions that may be decided ``cut_off``: the end of an unfinished text."""
    allowed = set()
    for u in entry.get("cap_review", {}).get("units", []):
        if u.get("unfinished") is True:
            if u["field"] == "summary":
                position = len(units["summary"]) - 1
                if units["summary"][position].strip() == u["cut_off_text"].strip():
                    allowed.add(("summary", position))
            elif u["field"] == "limitation":
                position = int(u["unit"])
                if units["limitation"][position].strip() == u["cut_off_text"].strip():
                    allowed.add(("limitation", position))
    return allowed


def _validate_text_review(output: BlindOutput, entry: dict, complete: bool) -> None:
    audit = entry["text_review"]
    units = review_units(output)
    cut_off = _cut_off_units(units, entry)
    if not isinstance(audit, dict) or set(audit) != set(units):
        raise ValueError("text_review must cover summary, limitation and raw units")
    assertions = {a["assertion_id"]: a for a in entry["assertions"]}
    referenced = set()
    for source, texts in units.items():
        rows = audit[source]
        if not isinstance(rows, list) or len(rows) != len(texts):
            raise ValueError("every text unit needs a recorded decision")
        for position, (row, text) in enumerate(zip(rows, texts)):
            if not isinstance(row, dict) or set(row) != {"text", "decision", "assertion_ids"}:
                raise ValueError("invalid text-review record")
            if row["text"] != text:
                raise ValueError("text-review units must preserve exact source text")
            decision, ids = row["decision"], row["assertion_ids"]
            if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
                raise ValueError("assertion_ids must be a list of IDs")
            if len(ids) != len(set(ids)) or any(i not in assertions for i in ids):
                raise ValueError("unknown or duplicate text-review assertion ID")
            if decision is None and not complete and not ids:
                continue
            if decision not in {"extracted", "repeats", "not_checkable", "cut_off"}:
                raise ValueError("every text unit needs an explicit review decision")
            if decision == "cut_off" and (source, position) not in cut_off:
                raise ValueError("cut_off is only for the end of a text marked unfinished")
            if (decision in ("not_checkable", "cut_off")) != (not ids):
                raise ValueError("extracted/repeated facts need IDs; non-checkable text has none")
            if decision == "extracted" and not any(assertions[i]["source"] == source for i in ids):
                raise ValueError("extracted unit must reference an assertion from its source")
            referenced.update(ids)
    if complete and any(
        a["source"] != "claim" and aid not in referenced for aid, a in assertions.items()
    ):
        raise ValueError("every extracted assertion must link to a reviewed text unit")


def validate_annotation(
    case: ReviewCase,
    entry: dict,
    *,
    complete: bool,
    require_text_review: bool = False,
    cap_limit: int | None = None,
) -> None:
    """Refuse an annotation that breaks the extraction rule; ``complete`` requires judgements.

    Raises ValueError with the first problem found. It checks structure only and never
    decides whether a label is right. ``cap_limit`` requires a rule §11.9 ``cap_review``
    for that length limit.
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
    cap_record = entry.get("cap_review")
    if cap_limit is not None and (
        not isinstance(cap_record, dict) or cap_record.get("limit") != cap_limit
    ):
        raise ValueError(f"{where}: cap_review for the {cap_limit}-character limit is required")
    if "cap_review" in entry:
        _validate_cap_review(output, entry, complete)
    cut_only_claims = {
        u["unit"]
        for u in entry.get("cap_review", {}).get("units", [])
        if u["field"] == "claim"
        and u["unfinished"] is True
        and u["cut_off_text"] == claims[u["unit"]].text
    }
    listed_claims = [a["assertion_id"] for a in assertions if a.get("source") == "claim"]
    if sorted(listed_claims) != sorted(set(claims) - cut_only_claims):
        raise ValueError(
            f"{where}: every Claim record is exactly one assertion, "
            "except a whole-text cut-off fragment, which has none"
        )
    for a in assertions:
        _check_assertion(a, claims, complete, where)
    if require_text_review and "text_review" not in entry:
        raise ValueError("prospective review requires text_review decisions")
    if "text_review" in entry:
        _validate_text_review(output, entry, complete)

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
    # Rule §11.9 counts by field; None when the annotation has no cap_review.
    cap_hits: dict[str, int] | None = None
    unfinished: dict[str, int] | None = None

    @property
    def raw_faithfulness(self) -> float | None:
        return self.raw_supported / self.raw_checkable if self.raw_checkable else None


def score_annotation(
    case: ReviewCase, entry: dict, *, cap_limit: int | None = None
) -> OutputScore | None:
    """Per-output metrics from one rater's complete annotation; None for a no-op.

    Completeness is scored as written (rule §11.9); cap counts are reported beside it.
    """
    validate_annotation(case, entry, complete=True, cap_limit=cap_limit)
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
    caps = entry.get("cap_review")
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
        cap_hits=None if caps is None else _by_field(caps["units"]),
        unfinished=None if caps is None else _by_field(u for u in caps["units"] if u["unfinished"]),
    )


def _by_field(units: Iterable[dict]) -> dict[str, int]:
    fields = [u["field"] for u in units]
    return {f: fields.count(f) for f in CAP_FIELDS}


def cap_report(scored: Iterable[tuple[str, OutputScore]]) -> dict:
    """Rule §11.9 report by system, beside (never replacing) the main measures.

    ``scored`` pairs each unblinded system name with an output's score; every score
    must carry a cap review. Returns cap-hit and unfinished counts by field, mean
    completeness for outputs with and without a cap hit, and the separate sensitivity
    check: faithfulness over complete assertions, retaining outputs with cut-off fragments.
    """
    by_system: dict[str, list[OutputScore]] = {}
    for system, score in scored:
        if score.cap_hits is None or score.unfinished is None:
            raise ValueError("every scored output needs a cap review")
        by_system.setdefault(system, []).append(score)

    def mean(values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else None

    def pooled(scores):
        n = sum(x.checkable for x in scores)
        return sum(x.supported for x in scores) / n if n else None

    report = {}
    for system, scores in sorted(by_system.items()):
        hit = [x for x in scores if sum(x.cap_hits.values())]
        no_hit = [x for x in scores if not sum(x.cap_hits.values())]
        report[system] = {
            "outputs": len(scores),
            "outputs_with_cap_hit": len(hit),
            "cap_hits": {f: sum(x.cap_hits[f] for x in scores) for f in CAP_FIELDS},
            "unfinished": {f: sum(x.unfinished[f] for x in scores) for f in CAP_FIELDS},
            "completeness_with_cap_hit": mean(x.completeness for x in hit),
            "completeness_without_cap_hit": mean(x.completeness for x in no_hit),
            "sensitivity": {
                "faithfulness_all": pooled(scores),
                "faithfulness_excluding_cut_off_fragments": pooled(scores),
                "outputs_retained": len(scores),
                "complete_assertions": sum(x.checkable for x in scores),
                "cut_off_fragments_excluded": sum(sum(x.unfinished.values()) for x in scores),
            },
        }
    return report


DEVELOPMENT_HEADER = (
    "# E04 development cases: rater packet",
    "",
    f"Rubric `{RUBRIC_VERSION}`. Synthetic pilot cases written for rubric development; "
    "they are not model outputs. Rate each output independently using "
    "[EXTRACTION_RULE.md](EXTRACTION_RULE.md) and `annotation_template.json`, before "
    "discussing with the other rater or opening the case generator script.",
)


def render_packet(cases: tuple[ReviewCase, ...], header: Iterable[str] = DEVELOPMENT_HEADER) -> str:
    """Markdown packet for raters: decision facts and both outputs, no system or answers.

    A study case shows each output under the visible state its own system faced.
    """
    lines = [*header, ""]
    for case in cases:
        lines += [f"## {case.case_id}", ""]
        if case.states is None:
            lines += _facts(case.state, case.snapshot) + [""]
            for key in OUTPUT_KEYS:
                lines += [f"### Output {key}", ""] + _output(case.outputs[key]) + [""]
        else:
            for key in OUTPUT_KEYS:
                lines += [f"### Output {key}", "", f"State seen by output {key}:", ""]
                lines += _facts(case.states[key], case.snapshot) + [""]
                lines += _output(case.outputs[key]) + [""]
    return "\n".join(lines).rstrip() + "\n"


def _facts(st: s.VisibleState, snap: s.ConstraintSnapshot) -> list[str]:
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
