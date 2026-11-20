"""Real dummy-process containment, not rule-study execution or fabricated proof."""

import ctypes
import json
import os
from ctypes import wintypes
from unittest.mock import patch

import pytest

from scripts import rehearse_rule_study_supervisor as cli


@pytest.mark.parametrize(
    "mode,limit", [("success", 3), ("failure", 3), ("timeout", 0.7), ("descendant", 4)]
)
@pytest.mark.skipif(os.name != "nt", reason="requires actual Windows process-tree containment")
def test_actual_workers_and_descendants_are_stopped_with_evidence(tmp_path, mode, limit):
    out = tmp_path / mode
    result = cli.rehearse(mode, out, limit)
    assert result["rehearsal_passed"], result
    assert not result["research_execution_authorized"]
    assert json.loads((out / "worker.json").read_text())["mode"] == mode
    assert json.loads((out / "rehearsal.json").read_text()) == result
    if mode == "failure":
        assert result["supervision"]["returncode"] == 7
        assert "dummy failure" in (out / "failure.txt").read_text()
    pids = [result["supervision"]["pid"]]
    if mode == "descendant":
        assert (out / "descendant-ready.txt").read_text() == "ready"
        pids.append(json.loads((out / "descendant.json").read_text())["pid"])
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    for pid in pids:
        handle = api.OpenProcess(0x100000, False, pid)
        if handle:
            try:
                assert api.WaitForSingleObject(handle, 0) == 0
            finally:
                api.CloseHandle(handle)
        else:
            assert ctypes.get_last_error() == 87  # no such process


@pytest.mark.parametrize("limit", [True, -1, 0, 6, float("nan"), float("inf")])
def test_invalid_limits_do_not_start_a_child(tmp_path, limit):
    with patch.object(cli, "supervise", side_effect=AssertionError("must not spawn")):
        with pytest.raises(ValueError):
            cli.rehearse("success", tmp_path / "unused", limit)
    assert not (tmp_path / "unused").exists()


def test_unknown_command_cannot_be_dispatched(tmp_path):
    with patch.object(cli, "supervise", side_effect=AssertionError("must not spawn")):
        with pytest.raises(ValueError):
            cli.rehearse("verify_rule_study.py", tmp_path / "unused")


@pytest.mark.skipif(os.name != "nt", reason="requires Windows preflight")
def test_output_reuse_is_refused_before_launch(tmp_path):
    marker = tmp_path / "keep.txt"
    marker.write_text("original")
    with patch.object(cli, "supervise", side_effect=AssertionError("must not spawn")):
        with pytest.raises(FileExistsError):
            cli.rehearse("success", tmp_path)
    assert marker.read_text() == "original"


def test_unavailable_containment_refuses_without_creating_output(tmp_path):
    with patch.object(cli.os, "name", "posix"):
        with pytest.raises(OSError, match="no uncontained fallback"):
            cli.rehearse("success", tmp_path / "unused")
    assert not (tmp_path / "unused").exists()
