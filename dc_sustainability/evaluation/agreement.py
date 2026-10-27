"""E05 comparison of two independent original ratings, and the adjudication record.

Follows the agreed Q10/E05 steps (#22, #42): both originals stay unchanged and are
identified by their SHA256; assertions are matched; extraction agreement is reported
separately from label agreement on the assertions both raters found (percent agreement
and Cohen's kappa, undefined when it cannot be computed); every disagreement goes into a
separate adjudication record that the raters fill in jointly. Nothing here decides a
label: the adjudication record starts empty.

Claim assertions share their F02 claim IDs, so they match automatically. Summary and
limitation assertions are numbered by each rater, so a match between them is a human
judgement supplied as explicit ID pairs; without one they are reported as found by one
rater only.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from dc_sustainability.evaluation import review

Key = tuple[str, str]  # (case ID, output key)


@dataclass(frozen=True)
class Original:
    rater: str
    sha256: str
    entries: Mapping[Key, dict]


def load_original(raw: bytes, cases: Iterable[review.ReviewCase]) -> Original:
    """Parse one original ratings file and refuse anything incomplete or inconsistent.

    The SHA256 is taken over LF line endings, which is how the originals are committed:
    a Windows checkout with CRLF conversion then gives the same, published hash.
    """
    raw = raw.replace(b"\r\n", b"\n")
    data = json.loads(raw.decode("utf-8"))
    if data.get("rubric_version") != review.RUBRIC_VERSION:
        raise ValueError("ratings are for another rubric version")
    if not isinstance(data.get("rater"), str) or not data["rater"].strip():
        raise ValueError("ratings must name their rater")
    by_id = {c.case_id: c for c in cases}
    entries: dict[Key, dict] = {}
    for entry in data["outputs"]:
        key = (entry["case_id"], entry["output"])
        if key in entries or entry["case_id"] not in by_id:
            raise ValueError(f"unexpected or repeated output {key}")
        review.validate_annotation(by_id[entry["case_id"]], entry, complete=True)
        entries[key] = entry
    expected = {(c, k) for c in by_id for k in review.OUTPUT_KEYS}
    if set(entries) != expected:
        raise ValueError(f"missing outputs {sorted(expected - set(entries))}")
    return Original(data["rater"], hashlib.sha256(raw).hexdigest(), entries)


def cohens_kappa(pairs: Iterable[tuple[object, object]]) -> float | None:
    """Cohen's kappa for two raters; None when there are no pairs or chance agreement is 1."""
    pairs = list(pairs)
    n = len(pairs)
    if not n:
        return None
    observed = sum(a == b for a, b in pairs) / n
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(first[k] * second[k] for k in first) / (n * n)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


@dataclass(frozen=True)
class Agreement:
    n: int
    agreed: int
    kappa: float | None

    @property
    def percent(self) -> float | None:
        return 100 * self.agreed / self.n if self.n else None


def _agreement(pairs: list[tuple[object, object]]) -> Agreement:
    return Agreement(len(pairs), sum(a == b for a, b in pairs), cohens_kappa(pairs))


@dataclass(frozen=True)
class Matched:
    key: Key
    a_id: str
    b_id: str
    source: str  # "claim" or "extracted"
    a_label: str
    b_label: str


@dataclass(frozen=True)
class OneSided:
    key: Key
    rater: str  # "a" or "b"
    assertion: dict


@dataclass(frozen=True)
class Extraction:
    """Summary/limitation assertions; claims are given to both raters, so not counted."""

    both: int
    only_a: int
    only_b: int

    @property
    def agreement(self) -> float | None:
        total = self.both + self.only_a + self.only_b
        return self.both / total if total else None


@dataclass(frozen=True)
class Comparison:
    a: Original
    b: Original
    not_applicable: int  # output units both mark as empty-queue no-ops
    matched: tuple[Matched, ...]
    one_sided: tuple[OneSided, ...]
    extraction: Extraction
    labels: Agreement  # every matched assertion
    claim_labels: Agreement  # matched claim records only, reported separately
    completeness: Mapping[str, Agreement] = field(default_factory=dict)
    completeness_pairs: Mapping[Key, Mapping[str, tuple[int, int]]] = field(default_factory=dict)


