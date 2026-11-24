"""RULE-07 demo page: built from the retained evidence on main, no policy or simulator runs."""

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
from html import escape as html_escape
from pathlib import Path

import pytest

from scripts import rule_demo_page_core as core

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "build_rule_demo_page.py"


@pytest.fixture(scope="module")
def inputs():
    return core.load_inputs({})


@pytest.fixture(scope="module")
def page(inputs):
    return core.render(inputs)


def _section(page, anchor):
    match = re.search(rf'<section id="{re.escape(anchor)}">(.*?)</section>', page, re.S)
    assert match, anchor
    return match.group(1)


def test_page_is_deterministic(inputs, page):
    assert core.render(core.load_inputs({})) == page


def test_page_makes_no_network_references(page):
    assert core.CSP in page
    assert not re.search(r"(?:src|href)=\"(?:https?:)?//", page)
    assert "<script" not in page


def test_every_case_and_policy_from_the_archive_is_shown(inputs, page):
    assert len(inputs["runs"]) == 10
    for case_id, policy in inputs["runs"]:
        assert f"<h4>{policy} " in _section(page, f"case-{case_id}")


def test_case_values_match_the_retained_records(inputs, page):
    a = _section(page, "case-A")
    assert "Executed at slot 0: J2 (executed)" in a  # rules-v1 and Greedy B delay J1
    assert "Executed at slot 0: J1, J2 (executed)" in a  # Greedy A starts both
    assert "Artificial impact: 8000 score-kWh" in a and "12000 score-kWh" in a
    b = _section(page, "case-B")
    assert b.count("Executed at slot 0: no starts (blocked)") == 3
    assert "Completed: J1, J2" not in b
    fault = _section(page, "case-B-fault")
    assert "slot 0: 20 + 30 + 30 kW &gt; 60 kW (excess 20)" in fault
    for (case_id, policy), run in inputs["runs"].items():
        total = run["result"]["accounting"]["synthetic_impact_total"]
        assert f"Artificial impact: {total} score-kWh" in _section(page, f"case-{case_id}")


def test_labels_keep_expected_observed_and_scope_distinct(page):
    for case_id in core.CASES:
        section = _section(page, f"case-{case_id}")
        assert core.BADGES["EXPECTED"] in section and core.BADGES["OBSERVED"] in section
    assert "not a measured advantage" in _section(page, "case-A")
    assert "not a P1 success" in _section(page, "case-B")
    assert "not a natural rules-v1 output" in _section(page, "case-B-fault")
    workflow = _section(page, "workflow")
    assert core.BADGES["EXPECTED"] in workflow and "design, not a result" in workflow


def test_s4_is_not_run_in_primary_and_pass_only_for_authored_rules_v1(inputs, page):
    section = _section(page, "verification")
    rows = re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td>(.*?)</tr>", section)
    s4 = {(d, p): re.findall(r">([A-Z_]+)</td>", cells)[3] for d, p, cells in rows}
    assert s4[("Primary 64 (Nov 22 attempt)", "rules-v1")] == "NOT_RUN"
    assert s4[("Authored A/B/B-fault/B-progress (Nov 23)", "rules-v1")] == "PASS"
    assert s4[("Authored A/B/B-fault/B-progress (Nov 23)", "greedy_a")] == "NOT_RUN"
    assert "INCOMPLETE" in section  # the original attempt stays recorded as history


def test_metrics_panel_is_pending_without_a_record_and_never_shows_zero_savings(tmp_path):
    page = core.render(core.load_inputs({}))
    assert core.BADGES["PENDING"] in _section(page, "metrics")
    record = {
        "label": "fixture",
        "runs": [],
        "equal_work_vs_greedy_a": [
            {
                "case_id": "B",
                "policy_id": "rules-v1",
                "available": False,
                "reason": "greedy_a_impact_not_positive",
            }
        ],
    }
    inputs = core.load_inputs({})
    inputs["metrics"] = record
    section = _section(core.render(inputs), "metrics")
    assert "unavailable: greedy_a_impact_not_positive" in section
    assert "(0.000)" not in section


def test_feedback_and_rules_come_from_their_sources(inputs, page):
    assert [r[0] for r in inputs["rules"]] == [f"R0{i}" for i in range(1, 10)]
    feedback = _section(page, "feedback")
    for item, status in inputs["feedback"]:
        assert item in feedback and status.split(".")[0] in feedback


def _copy_archive(tmp_path, mutate):
    src = core.DEFAULTS["archive"]
    out = tmp_path / "a.tar.gz"
    with tarfile.open(src, "r:gz") as tin, tarfile.open(out, "w:gz") as tout:
        for member in tin.getmembers():
            data = tin.extractfile(member).read() if member.isfile() else None
            data = mutate(member.name, data)
            if data is not None:
                member.size = len(data)
                tout.addfile(member, io.BytesIO(data))
            else:
                tout.addfile(member)
    return out


def test_tampered_archive_member_is_refused(tmp_path):
    def mutate(name, data):
        if name.endswith("A-rules-v1/result.json"):
            return data.replace(b'"complete"', b'"COMPLETE"')
        return data

    archive = _copy_archive(tmp_path, mutate)
    with pytest.raises(ValueError, match="manifest"):
        core.load_inputs({"archive": archive})


