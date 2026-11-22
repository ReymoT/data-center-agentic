"""Offline demo: runs the real pipeline, shows blocked Scenario B, replays, refuses reuse."""

import json

import pytest

from dc_sustainability.rule_study import cases as c
from dc_sustainability.rule_study import demo
from tests.rule_study.helpers import REPO_ROOT, TEST_ONLY_COMMIT


@pytest.fixture(scope="module")
def demo_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("demo") / "out"
    return out, demo.run_demo(out, code_commit=TEST_ONLY_COMMIT)


def row(rows, case, policy):
    return next(x for x in rows if x["case"] == case and x["policy"] == policy)


def test_demo_covers_every_authored_case_for_every_policy(demo_run):
    _, rows = demo_run
    seen = {(x["case"], x["policy"]) for x in rows}
    for case in ("A", "B", "B-progress"):
        for policy in demo.POLICIES:
            assert (case, policy) in seen
    assert ("B-fault", "rules-v1") in seen


def test_demo_scenario_a_completes_and_scenario_b_is_blocked(demo_run):
    _, rows = demo_run
    assert row(rows, "A", "rules-v1")["completed"] == ("J1", "J2")
    blocked = row(rows, "B", "rules-v1")
    assert blocked["status"] == "BLOCKED" and blocked["completed"] == ()
    assert blocked["missed"] == ("J1", "J2")
    assert row(rows, "B-progress", "rules-v1")["completed"] == ("J1", "J2")


def test_demo_replays_identically_and_makes_no_model_calls(demo_run):
    _, rows = demo_run
    assert all(x["replay_identical"] for x in rows)
    assert all(x["model_call_count"] == 0 for x in rows)


def test_demo_writes_hash_checked_result_files(demo_run):
    out, rows = demo_run
    import hashlib

    for x in rows:
        if x["case"] == "A" and x["policy"] == "rules-v1":
            data = (out / "rules-v1" / "A-rules-v1" / "result.json").read_bytes()
            assert hashlib.sha256(data).hexdigest() == x["result_sha256"]
            assert "model_call_count" not in json.loads(data)  # result fields are reader-exact
            first = out / "rules-v1" / "A-rules-v1" / "decisions" / "decision-00.json"
            assert json.loads(first.read_text())["model_call_count"] == 0


def test_demo_behavior_is_deterministic_across_fresh_output_directories(tmp_path):
    # Behavior is deterministic. Bytes are not: the unchanged production checker mints a random
    # ``check_id`` per check, so fresh runs hash differently; replay of SAVED evidence is exact.
    keys = ("case", "policy", "status", "completed", "missed", "replay_identical")
    first = demo.run_demo(tmp_path / "one", code_commit=TEST_ONLY_COMMIT)
    second = demo.run_demo(tmp_path / "two", code_commit=TEST_ONLY_COMMIT)
    assert [tuple(x[k] for k in keys) for x in first] == [tuple(x[k] for k in keys) for x in second]


def test_main_refuses_a_non_empty_output_directory(tmp_path, capsys):
    (tmp_path / "keep.txt").write_text("x")
    assert demo.main(["--output-dir", str(tmp_path)]) == 2
    assert (tmp_path / "keep.txt").read_text() == "x"
    assert "refusing" in capsys.readouterr().err


def test_main_succeeds_on_an_empty_directory(tmp_path, capsys, monkeypatch):
    real = demo.make_bindings
    monkeypatch.setattr(
        demo,
        "make_bindings",
        lambda case, root, code_commit=None: real(case, root, code_commit=TEST_ONLY_COMMIT),
    )
    assert demo.main(["--output-dir", str(tmp_path / "fresh")]) == 0
    assert "model calls: 0" in capsys.readouterr().out


def test_main_reports_an_unbindable_checkout_instead_of_inventing_a_binding(
    tmp_path, capsys, monkeypatch
):
    def refuse(case, root, code_commit=None):
        raise demo.BindingError("a clean committed checkout is required")

    monkeypatch.setattr(demo, "make_bindings", refuse)
    assert demo.main(["--output-dir", str(tmp_path / "fresh")]) == 2
    assert "cannot bind" in capsys.readouterr().err


# --------------------------------------------------------------------------- spec consistency
def test_authored_cases_match_docs_specification_json():
    spec = json.loads((REPO_ROOT / "docs" / "rule_study" / "specification.json").read_text("utf-8"))
    text = json.dumps(spec)
    for needle in ("60", "20", "J1", "J2"):
        assert needle in text
    assert c.CASE_A.capacity_kw == 60 and c.CASE_A.background_kw == 20
