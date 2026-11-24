"""RULE-07: build the two-scenario demo page from retained evidence (#246).

Reads only files already published on main: the authored native-continuation archive
(read in place, every member checked against its SHA-256 manifest), the retained
verification reports and baseline, the rule table in the specification, the
professor-feedback disposition table and, optionally, a metrics record. It runs no
policy, checker, simulator, verifier or model, and imports none of them.

Lives in scripts/ on purpose: a new module under dc_sustainability/ would change the
frozen scientific package that the verification baseline is bound to.

Every panel carries one provenance badge:
EXPECTED (specification text), OBSERVED (saved trace, with its producer pin),
INDEPENDENTLY CHECKED (receiving report) or PENDING (not available yet).
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import tarfile
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "archive": ROOT / "docs/evidence/rule03-nov23-native/authored-artifacts.tar.gz",
    "sums": ROOT / "docs/evidence/rule03-nov23-native/AUTHORED_SHA256SUMS.txt",
    "continuation": ROOT / "docs/evidence/rule03-nov23-native/continuation-report.json",
    "primary": ROOT / "docs/evidence/rule03-nov22/receiving-report.json",
    "baseline": ROOT / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json",
    "spec_md": ROOT / "docs/rule_study/RULE01_SPECIFICATION.md",
    "spec_json": ROOT / "docs/rule_study/specification.json",
    "feedback": ROOT / "docs/report/VERIFIED_EVIDENCE_WORKING_DRAFT.md",
    "workflow": ROOT / "docs/report/RULE05_WORKFLOW_DIAGRAMS.md",
}
DEFAULT_METRICS = ROOT / "docs/evidence/rule04-dev-nov23/authored-metrics-reviewed.json"
WORKFLOW_FIGURE = "## Figure 2."
CASES = ("A", "B", "B-fault", "B-progress")
POLICIES = ("rules-v1", "greedy_a", "greedy_b")
PROPERTIES = ("S1", "S2", "S3", "S4", "S5", "P1", "P2")
FEEDBACK_ITEMS = (
    "Grouped ten-fold C/D cross-validation",
    "Explicit violation arithmetic / repair deltas",
    "ML warm-start / expert ranking",
    "Turnaround versus impact",
)
SHOWN_SLOTS = 6  # every authored job finishes by slot 3; slots 6-29 are drain only
MAX_MEMBER_BYTES = 2 * 1024 * 1024
BADGES = {
    "EXPECTED": "Expected (specification, not a result)",
    "OBSERVED": "Observed (saved trace)",
    "CHECKED": "Independently checked",
    "PENDING": "Pending",
}
CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --- Loading -------------------------------------------------------------------------------


def _read_sums(path: Path) -> dict[str, str]:
    sums = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            name = name.strip()
            if name in sums or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("duplicate or malformed checksum entry")
            sums[name] = digest
    return sums


def load_authored(archive: Path, sums_path: Path) -> dict[tuple[str, str], dict]:
    """Read case/result/decision JSON for each authored run, verifying every member read."""
    sums = _read_sums(sums_path)
    runs: dict[tuple[str, str], dict] = {}
    seen = set()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            parts = member.name.split("/")
            if len(parts) < 4 or parts[0] != "authored":
                continue
            policy, run_dir, leaf = parts[1], parts[2], "/".join(parts[3:])
            if leaf not in ("case.json", "result.json") and not re.fullmatch(
                r"decisions/decision-\d\d\.json", leaf
            ):
                continue
            if member.name in seen:
                raise ValueError(f"{member.name}: duplicate archive member")
            seen.add(member.name)
            if not member.isfile() or member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"{member.name}: not a bounded regular file")
            data = tar.extractfile(member).read()
            expected = sums.get(member.name)
            if expected is None or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"{member.name}: missing from or different to the manifest")
            if not run_dir.endswith("-" + policy):
                raise ValueError(f"{member.name}: run folder does not name its policy")
            case_id = run_dir[: -len(policy) - 1]
            run = runs.setdefault((case_id, policy), {"decisions": {}})
            record = json.load(io.BytesIO(data))
            if leaf.startswith("decisions/"):
                if record["decision_index"] != int(leaf[-7:-5]):
                    raise ValueError(f"{member.name}: decision index differs from filename")
                run["decisions"][record["decision_index"]] = record
            else:
                run[leaf.removesuffix(".json")] = record
    for key, run in runs.items():
        if "case" not in run or "result" not in run or 0 not in run["decisions"]:
            raise ValueError(f"{key}: incomplete run in archive")
        if run["result"]["policy_id"] != key[1] or run["result"]["case_id"] != key[0]:
            raise ValueError(f"{key}: result identity differs from its folder")
        if run["case"]["case_id"] != key[0] or set(run["decisions"]) != set(range(30)):
            raise ValueError(f"{key}: incomplete or mismatched 30-decision trace")
        if run["result"]["status"] != "complete":
            raise ValueError(f"{key}: incomplete result")
        for index, record in run["decisions"].items():
            if (record["case_id"], record["policy_id"]) != key:
                raise ValueError(f"{key}: decision identity differs from its folder")
            digest = sums[f"authored/{key[1]}/{key[0]}-{key[1]}/decisions/decision-{index:02}.json"]
            if run["result"]["decision_sha256s"][index] != digest:
                raise ValueError(f"{key}: result decision commitment differs")
    expected_runs = {(c, p) for c in CASES for p in POLICIES if c != "B-fault" or p == "rules-v1"}
    if set(runs) != expected_runs:
        raise ValueError("incomplete or unexpected authored case-policy coverage")
    return runs


def rule_table(spec_md: Path) -> list[tuple[str, str, str]]:
    rows = []
    for line in Path(spec_md).read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"\| (R0\d) \| (.+?) \| (.+?) \|", line.strip())
        if match:
            rows.append(match.groups())
    if [r[0] for r in rows] != [f"R0{i}" for i in range(1, 10)]:
        raise ValueError("specification rule table R01-R09 not found")
    return rows


def feedback_table(path: Path) -> list[tuple[str, str]]:
    found = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0] in FEEDBACK_ITEMS:
            found[cells[0]] = cells[1]
    if set(found) != set(FEEDBACK_ITEMS):
        raise ValueError("professor-feedback disposition table incomplete")
    return [(item, found[item]) for item in FEEDBACK_ITEMS]


NODE = re.compile(r'^\s*([A-Za-z]\w*)\s*[\[{(]+"(.+?)"[\]})]+\s*$')


def workflow_figure(path: Path) -> dict:
    """Reimo's RULE-05 Figure 2: its node labels, edges and caption, read from the Mermaid source."""
    text = Path(path).read_text(encoding="utf-8")
    start = text.find(WORKFLOW_FIGURE)
    if start < 0:
        raise ValueError("workflow Figure 2 not found")
    section = text[start:]
    title = section.splitlines()[0].lstrip("# ").strip()
    block = re.search(r"```mermaid\n(.*?)```", section, re.S)
    caption = re.search(r"\nCaption:(.*?)(?:\n\n|\Z)", section, re.S)
    if not block or not caption:
        raise ValueError("workflow Figure 2 is missing its Mermaid source or caption")
    nodes, edges = {}, []
    for line in block.group(1).splitlines():
        if (node := NODE.match(line)) and "-->" not in line:
            nodes[node.group(1)] = re.sub(r"<br\s*/?>", " — ", node.group(2))
        for chain in re.split(r"\s*;\s*", line):
            hops = re.split(r"\s*(-\.?->(?:\|[^|]*\|)?)\s*", chain.strip())
            for i in range(0, len(hops) - 2, 2):
                arrow = hops[i + 1]
                label = re.search(r"\|\"?(.*?)\"?\|", arrow)
                edges.append((hops[i], hops[i + 2], label.group(1) if label else ""))
    edges = [(a, b, c) for a, b, c in edges if a in nodes and b in nodes]
    if not nodes or not edges:
        raise ValueError("workflow Figure 2 has no readable nodes/edges")
    return {
        "title": title,
        "nodes": nodes,
        "edges": edges,
        "caption": " ".join(caption.group(1).split()),
    }