def test_missing_rule_table_or_feedback_is_refused(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("# nothing\n", "utf-8")
    with pytest.raises(ValueError, match="rule table"):
        core.load_inputs({"spec_md": empty})
    with pytest.raises(ValueError, match="feedback"):
        core.load_inputs({"feedback": empty})


def test_provenance_lists_every_input_hash(inputs, page):
    section = _section(page, "provenance")
    for key, _, digest in inputs["provenance"]:
        assert digest == hashlib.sha256(core.DEFAULTS[key].read_bytes()).hexdigest()
        assert digest in section


def test_cli_writes_once_and_never_overwrites(tmp_path):
    page = core.render(core.load_inputs({}, metrics=core.DEFAULT_METRICS))
    out = tmp_path / "demo.html"
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)], capture_output=True, text=True, cwd=ROOT
    )
    assert done.returncode == 0, done.stderr
    assert out.read_text("utf-8") == page
    again = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)], capture_output=True, text=True, cwd=ROOT
    )
    assert again.returncode != 0 and out.read_text("utf-8") == page
    shutil.rmtree(tmp_path)


def test_workflow_is_reimos_figure_2_read_from_its_mermaid_source(inputs, page):
    figure = inputs["workflow"]
    assert figure["title"].startswith("Figure 2.")
    section = _section(page, "workflow")
    for node, label in figure["nodes"].items():
        assert html_escape(label) in section
    assert ("GC", "N", "Fail or unavailable") in figure["edges"]
    assert ("L", "A", "Pass") in figure["edges"]
    assert html_escape(figure["caption"][:60]) in section


def test_default_metrics_on_main_match_the_reviewed_checksum():
    sums = (core.DEFAULT_METRICS.parent / "REVIEWED_SHA256SUMS.txt").read_text("utf-8")
    digest = hashlib.sha256(core.DEFAULT_METRICS.read_bytes()).hexdigest()
    assert f"{digest}  {core.DEFAULT_METRICS.name}" in sums
    section = _section(core.render(core.load_inputs({}, metrics=core.DEFAULT_METRICS)), "metrics")
    assert "8000 vs 12000" in section and "unavailable: " in section
    inputs = core.load_inputs({}, metrics=core.DEFAULT_METRICS)
    keys = [k for k, _, _ in inputs["provenance"]]
    assert "metrics" in keys and "metrics_review_receipt" in keys


def test_missing_workflow_figure_is_refused(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("# nothing\n", "utf-8")
    with pytest.raises(ValueError, match="Figure 2"):
        core.load_inputs({"workflow": empty})


@pytest.mark.parametrize(
    "missing", ["B-progress-greedy_b/", "A-rules-v1/decisions/decision-29.json"]
)
def test_missing_saved_run_or_decision_is_refused(tmp_path, missing):
    archive = tmp_path / "partial.tar.gz"
    with (
        tarfile.open(core.DEFAULTS["archive"], "r:gz") as src,
        tarfile.open(archive, "w:gz") as dst,
    ):
        for member in src.getmembers():
            if missing in member.name:
                continue
            dst.addfile(member, src.extractfile(member) if member.isfile() else None)
    with pytest.raises(ValueError, match="incomplete"):
        core.load_inputs({"archive": archive})


def test_duplicate_archive_member_is_refused(tmp_path):
    archive = _copy_archive(tmp_path, lambda name, data: data)
    duplicate = tmp_path / "duplicate.tar.gz"
    with tarfile.open(archive, "r:gz") as src, tarfile.open(duplicate, "w:gz") as dst:
        for member in src.getmembers():
            dst.addfile(member, src.extractfile(member) if member.isfile() else None)
            if member.name.endswith("A-rules-v1/result.json"):
                dst.addfile(member, src.extractfile(member))
    with pytest.raises(ValueError, match="duplicate"):
        core.load_inputs({"archive": duplicate})


def test_tampered_metrics_are_refused_before_rendering(tmp_path):
    for name in (
        core.DEFAULT_METRICS.name,
        "manager-review-receipt.json",
        "REVIEWED_SHA256SUMS.txt",
    ):
        shutil.copyfile(core.DEFAULT_METRICS.parent / name, tmp_path / name)
    metric = tmp_path / core.DEFAULT_METRICS.name
    metric.write_bytes(metric.read_bytes().replace(b"12000", b"99000"))
    with pytest.raises(ValueError, match="checksum"):
        core.load_inputs({}, metrics=metric)


def test_metrics_without_review_receipt_are_refused(tmp_path):
    metric = tmp_path / "unreviewed.json"
    metric.write_text(json.dumps({"runs": [], "equal_work_vs_greedy_a": []}), "utf-8")
    with pytest.raises(OSError):
        core.load_inputs({}, metrics=metric)


def test_portable_page_does_not_claim_markdown_is_a_rendered_diagram(page):
    assert "Rendered diagram:" not in page
    assert "../docs/report/RULE05_WORKFLOW_DIAGRAMS.md" not in page


def test_accepted_metric_receiving_and_turnaround_are_shown():
    inputs = core.load_inputs({}, metrics=core.DEFAULT_METRICS)
    section = _section(core.render(inputs), "metrics")
    assert inputs["metrics_accepted"] and "Nisha accounting/metrics, comment 7121894902" in section
    assert "independent metric receiving" not in section
    assert "Mean turnaround (slots)" in section and "33.3%" in section
    assert "Do not add those counts together" in section


def test_modified_accounting_receiving_source_refused(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("not the original reply", encoding="utf-8")
    with pytest.raises(ValueError, match="receiving source"):
        core.load_inputs({"accounting_source": source}, metrics=core.DEFAULT_METRICS)
