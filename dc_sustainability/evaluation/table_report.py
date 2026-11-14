"""E06 report tables: LaTeX rendered from the saved ``study_tables`` JSON only.

Every number comes from the JSON written by ``scripts/build_study_tables.py``; nothing is
recomputed here. Captions state the split, so development tables cannot pass as held-out
findings. Missing values stay visible: an absent estimate prints as an em dash, an
interval that could not be formed says so, and exclusions are counted with their reasons.

Differences are candidate minus baseline (Agent minus Plain LLM). Savings are baseline
minus candidate in kg, so a positive value means the candidate emitted less, and they
exist only where the equal-work rule allowed a comparison.
"""

import math
import re
from collections.abc import Iterable

SYSTEMS = {
    "agent": "Agent",
    "plain_llm": "Plain LLM",
    "greedy_a": "Greedy A",
    "greedy_b": "Greedy B",
    "decision_tree_c": "Decision tree C",
    "random_forest_d": "Random forest D",
}
# metric -> (label, decimals)
METRICS = {
    "decision_accuracy": ("Decision accuracy", 2),
    "unsafe_rate_initial": ("Unsafe rate, initial", 2),
    "unsafe_rate_repaired": ("Unsafe rate, repaired", 2),
    "unsafe_rate_fallback": ("Unsafe rate, fallback", 2),
    "unsafe_rate_final": ("Unsafe rate, final", 2),
    "unsafe_rate_without_omissions_initial": ("Unsafe excl. omissions, initial", 2),
    "unsafe_rate_without_omissions_repaired": ("Unsafe excl. omissions, repaired", 2),
    "unsafe_rate_without_omissions_fallback": ("Unsafe excl. omissions, fallback", 2),
    "unsafe_rate_without_omissions_final": ("Unsafe excl. omissions, final", 2),
    "repair_rate": ("Repair rate", 2),
    "fallback_rate": ("Fallback rate", 2),
    "completed_jobs": ("Completed jobs", 2),
    "missed_jobs": ("Deadline misses", 2),
    "unfinished_jobs": ("Unfinished jobs", 2),
    "completed_it_energy_kwh": ("Completed IT energy (kWh)", 1),
    "completed_job_emissions_kg": ("Completed-job emissions (kg)", 1),
    "model_calls": ("Model calls", 2),
    "latency_ms": ("Latency (ms)", 0),
    "prompt_tokens": ("Prompt tokens", 0),
    "completion_tokens": ("Completion tokens", 0),
    "savings_kg": ("Emissions saved (kg)", 1),
}
PRIMARY = (
    "decision_accuracy",
    "unsafe_rate_initial",
    "unsafe_rate_final",
    "unsafe_rate_without_omissions_initial",
    "repair_rate",
    "fallback_rate",
    "completed_jobs",
    "missed_jobs",
    "model_calls",
    "latency_ms",
)
SCENARIO_METRICS = ("decision_accuracy", "unsafe_rate_final", "completed_jobs", "missed_jobs")
DASH = "---"


def _tex(text: str) -> str:
    escapes = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(escapes.get(c, c) for c in text.replace("\n", " ").replace("\r", " "))


def _reason(text: str) -> str:
    # Detailed exception text can contain private IDs/paths. Full reasons stay in JSON.
    return text if re.fullmatch(r"[a-z][a-z0-9_]*", text) else "details_withheld"


def _num(value, decimals: int, signed: bool = False) -> str:
    if value is None:
        return DASH
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("report contains a nonfinite or nonnumeric measure")
    return "$" + (f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}") + "$"


def _interval(block: dict | None, decimals: int) -> str:
    """'est [lo, hi]', or the estimate with why there is no interval."""
    if block is None or block.get("estimate") is None:
        return DASH
    est = _num(block["estimate"], decimals, signed=True)
    if block.get("lower") is None or block.get("upper") is None:
        return f"{est} (no CI)"
    return f"{est} [{_num(block['lower'], decimals, True)}, {_num(block['upper'], decimals, True)}]"