def load_inputs(paths: Mapping[str, Path], metrics: Path | None = None) -> dict:
    paths = {**DEFAULTS, **{k: Path(v) for k, v in paths.items()}}
    spec = json.loads(paths["spec_json"].read_text(encoding="utf-8"))
    inputs = {
        "runs": load_authored(paths["archive"], paths["sums"]),
        "continuation": json.loads(paths["continuation"].read_text(encoding="utf-8")),
        "primary": json.loads(paths["primary"].read_text(encoding="utf-8")),
        "baseline": json.loads(paths["baseline"].read_text(encoding="utf-8")),
        "rules": rule_table(paths["spec_md"]),
        "scenarios": {s["id"]: s for s in spec["scenarios"]},
        "feedback": feedback_table(paths["feedback"]),
        "workflow": workflow_figure(paths["workflow"]),
        "metrics": None,
        "provenance": [],
    }
    used = list(DEFAULTS)
    if metrics is not None:
        metrics = Path(metrics)
        receipt = metrics.parent / "manager-review-receipt.json"
        checksums = metrics.parent / "REVIEWED_SHA256SUMS.txt"
        sums = _read_sums(checksums)
        for artifact in (metrics, receipt):
            if sha256_file(artifact) != sums.get(artifact.name):
                raise ValueError("metrics or review receipt checksum mismatch")
        reviewed = json.loads(receipt.read_text(encoding="utf-8"))
        if (
            reviewed["reviewed_metrics_sha256"] != sha256_file(metrics)
            or reviewed["authored_input_archive_sha256"] != sha256_file(paths["archive"])
            or reviewed["authored_producer_commit"]
            != inputs["baseline"]["new_authored_producer_commit"]
        ):
            raise ValueError("metrics receipt does not bind these authored inputs")
        inputs["metrics"] = json.loads(metrics.read_text(encoding="utf-8"))
        paths["metrics"] = metrics
        used.append("metrics")
        paths["metrics_review_receipt"] = receipt
        paths["metrics_checksums"] = checksums
        used.extend(("metrics_review_receipt", "metrics_checksums"))
    for key in used:
        path = paths[key]
        try:
            shown = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            shown = path.name
        inputs["provenance"].append((key, shown, sha256_file(path)))
    return inputs


