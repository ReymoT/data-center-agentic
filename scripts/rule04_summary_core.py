"""RULE-04: per-stratum tables and the matched turnaround-vs-impact plot (#242).

Reads one development rollout output directory written by prepare_rule_study_rollout.py:
each completed pair's ``pair-result.json`` (status PASS, with its frozen
rule_study_metrics_core record) plus the run's ``rollout-report.json`` or, for a stopped
run, ``rollout-failure.json``. Strata come from the retained development case set.

Descriptive only, per the RULE-04 freeze: no pooled ranking, no resampling, no new metric
arithmetic. Equal-work rows come from the frozen ``equal_work``; unavailable comparisons
keep their reason and are never shown as zero. Missing-forecast rows are a control, not a
policy ranking. A stopped run is reported as partial coverage, never as complete.
Runs nothing: no policy, checker, simulator, verifier or model.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Mapping, Sequence

from scripts import prepare_rule_study_rollout as rollout
from scripts import rule_study_metrics_core as mc

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "docs/evidence/rule04-dev-nov23/development.cases.json"
POLICIES = rollout.POLICIES
BASELINE = mc.BASELINE_POLICY
CONTROL = "missing_forecast"
RECORD_KIND = "rule04_summary_v1"
UNIT = "artificial score-kWh (not g/kWh, not emissions)"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_run(run_dir: Path, cases_path: Path = CASES) -> dict:
    """Completed pair metrics, the run's own status record and the case strata."""
    run_dir = Path(run_dir)
    report, failure = run_dir / "rollout-report.json", run_dir / "rollout-failure.json"
    if report.is_file() == failure.is_file():
        raise ValueError("expected exactly one of rollout-report.json or rollout-failure.json")
    status_path = report if report.is_file() else failure
    status = _json(status_path)
    case_set = _json(cases_path)
    strata = {c["case_id"]: c["stratum"] for c in case_set["cases"]}

    metrics, failed = [], []
    for pair in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        result, pair_failure = pair / "pair-result.json", pair / "pair-failure.json"
        if pair_failure.is_file():
            record = _json(pair_failure)
            failed.append(
                {
                    "case_id": record.get("case_id"),
                    "policy_id": record.get("policy_id"),
                    "exception": record.get("exception"),
                }
            )
            continue
        if not result.is_file():
            failed.append({"folder": pair.name, "exception": "no pair result"})
            continue
        record = _json(result)
        metric = record["metric"]
        if record.get("status") != "PASS" or metric.get("status") != "complete":
            raise ValueError(f"{pair.name}: pair result is not a complete PASS")
        if (record["case_id"], record["policy_id"]) != (metric["case_id"], metric["policy_id"]):
            raise ValueError(f"{pair.name}: pair identity differs from its metric")
        if metric["case_id"] not in strata or metric["policy_id"] not in POLICIES:
            raise ValueError(f"{pair.name}: unknown case or policy")
        metrics.append(metric)

    keys = [(m["case_id"], m["policy_id"]) for m in metrics]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate completed pair")
    if status.get("completed_runs", status.get("runs")) != len(metrics):
        raise ValueError("completed pair count differs from the run's own record")
    if status.get("coverage") is not None and status["coverage"] != rollout.coverage(
        metrics, strata
    ):
        raise ValueError("coverage differs from the run's own record")
    complete = report.is_file() and status.get("status") == "PASS"
    return {
        "metrics": sorted(metrics, key=lambda m: (m["case_id"], m["policy_id"])),
        "failed": failed,
        "strata": strata,
        "complete": complete,
        "run_status": status.get("status"),
        "stop_message": None if complete else status.get("message"),
        "inputs": [
            (status_path.name, _sha(status_path)),
            (Path(cases_path).name, _sha(cases_path)),
        ],
    }


def _mean(values):
    return round(mean(values), 4) if values else None


def policy_rows(metrics: Sequence[Mapping], strata: Mapping[str, str]) -> list[dict]:
    cover = rollout.coverage(metrics, strata)
    rows = []
    for stratum in sorted(cover):
        for policy in POLICIES:
            runs = [
                m for m in metrics if strata[m["case_id"]] == stratum and m["policy_id"] == policy
            ]
            turnaround = [v for m in runs for v in m["turnaround_slots"]["values"]]
            delay = [v for m in runs for v in m["start_delay_slots"]["values"]]
            rows.append(
                {
                    "stratum": stratum,
                    "policy_id": policy,
                    "role": "control_not_ranking"
                    if stratum == CONTROL
                    else "development_comparison",
                    "runs_completed": len(runs),
                    "runs_expected": cover[stratum]["expected_runs"] // len(POLICIES),
                    "execution_violations": sum(m["execution_violations"] for m in runs),
                    "executed_starts": sum(m["executed_starts"] for m in runs),
                    "checked_decisions": sum(m["checked_decisions"] for m in runs),
                    "jobs": sum(m["jobs"] for m in runs),
                    "completed": sum(m["completed"] for m in runs),
                    "missed": sum(m["missed"] for m in runs),
                    "unfinished": sum(m["unfinished"] for m in runs),
                    "turnaround_mean_slots": _mean(turnaround),
                    "turnaround_count": len(turnaround),
                    "start_delay_mean_slots": _mean(delay),
                    "start_delay_count": len(delay),
                    "runs_with_fallback_selected": sum(m["fallback"]["selected"] > 0 for m in runs),
                    "runs_with_blocked_decision": sum(
                        m["fallback"]["blocked_decisions"] > 0 for m in runs
                    ),
                    "job_impact_total": sum(m["synthetic_impact"]["producer_total"] for m in runs),
                }
            )
    return rows