def compare(
    a: Original, b: Original, matches: Mapping[Key, Iterable[tuple[str, str]]] | None = None
) -> Comparison:
    """Match assertions and measure agreement between originals ``a`` and ``b``.

    ``matches`` maps an output to (a ID, b ID) pairs for summary/limitation assertions
    the raters agree describe the same fact; each ID may be used once.
    """
    if set(a.entries) != set(b.entries):
        raise ValueError("the originals cover different outputs")
    matches = {k: list(v) for k, v in (matches or {}).items()}
    if set(matches) - set(a.entries):
        raise ValueError("matches name an unknown output")
    matched, one_sided, not_applicable = [], [], 0
    completeness_pairs: dict[Key, dict[str, tuple[int, int]]] = {}
    for key in sorted(a.entries):
        ea, eb = a.entries[key], b.entries[key]
        if ea["not_applicable"]:
            not_applicable += 1
            continue
        completeness_pairs[key] = {
            part: (ea["completeness"][part], eb["completeness"][part])
            for part in review.COMPLETENESS
        }
        xa = {x["assertion_id"]: x for x in ea["assertions"]}
        xb = {x["assertion_id"]: x for x in eb["assertions"]}
        pairs = [(i, i) for i in xa if xa[i]["source"] == "claim"]
        extracted = matches.get(key, [])
        used_a, used_b = [i for i, _ in extracted], [j for _, j in extracted]
        if len(set(used_a)) != len(used_a) or len(set(used_b)) != len(used_b):
            raise ValueError(f"{key}: an assertion is matched more than once")
        for i, j in extracted:
            if xa.get(i, {}).get("source", "claim") == "claim" or (
                xb.get(j, {}).get("source", "claim") == "claim"
            ):
                raise ValueError(f"{key}: matches pair summary/limitation IDs that exist")
        for i, j in pairs + extracted:
            source = "claim" if xa[i]["source"] == "claim" else "extracted"
            matched.append(Matched(key, i, j, source, xa[i]["label"], xb[j]["label"]))
        one_sided += [OneSided(key, "a", xa[i]) for i in xa if i not in dict(pairs + extracted)]
        taken_b = {j for _, j in pairs + extracted}
        one_sided += [OneSided(key, "b", xb[j]) for j in xb if j not in taken_b]

    return Comparison(
        a=a,
        b=b,
        not_applicable=not_applicable,
        matched=tuple(matched),
        one_sided=tuple(one_sided),
        extraction=Extraction(
            both=sum(m.source == "extracted" for m in matched),
            only_a=sum(o.rater == "a" for o in one_sided),
            only_b=sum(o.rater == "b" for o in one_sided),
        ),
        labels=_agreement([(m.a_label, m.b_label) for m in matched]),
        claim_labels=_agreement([(m.a_label, m.b_label) for m in matched if m.source == "claim"]),
        completeness={
            part: _agreement([p[part] for p in completeness_pairs.values()])
            for part in review.COMPLETENESS
        },
        completeness_pairs=completeness_pairs,
    )


def summary(comparison: Comparison) -> dict:
    """JSON-ready agreement report; percentages and kappa stay None when undefined."""

    def agreement(x: Agreement) -> dict:
        return {"n": x.n, "agreed": x.agreed, "percent": x.percent, "kappa": x.kappa}

    e = comparison.extraction
    return {
        "rubric_version": review.RUBRIC_VERSION,
        "originals": {
            "a": {"rater": comparison.a.rater, "sha256": comparison.a.sha256},
            "b": {"rater": comparison.b.rater, "sha256": comparison.b.sha256},
        },
        "not_applicable_outputs": comparison.not_applicable,
        "extraction": {
            "both": e.both,
            "only_a": e.only_a,
            "only_b": e.only_b,
            "agreement": e.agreement,
        },
        "labels_all_matched": agreement(comparison.labels),
        "labels_claims_only": agreement(comparison.claim_labels),
        "completeness": {k: agreement(v) for k, v in comparison.completeness.items()},
    }


# ----------------------------------------------------------------- adjudication
def adjudication_record(comparison: Comparison) -> dict:
    """An empty joint record of every disagreement; the originals are never edited."""
    items = []
    for m in comparison.matched:
        if m.a_label != m.b_label:
            items.append(
                {
                    "kind": "label",
                    "case_id": m.key[0],
                    "output": m.key[1],
                    "a_id": m.a_id,
                    "b_id": m.b_id,
                    "a": m.a_label,
                    "b": m.b_label,
                    "decision": None,
                    "rationale": "",
                }
            )
    for o in comparison.one_sided:
        items.append(
            {
                "kind": "extraction",
                "case_id": o.key[0],
                "output": o.key[1],
                "found_by": o.rater,
                "assertion_id": o.assertion["assertion_id"],
                "text": o.assertion["text"],
                "label": o.assertion["label"],
                "decision": None,  # "keep" (with label) or "drop"
                "decided_label": None,
                "rationale": "",
            }
        )
    for key, parts in comparison.completeness_pairs.items():
        for part, (x, y) in parts.items():
            if x != y:
                items.append(
                    {
                        "kind": "completeness",
                        "case_id": key[0],
                        "output": key[1],
                        "part": part,
                        "a": x,
                        "b": y,
                        "decision": None,
                        "rationale": "",
                    }
                )
    return {
        "rubric_version": review.RUBRIC_VERSION,
        "originals": summary(comparison)["originals"],
        "adjudicators": [],
        "items": items,
    }


def validate_adjudication(record: dict, comparison: Comparison) -> None:
    """Check a filled adjudication: same originals and items, every item decided jointly."""
    expected = adjudication_record(comparison)
    if record.get("originals") != expected["originals"]:
        raise ValueError("the adjudication is bound to different originals")
    adjudicators = record.get("adjudicators", [])
    if len(set(adjudicators)) < 2:
        raise ValueError("a joint adjudication names at least two adjudicators")
    fixed = ("decision", "decided_label", "rationale")
    strip = [{k: v for k, v in item.items() if k not in fixed} for item in record["items"]]
    if strip != [{k: v for k, v in i.items() if k not in fixed} for i in expected["items"]]:
        raise ValueError("adjudication items differ from the disagreements")
    for item in record["items"]:
        decision, where = item.get("decision"), (item["case_id"], item["output"], item["kind"])
        if not isinstance(item.get("rationale"), str) or not item["rationale"].strip():
            raise ValueError(f"{where}: every decision needs a rationale")
        if item["kind"] == "label" and decision not in review.LABELS:
            raise ValueError(f"{where}: decision must be a label")
        if item["kind"] == "completeness" and decision not in (0, 1):
            raise ValueError(f"{where}: decision must be 0 or 1")
        if item["kind"] == "extraction":
            if decision == "drop" and item.get("decided_label") is None:
                continue
            if decision != "keep" or item.get("decided_label") not in review.LABELS:
                raise ValueError(f"{where}: decide keep with a label, or drop")