# --- Rendering -----------------------------------------------------------------------------

e = html.escape
JOB_COLOURS = {"J1": "#3b82c4", "J2": "#d9822b", "J3": "#4a9d5b", "J4": "#9b59b6"}


def badge(kind: str, detail: str = "") -> str:
    text = BADGES[kind] + (f": {detail}" if detail else "")
    return f'<span class="badge {kind.lower()}">{e(text)}</span>'


def timeline_svg(run: Mapping) -> str:
    """Per-slot load (background + executed jobs) against capacity, with the score row."""
    case, accounting = run["case"], run["result"]["accounting"]
    cap, bg = case["capacity_kw"], case["background_kw"]
    scale, width, top = 2.0, 72, 16
    height = top + int(70 * scale) + 46
    parts = [
        f'<svg viewBox="0 0 {SHOWN_SLOTS * width + 60} {height}" role="img" '
        f'aria-label="{e(case["case_id"])} {e(run["result"]["policy_id"])} slot load">'
    ]
    base_y = top + int(70 * scale)
    for slot in range(SHOWN_SLOTS):
        x = 50 + slot * width
        y = base_y - bg * scale
        parts.append(
            f'<rect x="{x}" y="{y}" width="{width - 12}" height="{bg * scale}" class="bg"/>'
        )
        for job in accounting["per_job"]:
            if job["start_slot"] <= slot < job["end_slot"]:
                h = job["power_kw"] * scale
                y -= h
                colour = JOB_COLOURS.get(job["job_id"], "#777")
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{width - 12}" height="{h}" fill="{colour}"/>'
                    f'<text x="{x + 6}" y="{y + 14}" class="lbl">{e(job["job_id"])}</text>'
                )
        parts.append(
            f'<text x="{x + 4}" y="{base_y + 16}" class="axis">slot {slot}</text>'
            f'<text x="{x + 4}" y="{base_y + 32}" class="score">score {case["scores"][slot]}</text>'
        )
    cap_y = base_y - cap * scale
    parts.append(
        f'<line x1="44" x2="{50 + SHOWN_SLOTS * width}" y1="{cap_y}" y2="{cap_y}" class="cap"/>'
        f'<text x="2" y="{cap_y + 4}" class="axis">{cap} kW</text>'
        f'<text x="2" y="{base_y}" class="axis">0</text></svg>'
    )
    return "".join(parts)


