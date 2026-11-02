"""Viewer exports actual test-run evidence and refuses inconsistent or private units."""

import json
from pathlib import Path

import pytest

from dc_sustainability.experiments import runner
from dc_sustainability.experiments.config import load_bundle
from dc_sustainability.visualization.trace_explorer import build, project_unit
from tests.experiments.test_runner import config


@pytest.fixture
def unit(tmp_path):
    bundle = Path(__file__).resolve().parents[2] / "docs/evidence/ep-hand1-episode-bundle.json"
    episode = load_bundle(bundle).episode
    cfg = config(bundle, episode, systems=("greedy_a",))
    [status] = runner.run(cfg, tmp_path / "runs")
    return tmp_path / "runs" / cfg.run_id / "units" / status.unit.key


def test_export_is_complete_read_only_and_excludes_raw_text(unit, tmp_path):
    trace = next((unit / "traces").glob("*.json"))
    record = json.loads(trace.read_text())
    record["raw_response"] = "SECRET</script><script>alert('x')</script>"
    record["errors"] = ["PRIVATE MACHINE PATH"]
    trace.write_text(json.dumps(record), encoding="utf-8")
    originals = {p: p.read_bytes() for p in unit.rglob("*.json")}
    output = tmp_path / "viewer.html"
    summary = build([unit], output)
    assert summary["units"] == 1 and summary["traces"] == 30 and summary["model_calls"] == 0
    html = output.read_text()
    assert "SECRET" not in html and "PRIVATE MACHINE PATH" not in html
    assert "connect-src 'none'" in html and "{{DATA}}" not in html
    assert "innerHTML" not in html
    assert originals == {p: p.read_bytes() for p in unit.rglob("*.json")}
    with pytest.raises(FileExistsError):
        build([unit], output)


def test_incomplete_and_mixed_identity_units_are_refused(unit):
    trace = next((unit / "traces").glob("*.json"))
    original = trace.read_text()
    data = json.loads(original)
    data["run_id"] = "RUN-OTHER"
    trace.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity differs"):
        project_unit(unit)
    trace.write_text(original)
    trace.unlink()
    with pytest.raises(ValueError, match="every slot"):
        project_unit(unit)


def test_private_episode_and_duplicate_units_are_refused(unit, tmp_path):
    with pytest.raises(ValueError, match="distinct"):
        build([unit, unit], tmp_path / "duplicate.html")
    result = json.loads((unit / "result.json").read_text())
    result["episode_id"] = "EP-NOTPUBLIC"
    (unit / "result.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="public EP-HAND1"):
        build([unit], tmp_path / "private.html")


def test_rendered_payload_contains_saved_status_not_inferred_pass(unit):
    data = project_unit(unit)
    assert data["completed"] == 2
    assert data["records"][24]["final_status"] == "blocked"
    assert all(stage["check"] == "not checked" for stage in data["records"][24]["stages"])
    assert all("raw_response" not in record for record in data["records"])
