import copy
import json
from pathlib import Path

import pytest

from scripts.validate_i02_freeze_manifest import CATEGORIES, main, validate_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/i02/freeze-manifest.json"


def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def all_frozen(manifest):
    manifest = copy.deepcopy(manifest)
    for item in manifest["items"]:
        item.update(status="frozen", sha256="a" * 64, blocker=None)
    manifest["freeze"] = {"commit": "b" * 40, "frozen_at": "2026-11-13", "frozen_by": "Nisha"}
    return manifest


def test_checked_in_manifest_is_a_valid_pre_freeze_checklist():
    manifest = load()
    assert validate_manifest(manifest) == []
    assert manifest["evidence_kind"] == "pre_freeze_checklist_not_frozen"
    assert {i["category"] for i in manifest["items"]} == set(CATEGORIES)
    assert not any(i["status"] == "frozen" for i in manifest["items"])


def test_readiness_names_every_unfrozen_item_and_the_missing_commit():
    manifest = load()
    blockers = validate_manifest(manifest, require_ready=True)
    for item in manifest["items"]:
        assert any(b.startswith(f"{item['id']}: ") for b in blockers)
    assert any("#112" in b for b in blockers)  # blockers carry their reason
    assert "freeze.commit is not recorded" in blockers


def test_ready_when_every_item_is_frozen_with_evidence():
    assert validate_manifest(all_frozen(load()), require_ready=True) == []


def test_planned_matrix_is_300_runs_and_the_accepted_call_maxima():
    matrix = load()["run_matrix"]
    assert matrix["total_runs"] == 300
    assert matrix["maximum_model_calls"] == {"plain_llm": 2160, "agent": 6480}


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda m: m["run_matrix"].update(total_runs=240), "total_runs"),
        (lambda m: m["run_matrix"]["episodes"].update(total=24), "total episodes"),
        (lambda m: m["run_matrix"]["trials_per_system"].update(agent=2), "total_runs"),
        (lambda m: m["run_matrix"]["trials_per_system"].pop("random_forest_d"), "six systems"),
        (lambda m: m["run_matrix"]["maximum_model_calls"].update(agent=7000), "agent calls"),
        (lambda m: m["items"][0].update(status="done"), "status must be"),
        (lambda m: m["items"][2].update(blocker=""), "names its blocker"),
        (lambda m: m["items"][1].update(sha256="abc"), "64 lowercase hex"),
        (lambda m: m["items"][1].update(owner="Someone"), "team member"),
        (lambda m: m["items"].append(copy.deepcopy(m["items"][0])), "repeated"),
        (lambda m: m["items"][0].pop("sha256"), "missing fields"),
        (lambda m: m["freeze"].update(commit="abc123"), "40-character"),
        (
            lambda m: m.update(items=[i for i in m["items"] if i["category"] != "ontology"]),
            "no item covers ontology",
        ),
    ],
)
def test_integrity_problems_are_refused(change, message):
    manifest = load()
    change(manifest)
    assert any(message in b for b in validate_manifest(manifest))


def test_frozen_item_needs_a_hash_or_an_in_repo_path_with_the_freeze_commit():
    manifest = all_frozen(load())
    model = next(i for i in manifest["items"] if i["id"] == "trained-models-c-d")
    model["sha256"] = None  # no path: only its own hash can pin it
    assert any("trained-models-c-d: frozen" in b for b in validate_manifest(manifest))
    prompts = next(i for i in manifest["items"] if i["id"] == "plain-prompts")
    prompts["sha256"] = None  # in the repo: the freeze commit pins it
    assert not any("plain-prompts" in b for b in validate_manifest(manifest))


def test_command_line_exit_codes(tmp_path, capsys):
    assert main([str(MANIFEST)]) == 0
    assert "VALID: not a readiness claim" in capsys.readouterr().out
    assert main([str(MANIFEST), "--require-ready"]) == 1
    ready = tmp_path / "ready.json"
    ready.write_text(json.dumps(all_frozen(load())), encoding="utf-8")
    assert main([str(ready), "--require-ready"]) == 0