def _stage_rows(decision: Mapping) -> str:
    rows = []
    for stage in decision["proposal_stages"]:
        plan = stage.get("plan") or {}
        starts = ", ".join(f"{s['job_id']}@{s['start_slot']}" for s in plan.get("starts", []))
        check = stage["check_result"]["status"]
        why = "; ".join(v["message"] for v in stage["check_result"].get("violations", []))
        r04 = [
            a
            for a in stage.get("arithmetic", [])
            if a["rule_id"] == "R04" and a.get("slot") == 0 and a["outcome"] == "fail"
        ]
        arithmetic = ""
        for a in r04:
            terms = " + ".join(f"{t['value']}" for t in a["terms"])
            arithmetic = f"slot 0: {terms} kW &gt; {a['limit']} kW (excess {a['signed_excess']})"
        rows.append(
            f"<tr><td>{e(stage['origin'])}</td><td>{e(starts or '—')}</td>"
            f"<td>{e(check)}</td><td>{arithmetic or e(why or '—')}</td></tr>"
        )
    return "".join(rows)


def run_panel(run: Mapping, pin: str) -> str:
    result, first = run["result"], run["decisions"][0]
    executed = first["execution"]["current_starts"]
    codes = ", ".join(sorted({err["code"] for err in first.get("errors", [])})) or "none"
    return (
        f'<div class="run"><h4>{e(result["policy_id"])} '
        f"{badge('OBSERVED', 'producer ' + pin[:8])}</h4>"
        f"{timeline_svg(run)}"
        f"<p>Completed: {e(', '.join(result['completed_job_ids']) or 'none')} · "
        f"Missed: {e(', '.join(result['missed_job_ids']) or 'none')} · "
        f"Artificial impact: {result['accounting']['synthetic_impact_total']} score-kWh</p>"
        f"<details><summary>Slot-0 decision: proposal stages and production check</summary>"
        f"<table><tr><th>Stage origin</th><th>Proposed starts</th><th>Check</th>"
        f"<th>Recorded reason / R04 arithmetic</th></tr>{_stage_rows(first)}</table>"
        f"<p>Executed at slot 0: {e(', '.join(executed) or 'no starts')} "
        f"({e(first['execution']['status'])}); errors: {e(codes)}</p></details></div>"
    )


CASE_NOTES = {
    "A": "Timing preference, not a capacity failure: both jobs plus background fit 60 kW. "
    "The delayed lower-score start is an observed authored example, not a measured advantage.",
    "B": "Jointly infeasible: both rigid jobs need 20 + 30 + 30 = 80 kW against 60 kW, though each "
    "fits alone. The proposed one-job plan (50 kW) is not a capacity violation; the unchanged "
    "abstention gate refuses it because the other job's abstention has no individual physical "
    "justification. It refuses rules-v1's proposal and its checked Greedy A fallback, and Greedy "
    "A's and Greedy B's own proposals, so no job starts under any policy and both end missed. "
    "This is safe refusal with no partial progress, not a P1 success.",
    "B-fault": "Deliberate fault injection: a both-jobs slot-0 proposal is injected to show the "
    "independent arithmetic rejection. It is not a natural rules-v1 output.",
    "B-progress": "Separate feasible subcase: J2 is flexible with deadline 2, so the two jobs "
    "complete one after the other.",
}


def case_panel(case_id: str, inputs: Mapping, pin: str) -> str:
    base = "B" if case_id in ("B-fault", "B-progress") else case_id
    scenario = inputs["scenarios"][base]
    if case_id == "B-fault":
        expected = json.dumps(scenario["fault_injection_not_natural_output"], sort_keys=True)
    elif case_id == "B-progress":
        expected = json.dumps(scenario["feasible_progress_subcase"], sort_keys=True)
    else:
        expected = scenario["expected_not_measured"]
    runs = [inputs["runs"][(case_id, p)] for p in POLICIES if (case_id, p) in inputs["runs"]]
    return (
        f'<section id="case-{e(case_id)}"><h2>Case {e(case_id)}</h2>'
        f"<p>{e(CASE_NOTES[case_id])}</p>"
        f"<p>{badge('EXPECTED')} {e(expected)}</p>"
        + "".join(run_panel(r, pin) for r in runs)
        + "</section>"
    )


def _status_cells(statuses: Mapping) -> str:
    return "".join(
        f'<td class="st {e(statuses.get(p, "—").lower())}">{e(statuses.get(p, "—"))}</td>'
        for p in PROPERTIES
    )