def comparison_rows(metrics: Sequence[Mapping], strata: Mapping[str, str]) -> list[dict]:
    """Frozen equal-work rows, summarised per stratum and policy; reasons kept, never zero."""
    rows = rollout.comparison_rows(mc.equal_work(metrics), strata)
    by_run = {(m["case_id"], m["policy_id"]): m for m in metrics}
    out = []
    for stratum in sorted(set(strata.values())):
        for policy in POLICIES:
            if policy == BASELINE:
                continue
            group = [r for r in rows if r["stratum"] == stratum and r["policy_id"] == policy]
            available = [r for r in group if r.get("available")]
            reductions = [r["reduction"] for r in available]
            shift = []
            for r in available:
                x = by_run[(r["case_id"], policy)]["turnaround_slots"]["values"]
                a = by_run[(r["case_id"], BASELINE)]["turnaround_slots"]["values"]
                if x and a:
                    shift.append(mean(x) - mean(a))
            out.append(
                {
                    "stratum": stratum,
                    "policy_id": policy,
                    "role": "control_not_ranking"
                    if stratum == CONTROL
                    else "development_comparison",
                    "rows": len(group),
                    "available": len(available),
                    "unavailable_reasons": dict(
                        sorted(
                            Counter(r["reason"] for r in group if not r.get("available")).items()
                        )
                    ),
                    "reduction_median": round(median(reductions), 4) if reductions else None,
                    "reduction_min": round(min(reductions), 4) if reductions else None,
                    "reduction_max": round(max(reductions), 4) if reductions else None,
                    "turnaround_shift_mean_slots": _mean(shift),
                    "turnaround_shift_count": len(shift),
                }
            )
    return out


def summarize(run: Mapping) -> dict:
    return {
        "record_kind": RECORD_KIND,
        "coverage_status": "COMPLETE" if run["complete"] else "PARTIAL",
        "run_status": run["run_status"],
        "stop_message": run["stop_message"],
        "coverage": rollout.coverage(run["metrics"], run["strata"]),
        "failed_or_unfinished_pairs": run["failed"],
        "policy_rows": policy_rows(run["metrics"], run["strata"]),
        "comparison_rows": comparison_rows(run["metrics"], run["strata"]),
        "unit": UNIT,
        "inputs": run["inputs"],
        "notes": [
            "Development cases only; not unseen generalization or final-set evaluation.",
            "Per stratum; no pooled ranking. Missing-forecast rows are a control.",
            "Missed and unfinished counts overlap and are not summed.",
            "Unavailable comparisons keep their reason; none is shown as zero.",
            "Reductions are descriptive (median/min/max); no resampling interval.",
        ],
    }


def _cell(value):
    return "—" if value is None else str(value)


