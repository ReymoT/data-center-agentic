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
    return hashlib.sha256(mc._bytes(path)).hexdigest()


def _json(path: Path) -> dict:
    return mc._load(path)


def _inputs(cases_path):
    if _sha(cases_path) != rollout.INPUTS["development_cases"][1]:
        raise ValueError("only the frozen retained development case set is supported")
    return rollout.pair()


def _validate_metric(pair, record, inputs):
    """Read/recompute retained artifacts only; saved replay remains attributed."""
    from dc_sustainability.evaluation import rule_study_receiving as rv

    _, sidecar, parsed = inputs
    relative = Path(record["trace_directory"])
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not relative.parts
        or relative.parts[0] != "trace"
    ):
        raise ValueError("trace must be inside its pair directory")
    folder = rollout.safe_path(pair / relative)
    if not folder.resolve().is_relative_to(pair.resolve()):
        raise ValueError("trace escapes pair")
    case, result, decisions = mc.load_run(folder)
    if case != rv.case_spec_for(parsed[record["case_id"]]).case_json():
        raise ValueError("trace differs from frozen case")
    if (
        result["policy_id"] != record["policy_id"]
        or record.get("replay", {}).get("overall") != "PASS"
    ):
        raise ValueError("saved policy/replay evidence refused")
    weights = next(e["weights"] for e in sidecar["cases"] if e["case_id"] == record["case_id"])
    recomputed = rollout._metric(folder, weights)
    if record["metric"] != recomputed or recomputed["execution_violations"]:
        raise ValueError("saved metric differs from retained trace accounting")
    signature = hashlib.sha256(
        json.dumps([d["execution"]["current_starts"] for d in decisions], sort_keys=True).encode()
    ).hexdigest()
    if signature != record["execution_signature"]:
        raise ValueError("saved execution signature differs")
    return recomputed