def verification_panel(inputs: Mapping) -> str:
    cont, prim, base = inputs["continuation"], inputs["primary"], inputs["baseline"]
    rows = []
    for policy, statuses in prim["domains"]["primary"]["property_statuses"].items():
        rows.append(("Primary 64 (Nov 22 attempt)", policy, statuses))
    for policy, statuses in cont["phases"]["saved_greedy_b"]["property_statuses"].items():
        rows.append(("Primary: 51 saved Greedy B replays (Nov 23)", policy, statuses))
    authored = cont["phases"]["authored"]["domains"]["authored"]
    for policy, statuses in authored["property_statuses"].items():
        rows.append(("Authored A/B/B-fault/B-progress (Nov 23)", policy, statuses))
    body = "".join(f"<tr><td>{e(d)}</td><td>{e(p)}</td>{_status_cells(s)}</tr>" for d, p, s in rows)
    head = "".join(f"<th>{p}</th>" for p in PROPERTIES)
    return (
        '<section id="verification"><h2>Independent verification</h2>'
        f"<p>{badge('CHECKED', 'Nisha receiving, comment ' + str(base['receiving_source_comment_id']))}</p>"
        f"<p>Baseline: {e(base['status'])}. Traces: {base['domains']['case_policy_traces']} "
        f"case-policy traces across {base['domains']['primary']} primary and "
        f"{base['domains']['authored']} authored cases. The Nov 22 attempt stays "
        f"{e(prim['overall'])} as history; the Nov 23 continuation is {e(cont['overall'])} within "
        "its scope. S4 (no unverified invalid execution) is NOT_RUN in the primary domain, which "
        "has no invalid proposals; it is exercised only by the authored rules-v1 B-fault case. "
        "Greedy A/B have no rule arithmetic and no fault injection.</p>"
        f"<table><tr><th>Domain</th><th>Policy</th>{head}</tr>{body}</table>"
        "<p>In all 12 jointly infeasible primary cases every policy starts no jobs: safe refusal "
        "does not salvage a feasible subset. Not an evaluation freeze or generalization result.</p>"
        "</section>"
    )


def metrics_panel(inputs: Mapping) -> str:
    metrics = inputs["metrics"]
    if metrics is None:
        return (
            '<section id="metrics"><h2>Metrics</h2>'
            f"<p>{badge('PENDING', 'no metrics record supplied')}</p></section>"
        )
    rows = "".join(
        f"<tr><td>{e(r['case_id'])}</td><td>{e(r['policy_id'])}</td><td>{r['completed']}</td>"
        f"<td>{r['missed']}</td><td>{r['execution_violations']}</td>"
        f"<td>{r['synthetic_impact']['producer_total']}</td></tr>"
        for r in metrics["runs"]
    )
    comparisons = "".join(
        f"<tr><td>{e(c['case_id'])}</td><td>{e(c['policy_id'])}</td><td>"
        + (
            f"{c['policy_total']:g} vs {c['greedy_a_total']:g} ({c['reduction']:.3f})"
            if c.get("available")
            else "unavailable: " + e(c["reason"])
        )
        + "</td></tr>"
        for c in metrics["equal_work_vs_greedy_a"]
    )
    return (
        '<section id="metrics"><h2>Metrics on the authored runs</h2>'
        f"<p>{badge('OBSERVED', metrics['label'])} {badge('PENDING', 'independent metric receiving')}</p>"
        "<p>Artificial score-kWh (power × 1 h × PUE 1.0 × score weight): not g/kWh, not emissions. "
        "Four authored cases are illustrations, not unseen-case performance.</p>"
        "<table><tr><th>Case</th><th>Policy</th><th>Completed</th><th>Missed</th>"
        f"<th>Execution violations</th><th>Impact</th></tr>{rows}</table>"
        "<h3>Equal-work comparison against Greedy A</h3>"
        f"<table><tr><th>Case</th><th>Policy</th><th>Result</th></tr>{comparisons}</table>"
        "</section>"
    )


def workflow_panel(figure: Mapping) -> str:
    steps = "".join(f"<li><b>{e(k)}</b>: {e(v)}</li>" for k, v in figure["nodes"].items())
    edges = "".join(
        f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c or '—')}</td></tr>"
        for a, b, c in figure["edges"]
    )
    return (
        '<section id="workflow"><h2>Workflow</h2>'
        f"<p>{badge('EXPECTED', 'Reimo, RULE-05 ' + figure['title'] + '; design, not a result')}</p>"
        "<p>Editable diagram source in the repository: "
        "<code>docs/report/RULE05_WORKFLOW_DIAGRAMS.md</code>. Nodes and transitions below are read from its "
        "Mermaid source.</p>"
        f"<ol>{steps}</ol><table><tr><th>From</th><th>To</th><th>When</th></tr>{edges}</table>"
        f"<p><i>Caption:</i> {e(figure['caption'])}</p></section>"
    )