def _split_note(report: dict) -> str:
    split = report.get("split")
    if split == "held_out":
        return f"Held-out episodes. Saved-report status: {_tex(str(report.get('status', 'unknown')))}; freeze acceptance is not established by this renderer."
    return f"{_tex(str(split)).capitalize()} data: not a study result."


def _excluded(row: dict) -> str:
    reasons = row.get("excluded_by_reason") or {}
    if not reasons:
        return "0"
    return ", ".join(f"{n} {_tex(_reason(k))}" for k, n in sorted(reasons.items()))


def _table(
    caption: str, label: str, columns: str, head: list[str], rows: list[list[str]], wide=False
) -> list[str]:
    env = "table*" if wide else "table"
    return [
        rf"\begin{{{env}}}[htbp]",
        rf"\caption{{{caption}}}",
        r"\begin{center}",
        r"\footnotesize",
        rf"\begin{{tabular}}{{{columns}}}",
        r"\hline",
        " & ".join(rf"\textbf{{{h}}}" for h in head) + r" \\",
        r"\hline",
        *(" & ".join(r) + r" \\" for r in rows),
        r"\hline",
        r"\end{tabular}",
        rf"\label{{{label}}}",
        r"\end{center}",
        rf"\end{{{env}}}",
        "",
    ]


def paired_table(report: dict, cohort: str = "core", metrics: Iterable[str] = PRIMARY) -> list[str]:
    rows_by_metric = {r["metric"]: r for r in report["comparisons"] if r["cohort"] == cohort}
    if not rows_by_metric:
        return []
    any_row = next(iter(rows_by_metric.values()))
    cand, base = SYSTEMS.get(any_row["candidate"]), SYSTEMS.get(any_row["baseline"])
    rows = []
    for metric in metrics:
        row = rows_by_metric.get(metric)
        label, dec = METRICS[metric]
        if row is None:
            rows.append([label, DASH, DASH, DASH, DASH])
            continue
        ep = row["by_episode"]
        rows.append(
            [
                label,
                _interval(ep, dec),
                _interval(row["by_date"], dec),
                str(ep["episodes"]),
                _excluded(row),
            ]
        )
    res = report["resampling"]
    caption = (
        f"Paired differences, {cand} minus {base} ({cohort} episodes). Episode intervals "
        f"from {res['resamples']:,} resamples, {round(res['confidence'] * 100)}\\%; "
        f"date resampling is a sensitivity check. {_split_note(report)}"
    )
    return _table(
        caption,
        f"tab:paired-{cohort}",
        "|l|c|c|c|c|",
        ["Measure", "By episode", "By date", "Episodes", "Excluded"],
        rows,
        wide=True,
    )


def savings_table(report: dict) -> list[str]:
    rows = []
    for row in report["savings"]:
        pair = f"{SYSTEMS.get(row['candidate'])} vs {SYSTEMS.get(row['baseline'])}"
        cohort = row.get("cohort", "all")
        if row.get("status") == "blocked":
            rows.append(
                [pair, _tex(str(cohort)), "blocked: " + _tex(_reason(row["reason"])), DASH, DASH]
            )
            continue
        ep = row["by_episode"]
        rows.append(
            [pair, _tex(cohort), _interval(ep, 1), str(ep["episodes"] if ep else 0), _excluded(row)]
        )
    if not rows:
        return []
    caption = (
        "Equal-work emissions savings (kg, baseline minus candidate; positive means the "
        "candidate emitted less). Episodes whose schedules did not complete the same work "
        f"are excluded and counted. {_split_note(report)}"
    )
    return _table(
        caption,
        "tab:savings",
        "|l|c|c|c|c|",
        ["Comparison", "Cohort", "Saved, by episode", "Episodes", "Excluded"],
        rows,
        wide=True,
    )


