"""Historical receiving checks use recorded bytes, never a simulator or policy."""

import copy
import json
import shutil

import pytest

from scripts import check_rule02_evidence as c


def small_inventory(tmp_path):
    data = b"original\n"
    (tmp_path / "record.json").write_bytes(data)
    return {"artifacts": [{"path": "record.json", "bytes": len(data), "sha256": c.digest(data)}]}


@pytest.mark.parametrize(
    "path", ["../outside", "/absolute", "C:drive", "x\\y", "x/../y", "./record.json"]
)
def test_inventory_refuses_path_escape(tmp_path, path):
    manifest = small_inventory(tmp_path)
    manifest["artifacts"][0]["path"] = path
    with pytest.raises(ValueError, match="unsafe"):
        c.check_inventory(tmp_path, manifest)


@pytest.mark.parametrize("change", ["duplicate", "size", "bytes", "missing", "extra"])
def test_inventory_refuses_corrupt_or_incomplete_evidence(tmp_path, change):
    manifest = small_inventory(tmp_path)
    if change == "duplicate":
        manifest["artifacts"].append(copy.deepcopy(manifest["artifacts"][0]))
    elif change == "size":
        manifest["artifacts"][0]["bytes"] += 1
    elif change == "bytes":
        (tmp_path / "record.json").write_bytes(b"changed!\n")
    elif change == "missing":
        (tmp_path / "record.json").unlink()
    else:
        (tmp_path / "unlisted.json").write_bytes(b"extra")
    with pytest.raises(ValueError):
        c.check_inventory(tmp_path, manifest)


def test_duplicate_json_keys_are_not_silently_overwritten(tmp_path):
    path = tmp_path / "record.json"
    path.write_text('{"value":1,"value":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        c.read_json(path)


def test_committed_inventory_has_exact_original_bytes():
    assert c.check_inventory(c.EVIDENCE, c.read_json(c.EVIDENCE / "MANIFEST.json")) == 1270


def test_all_saved_references_and_record_bindings_are_checked(monkeypatch):
    # The source-commit object is not present in shallow CI checkouts. This test
    # checks saved references against declared pins, not Git-source authentication.
    bindings = json.loads((c.EVIDENCE / "traces/rules-v1/A-rules-v1/result.json").read_bytes())[
        "bindings"
    ]
    bindings.pop("case_sha256")
    monkeypatch.setattr(c, "historical_bindings", lambda repo: bindings)
    report = c.check_evidence()
    assert (report["traces"], report["decisions"]) == (10, 300)
    assert report["current_implementation_verified"] is False
    assert report["independent_scientific_acceptance"] is False
    assert report["model_or_policy_executed"] is False


def test_rehashed_manifest_cannot_launder_a_wrong_record_binding(tmp_path, monkeypatch):
    bindings = c.read_json(c.EVIDENCE / "traces/rules-v1/A-rules-v1/result.json")["bindings"]
    bindings.pop("case_sha256")
    monkeypatch.setattr(c, "historical_bindings", lambda repo: bindings)
    root = tmp_path / "archive"
    shutil.copytree(c.EVIDENCE, root, ignore=shutil.ignore_patterns("__pycache__"))
    rel = "traces/rules-v1/A-rules-v1/result.json"
    result = c.read_json(root / rel)
    result["bindings"]["code_commit"] = "abcdef0123456789abcdef0123456789abcdef0123"
    data = c.canonical(result)
    (root / rel).write_bytes(data)
    manifest = c.read_json(root / "MANIFEST.json")
    for item in manifest["artifacts"]:
        if item["path"] == rel:
            item.update(sha256=c.digest(data), bytes=len(data))
    for item in manifest["traces"]:
        if item["trace"] == "traces/rules-v1/A-rules-v1":
            item["result_sha256"] = c.digest(data)
    (root / "MANIFEST.json").write_bytes(c.canonical(manifest))
    with pytest.raises(ValueError, match="bindings differ"):
        c.check_evidence(root)