STYLE = """
:root{--fg:#1d2733;--muted:#5b6672;--line:#d6dbe1;--bg:#fff;--card:#f6f8fa}
@media (prefers-color-scheme:dark){:root{--fg:#e6e9ee;--muted:#a3adb8;--line:#3a434d;--bg:#14191f;--card:#1c232b}}
body{font:15px/1.5 system-ui,sans-serif;color:var(--fg);background:var(--bg);max-width:1040px;margin:0 auto;padding:16px}
h1{font-size:1.6em}h2{border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:1.8em}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:.92em}
td,th{border:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
td,code{overflow-wrap:anywhere}table{table-layout:fixed}
.run{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px 12px;margin:10px 0}
svg{width:100%;max-width:520px;height:auto}.bg{fill:#9aa4ae}.cap{stroke:#c0392b;stroke-dasharray:6 4}
.lbl{fill:#fff;font-size:11px}.axis,.score{fill:var(--muted);font-size:11px}
.badge{display:inline-block;border-radius:10px;padding:1px 8px;font-size:.8em;margin-right:4px}
.expected{background:#e8eefc;color:#203a7a}.observed{background:#e6f4ea;color:#1e5b31}
.checked{background:#f3e8fb;color:#5a2a7a}.pending{background:#fdf0dc;color:#7a4b10}
.st.pass{color:#1e7b3a}.st.not_run{color:var(--muted)}.st.incomplete,.st.fail{color:#b23b2a}
nav a{margin-right:10px}code{font-size:.9em}
"""


def render(inputs: Mapping) -> str:
    pin = inputs["baseline"]["new_authored_producer_commit"]
    rules = "".join(
        f"<tr><td>{e(r)}</td><td>{e(p)}</td><td>{e(x)}</td></tr>" for r, p, x in inputs["rules"]
    )
    feedback = "".join(f"<tr><td>{e(i)}</td><td>{e(s)}</td></tr>" for i, s in inputs["feedback"])
    provenance = "".join(
        f"<tr><td>{e(k)}</td><td><code>{e(p)}</code></td><td><code>{e(h)}</code></td></tr>"
        for k, p, h in inputs["provenance"]
    )
    nav = "".join(
        f'<a href="#{a}">{t}</a>'
        for a, t in [
            ("rules", "Rules"),
            ("workflow", "Workflow"),
            ("case-A", "A"),
            ("case-B", "B"),
            ("case-B-fault", "B-fault"),
            ("case-B-progress", "B-progress"),
            ("verification", "Verification"),
            ("metrics", "Metrics"),
            ("feedback", "Feedback"),
        ]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Rule Study Demo</title><style>{STYLE}</style></head><body>"
        "<h1>Rule-system study: two-scenario demo</h1>"
        "<p>Built offline from retained evidence on main. Nothing on this page was run to make "
        "it. Scores are artificial weights; nothing here is an emissions result. Finite bounded "
        "verification is not a universal proof or unseen generalization; historical Agent/Plain "
        "runs are not a matched comparison; missing-forecast cases are fallback/accounting "
        "controls, not a policy ranking. The original Agent-versus-Plain research question "
        "remains unanswered.</p>"
        f"<p>{' '.join(badge(k) for k in BADGES)}</p><nav>{nav}</nav>"
        f'<section id="rules"><h2>Rules R01–R09</h2><p>{badge("EXPECTED", "RULE01 specification")}</p>'
        f"<table><tr><th>Rule</th><th>Predicate/action</th><th>Explanation evidence</th></tr>{rules}"
        "</table></section>"
        + workflow_panel(inputs["workflow"])
        + "".join(case_panel(c, inputs, pin) for c in CASES)
        + verification_panel(inputs)
        + metrics_panel(inputs)
        + '<section id="feedback"><h2>Professor feedback (#231)</h2>'
        f"<p>{badge('EXPECTED', 'current disposition, working report')}</p>"
        f"<table><tr><th>Item</th><th>Status</th></tr>{feedback}</table></section>"
        '<section id="provenance"><h2>Inputs</h2>'
        f"<table><tr><th>Input</th><th>Path</th><th>SHA-256</th></tr>{provenance}</table>"
        f"<p>Authored traces: producer commit <code>{e(pin)}</code>.</p></section>"
        "</body></html>\n"
    )
