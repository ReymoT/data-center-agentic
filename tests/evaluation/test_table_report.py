"""E06 LaTeX report tables rendered from the saved study-tables JSON (public fixtures)."""

import json
import re

import pytest

from dc_sustainability.evaluation import study_tables as t
from dc_sustainability.evaluation import table_report as tr
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from scripts import render_study_tables as cli
from tests.evaluation.test_study_tables import FAST, PLANNED, TRIALS, pair_runs, run


def report(runs=None):
    runs = pair_runs() if runs is None else runs
    return json.loads(
        json.dumps(t.study_report(runs, PLANNED, TRIALS, Q03_OPTION_B, settings=FAST))
    )


def balanced(text):
    begins = re.findall(r"\\begin\{(\w+\*?)\}", text)
    ends = re.findall(r"\\end\{(\w+\*?)\}", text)
    return sorted(begins) == sorted(ends) and text.count("{") == text.count("}")


def test_every_table_states_the_split_and_is_balanced_latex():
    text = tr.render(report(), "a" * 64)
    assert balanced(text)
    captions = re.findall(r"\\caption\{(.*)\}", text)
    assert captions and all("Development data: not a study result." in c for c in captions)
    assert "% Split: development; status: not_a_frozen_result" in text


def test_held_out_captions_say_held_out():
    r = report()
    r["split"] = "held_out"
    assert "Held-out episodes." in tr.render(r, "a" * 64)


def test_paired_cells_are_the_json_numbers_not_recomputed():
    r = report()
    row = next(
        x for x in r["comparisons"] if x["metric"] == "decision_accuracy" and x["cohort"] == "core"
    )
    text = "\n".join(tr.paired_table(r))
    ep = row["by_episode"]
    expected = f"${ep['estimate']:+.2f}$ [${ep['lower']:+.2f}$, ${ep['upper']:+.2f}$]"
    assert expected in text


def test_core_and_withheld_are_separate_tables():
    text = tr.render(report(), "a" * 64)
    assert "tab:paired-core" in text and "tab:paired-withheld" in text


def test_an_absent_estimate_prints_a_dash_and_its_exclusion_reason():
    r = report()
    row = next(
        x for x in r["comparisons"] if x["metric"] == "decision_accuracy" and x["cohort"] == "core"
    )
    row["by_episode"] = {**row["by_episode"], "estimate": None, "episodes": 0}
    row["excluded_by_reason"] = {"value_unavailable": 2}
    line = next(x for x in tr.paired_table(r) if x.startswith("Decision accuracy"))
    assert "---" in line and "2 value\\_unavailable" in line


def test_a_blocked_savings_comparison_is_shown_as_blocked():
    r = report()
    r["savings"] = [
        {
            "metric": "savings_kg",
            "baseline": "plain_llm",
            "candidate": "agent",
            "status": "blocked",
            "reason": "unequal_trial_rule_not_agreed",
            "by_episode": None,
            "by_date": None,
        }
    ]
    text = "\n".join(tr.savings_table(r))
    assert "blocked: unequal\\_trial\\_rule\\_not\\_agreed" in text


def test_unscored_runs_are_counted_without_episode_ids():
    r = report()
    r["unscored_runs"] = [
        {"system": "agent", "episode_id": "EP-SECRET", "trial": 0, "reason": "replay_refused"}
    ]
    text = tr.render(r, "a" * 64)
    assert "1 replay_refused" in text and "EP-SECRET" not in text


def test_no_episode_ids_appear_in_rendered_tables():
    text = tr.render(report(), "a" * 64)
    assert not any(eid in text for eid in PLANNED)


def test_cli_refuses_an_existing_output(tmp_path):
    source = tmp_path / "tables.json"
    source.write_text(json.dumps(report()), encoding="utf-8")
    out = tmp_path / "tables.tex"
    assert cli.main(["--report", str(source), "--out", str(out)]) == 0
    assert balanced(out.read_text(encoding="utf-8"))
    with pytest.raises(FileExistsError):
        cli.main(["--report", str(source), "--out", str(out)])


def test_scenario_table_keeps_missing_counts():
    runs = pair_runs() + [run("EP-A", "greedy_a"), run("EP-B", "greedy_a")]
    r = report(runs)
    cell = next(
        x
        for x in r["scenario_summaries"]
        if x["metric"] == "completed_jobs" and x["cohort"] == "core"
    )
    cell["missing"] = 1
    text = "\n".join(tr.scenario_table(r, "completed_jobs"))
    assert "1 missing" in text


def test_tex_escapes_braces_dollars_and_control_characters_once():
    assert tr._tex("{x}$~^\\") == r"\{x\}\$\textasciitilde{}\textasciicircum{}\textbackslash{}"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_nonfinite_values_cannot_appear_as_scientific_numbers(value):
    with pytest.raises(ValueError, match="nonfinite or nonnumeric"):
        tr._num(value, 2)


def test_heldout_split_does_not_erase_unfrozen_status():
    r = report()
    r["split"] = "held_out"
    text = tr.render(r, "a" * 64)
    assert "not\\_a\\_frozen\\_result" in text and "freeze acceptance is not established" in text


def test_unscored_private_exception_details_stay_only_in_json():
    r = report()
    r["unscored_runs"] = [{"reason": "EP-SECRET failed at C:/private"}]
    text = tr.render(r, "a" * 64)
    assert "EP-SECRET" not in text and "C:/private" not in text and "1 details_withheld" in text