def load_run(run_dir: Path, cases_path: Path = CASES) -> dict:
    """Completed pair metrics, the run's own status record and the case strata."""
    run_dir = rollout.safe_path(run_dir)
    report, failure = run_dir / "rollout-report.json", run_dir / "rollout-failure.json"
    fallback = run_dir / "rollout-supervisor-failure.json"
    # A host failure takes precedence over even a complete report (e.g. failed cleanup).
    status_path = next((p for p in (fallback, failure, report) if p.exists()), None)
    if status_path is None:
        raise ValueError("no retained run status record")
    status = _json(status_path)
    complete = status_path == report and status.get("status") == "PASS"
    if not complete and status.get("status") != "FAIL_OR_INCOMPLETE":
        raise ValueError("unsupported failure status")
    inputs = _inputs(cases_path)
    case_set = inputs[0]
    strata = {c["case_id"]: c["stratum"] for c in case_set["cases"]}

    metrics, failed, commitments, authorities = [], [], [], set()
    entries = []
    for entry in run_dir.iterdir():
        rollout.safe_path(entry)
        entries.append(entry)
        if len(entries) > 1500:
            raise ValueError("excessive run inventory")
    pairs = sorted(p for p in entries if p.is_dir())
    if len(pairs) > 360:
        raise ValueError("too many pair directories")
    expected = {(c, p) for c in strata for p in POLICIES}
    for pair in pairs:
        result, pair_failure = pair / "pair-result.json", pair / "pair-failure.json"
        if pair_failure.is_file():
            record = _json(pair_failure)
            if (
                record.get("case_id"),
                record.get("policy_id"),
            ) not in expected or pair.name != f"{record['case_id']}-{record['policy_id']}":
                raise ValueError("failed pair identity refused")
            failed.append(
                {
                    "case_id": record.get("case_id"),
                    "policy_id": record.get("policy_id"),
                    "exception": record.get("exception"),
                    "message": record.get("message"),
                }
            )
            commitments.append((pair_failure.relative_to(run_dir).as_posix(), _sha(pair_failure)))
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
        if pair.name != f"{record['case_id']}-{record['policy_id']}":
            raise ValueError("pair folder identity differs")
        authority = record.get("authenticated_request_sha256")
        if (
            not isinstance(authority, str)
            or len(authority) != 64
            or any(c not in "0123456789abcdef" for c in authority)
        ):
            raise ValueError("original request hash missing or invalid")
        authorities.add(authority)
        before = _sha(result)
        metrics.append(_validate_metric(pair, record, inputs))
        if before != _sha(result):
            raise ValueError("pair record changed during validation")
        commitments.append((result.relative_to(run_dir).as_posix(), before))

    keys = [(m["case_id"], m["policy_id"]) for m in metrics]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate completed pair")
    recorded = status.get("completed_runs", status.get("runs"))
    if type(recorded) is not int or recorded < 0 or recorded > len(metrics):
        raise ValueError("completed pair count differs from the run's own record")
    if len(authorities) > 1 or (
        authorities
        and status.get("authenticated_request_sha256") not in (None, next(iter(authorities)))
    ):
        raise ValueError("mixed authenticated requests refused")
    if len({m["code_commit"] for m in metrics}) > 1:
        raise ValueError("mixed producer commits refused")
    shared_bindings = {
        json.dumps({k: v for k, v in m["bindings"].items() if k != "case_sha256"}, sort_keys=True)
        for m in metrics
    }
    if len(shared_bindings) > 1:
        raise ValueError("mixed producer source bindings refused")
    ordered = {(c, p): i for i, (c, p) in enumerate((c, p) for c in strata for p in POLICIES)}
    acknowledged = sorted(metrics, key=lambda m: ordered[(m["case_id"], m["policy_id"])])[:recorded]
    if status.get("coverage") is not None and status["coverage"] != rollout.coverage(
        acknowledged, strata
    ):
        raise ValueError("coverage differs from the run's own record")
    if complete and (set(keys) != expected or recorded != len(expected) or failed):
        raise ValueError("PASS requires every expected case/policy pair and no failures")
    if _json(status_path) != status:
        raise ValueError("status changed during validation")
    return {
        "metrics": sorted(metrics, key=lambda m: (m["case_id"], m["policy_id"])),
        "failed": failed,
        "strata": strata,
        "complete": complete,
        "run_status": status.get("status"),
        "stop_message": None if complete else status.get("message"),
        "recovered_unacknowledged_pairs": len(metrics) - recorded,
        "authenticated_request_sha256": next(iter(authorities), None),
        "inputs": [
            *[(p.name, _sha(p)) for p in (fallback, failure, report) if p.exists()],
            (Path(cases_path).name, _sha(cases_path)),
            ("development.accounting.json", rollout.INPUTS["development_accounting"][1]),
        ]
        + commitments,
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
                    "job_impact_total": sum(m["synthetic_impact"]["recomputed_total"] for m in runs)
                    if runs
                    else None,
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
            shift, joint_reductions = [], []
            for r in available:
                x = by_run[(r["case_id"], policy)]["turnaround_slots"]["values"]
                a = by_run[(r["case_id"], BASELINE)]["turnaround_slots"]["values"]
                if x and a:
                    shift.append(mean(x) - mean(a))
                    joint_reductions.append(r["reduction"])
            out.append(
                {
                    "stratum": stratum,
                    "policy_id": policy,
                    "role": "control_not_ranking"
                    if stratum == CONTROL
                    else "development_comparison",
                    "rows": len(group),
                    "expected_rows": sum(s == stratum for s in strata.values()),
                    "not_evaluated": sum(s == stratum for s in strata.values()) - len(group),
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
                    "matched_turnaround_reduction_median": median(joint_reductions)
                    if joint_reductions
                    else None,
                }
            )
    return out


def summarize(run: Mapping) -> dict:
    return {
        "record_kind": RECORD_KIND,
        "coverage_status": "COMPLETE" if run["complete"] else "PARTIAL",
        "run_status": run["run_status"],
        "stop_message": run["stop_message"],
        "recovered_unacknowledged_pairs": run["recovered_unacknowledged_pairs"],
        "authenticated_request_sha256": run["authenticated_request_sha256"],
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
            "Retained artifact consistency/recomputed arithmetic only; saved replay is attributed, not newly executed or independent-person acceptance.",
            "Recovered pairs beyond the last checkpoint are explicit; failed/in-flight work is not counted as complete.",
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
            f"{r['runs_with_blocked_decision']} | {_cell(r['job_impact_total'])} |"
        )
    lines += [
        "",
        "## Equal-work comparison against Greedy A",
        "",
        "| Stratum | Policy | Available / rows (not evaluated) | Reduction median [min, max] | "
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
            f"| {label} | {r['policy_id']} | {r['available']}/{r['rows']} ({r['not_evaluated']}) | {reduction} | "
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
        and r["matched_turnaround_reduction_median"] is not None
        and r["turnaround_shift_mean_slots"] is not None
    ]
    w, h, pad = 520, 340, 56
    xs = [p["turnaround_shift_mean_slots"] for p in points] + [0.0]
    ys = [100 * p["matched_turnaround_reduction_median"] for p in points] + [0.0]
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
        "Median equal-work reduction (%)</text>",
        f'<text x="{pad}" y="20">{e(summary["coverage_status"])} coverage; development cases only; '
        "missing-forecast control excluded</text>",
    ]
    for p in points:
        cx, cy = (
            px(p["turnaround_shift_mean_slots"]),
            py(100 * p["matched_turnaround_reduction_median"]),
        )
        label = f"{p['policy_id']} · {p['stratum']} (n={p['turnaround_shift_count']})"
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#3b6fb6"/>')
        parts.append(f'<text x="{cx + 8:.1f}" y="{cy - 6:.1f}">{e(label)}</text>')
    if not points:
        parts.append(
            f'<text x="{w / 2}" y="{h / 2}" text-anchor="middle">No available matched comparison'
            "</text>"
        )
    for i in range(5):
        x = x0 + (x1 - x0) * i / 4
        y = y0 + (y1 - y0) * i / 4
        parts.append(
            f'<text x="{px(x):.1f}" y="{h - pad + 16}" text-anchor="middle">{x:.2g}</text>'
        )
        parts.append(f'<text x="{pad - 6}" y="{py(y):.1f}" text-anchor="end">{y:.2g}</text>')
    parts.append("</svg>")
    return "".join(parts) + "\n"


def write_outputs(summary: Mapping, out_dir: Path) -> list[Path]:
    """Create a new directory with summary.json, RULE04_TABLES.md and the plot; never overwrite."""
    out_dir = rollout.safe_path(out_dir)
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