def scenario_table(report: dict, metric: str, cohort: str = "core") -> list[str]:
    rows = [
        r for r in report["scenario_summaries"] if r["metric"] == metric and r["cohort"] == cohort
    ]
    if not rows:
        return []
    scenarios = sorted({r["scenario"] for r in rows})
    label, dec = METRICS[metric]
    cell = {(r["system"], r["scenario"]): r for r in rows}

    def fmt(r):
        if r is None:
            return DASH
        mean = _num(r["mean"], dec)
        sd = "" if r["std"] is None else f" $\\pm$ {_num(r['std'], dec)}"
        miss = f", {r['missing']} missing" if r["missing"] else ""
        return f"{mean}{sd} (n={r['runs']}{miss})"

    body = [
        [SYSTEMS.get(system, _tex(system))] + [fmt(cell.get((system, sc))) for sc in scenarios]
        for system in SYSTEMS
        if any((system, sc) in cell for sc in scenarios)
    ]
    caption = (
        f"{label} by scenario ({cohort} episodes): mean $\\pm$ standard deviation over runs, "
        f"with run counts and missing values. {_split_note(report)}"
    )
    return _table(
        caption,
        f"tab:scenario-{metric.replace('_', '-')}-{cohort}",
        "|l|" + "c|" * len(scenarios),
        ["System", *(_tex(sc) for sc in scenarios)],
        body,
        wide=True,
    )


def ties_table(report: dict) -> list[str]:
    rows = [
        [
            SYSTEMS.get(r["system"], _tex(r["system"])),
            _tex(r["cohort"]),
            _num(r["tie_rate"], 2),
            f"{r['tied']} / {r['comparable']}",
            str(r["no_choice"]),
            f"{r['uncovered']} / {r['unverifiable']}",
        ]
        for r in report["forecast_ties"]
    ]
    if not rows:
        return []
    caption = (
        "Forecast ties in Greedy B's job decisions: a tie means two or more start times had "
        f"equal forecast emissions, so the forecast gave no timing signal. {_split_note(report)}"
    )
    return _table(
        caption,
        "tab:forecast-ties",
        "|l|c|c|c|c|c|",
        [
            "System",
            "Cohort",
            "Tie rate",
            "Tied / comparable",
            "No choice",
            "Uncovered / unverifiable",
        ],
        rows,
    )


def render(
    report: dict, source_sha256: str, scenario_metrics: Iterable[str] = SCENARIO_METRICS
) -> str:
    """All report tables as one LaTeX fragment, headed by its provenance."""
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("source JSON hash must be SHA256")
    unscored = report.get("unscored_runs") or []
    lines = [
        f"% Generated by scripts/render_study_tables.py from study tables SHA256 {source_sha256}.",
        f"% Split: {report['split']}; status: {report['status']}; protocol: {report['protocol']}.",
        f"% Planned episodes: {report['planned_episodes']}; scored runs: {report['scored_runs']}; "
        f"unscored runs: {len(unscored)}.",
        "% Do not edit numbers by hand: re-render from the saved JSON.",
        "",
    ]
    for cohort in ("core", "withheld"):
        lines += paired_table(report, cohort)
    lines += savings_table(report)
    for metric in scenario_metrics:
        for cohort in ("core", "withheld"):
            lines += scenario_table(report, metric, cohort)
    lines += ties_table(report)
    if unscored:
        # Counts by reason only: episode IDs stay in the private JSON, not in report text.
        reasons: dict[str, int] = {}
        for u in unscored:
            reason = _reason(u["reason"])
            reasons[reason] = reasons.get(reason, 0) + 1
        lines.append(
            "% Unscored runs (listed in the JSON, never dropped): "
            + "; ".join(f"{n} {reason}" for reason, n in sorted(reasons.items()))
        )
    return "\n".join(lines).rstrip() + "\n"