def tables_markdown(summary: Mapping) -> str:
    lines = [
        "# RULE-04 development comparison tables",
        "",
        f"Coverage: **{summary['coverage_status']}** (run status `{summary['run_status']}`).",
    ]
    if summary["stop_message"]:
        lines.append(f"Stop reason recorded by the run: {summary['stop_message']}")
    lines += ["", f"Impact unit: {summary['unit']}.", "", "## Per stratum and policy", ""]
    head = (
        "| Stratum | Policy | Runs | Violations / starts | Jobs | Completed | Missed | "
        "Unfinished | Turnaround mean (n) | Delay mean (n) | Fallback runs | Blocked runs | "
        "Job impact |"
    )
    lines += [head, "|" + "---|" * 13]
    for r in summary["policy_rows"]:
        label = f"{r['stratum']} (control)" if r["role"] == "control_not_ranking" else r["stratum"]
        lines.append(
            f"| {label} | {r['policy_id']} | {r['runs_completed']}/{r['runs_expected']} | "
            f"{r['execution_violations']} / {r['executed_starts']} | {r['jobs']} | {r['completed']} | "
            f"{r['missed']} | {r['unfinished']} | {_cell(r['turnaround_mean_slots'])} "
            f"({r['turnaround_count']}) | {_cell(r['start_delay_mean_slots'])} "
            f"({r['start_delay_count']}) | {r['runs_with_fallback_selected']} | "
            f"{r['runs_with_blocked_decision']} | {r['job_impact_total']} |"
        )
    lines += [
        "",
        "## Equal-work comparison against Greedy A",
        "",
        "| Stratum | Policy | Available / rows | Reduction median [min, max] | "
        "Turnaround shift mean (n) | Unavailable reasons |",
        "|---|---|---|---|---|---|",
    ]
    for r in summary["comparison_rows"]:
        label = f"{r['stratum']} (control)" if r["role"] == "control_not_ranking" else r["stratum"]
        reduction = (
            "unavailable"
            if r["reduction_median"] is None
            else f"{r['reduction_median']} [{r['reduction_min']}, {r['reduction_max']}]"
        )
        reasons = ", ".join(f"{k}: {v}" for k, v in r["unavailable_reasons"].items()) or "—"
        lines.append(
            f"| {label} | {r['policy_id']} | {r['available']}/{r['rows']} | {reduction} | "
            f"{_cell(r['turnaround_shift_mean_slots'])} ({r['turnaround_shift_count']}) | {reasons} |"
        )
    if summary["failed_or_unfinished_pairs"]:
        lines += ["", "## Failed or unfinished pairs", ""]
        lines += [
            f"- {json.dumps(p, sort_keys=True)}" for p in summary["failed_or_unfinished_pairs"]
        ]
    lines += ["", "## Notes", ""] + [f"- {n}" for n in summary["notes"]]
    lines += ["", "## Inputs", ""] + [f"- `{n}` sha256 `{h}`" for n, h in summary["inputs"]]
    return "\n".join(lines) + "\n"


def plot_svg(summary: Mapping) -> str:
    """Matched turnaround shift (x, slots) vs median equal-work reduction (y); controls excluded."""
    points = [
        r
        for r in summary["comparison_rows"]
        if r["role"] == "development_comparison"
        and r["reduction_median"] is not None
        and r["turnaround_shift_mean_slots"] is not None
    ]
    w, h, pad = 520, 340, 56
    xs = [p["turnaround_shift_mean_slots"] for p in points] + [0.0]
    ys = [p["reduction_median"] for p in points] + [0.0]
    x0, x1 = min(xs) - 0.5, max(xs) + 0.5
    y0, y1 = min(ys) - 0.1, max(ys) + 0.1

    def px(x):
        return pad + (x - x0) / (x1 - x0) * (w - 2 * pad)

    def py(y):
        return h - pad - (y - y0) / (y1 - y0) * (h - 2 * pad)

    e = html.escape
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" '
        f'font-size="11"><title>Turnaround shift vs equal-work reduction</title>',
        f'<rect width="{w}" height="{h}" fill="white"/>',
        f'<line x1="{pad}" y1="{py(0)}" x2="{w - pad}" y2="{py(0)}" stroke="#999"/>',
        f'<line x1="{px(0)}" y1="{pad}" x2="{px(0)}" y2="{h - pad}" stroke="#999"/>',
        f'<text x="{w / 2}" y="{h - 16}" text-anchor="middle">Mean turnaround shift vs Greedy A '
        "(slots, matched cases)</text>",
        f'<text x="14" y="{h / 2}" transform="rotate(-90 14 {h / 2})" text-anchor="middle">'
        "Median equal-work reduction (artificial score-kWh)</text>",
        f'<text x="{pad}" y="20">{e(summary["coverage_status"])} coverage; development cases only; '
        "missing-forecast control excluded</text>",
    ]
    for p in points:
        cx, cy = px(p["turnaround_shift_mean_slots"]), py(p["reduction_median"])
        label = f"{p['policy_id']} · {p['stratum']} (n={p['available']})"
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#3b6fb6"/>')
        parts.append(f'<text x="{cx + 8:.1f}" y="{cy - 6:.1f}">{e(label)}</text>')
    if not points:
        parts.append(
            f'<text x="{w / 2}" y="{h / 2}" text-anchor="middle">No available matched comparison'
            "</text>"
        )
    parts.append("</svg>")
    return "".join(parts) + "\n"


def write_outputs(summary: Mapping, out_dir: Path) -> list[Path]:
    """Create a new directory with summary.json, RULE04_TABLES.md and the plot; never overwrite."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=False, exist_ok=False)
    files = {
        "summary.json": json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        "RULE04_TABLES.md": tables_markdown(summary),
        "turnaround_vs_impact.svg": plot_svg(summary),
    }
    written = []
    for name, text in files.items():
        path = out_dir / name
        with open(path, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        written.append(path)
    return written
