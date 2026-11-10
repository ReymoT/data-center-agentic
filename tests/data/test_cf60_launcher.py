"""Real Windows process-stop tests with synthetic programs; no source/model access."""

import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import pytest

from scripts import launch_cf60_ingest as launcher
from tests.data.test_cf60_extract import approval_fixture

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Job Object stop controls")


def command(code):
    return [sys.executable, "-c", "import sys; assert sys.stdin.buffer.read(1)==b'G'; " + code]


def alive(pid):
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x100000, False, pid)
    if not handle:
        return False
    try:
        return api.WaitForSingleObject(handle, 0) == 258
    finally:
        api.CloseHandle(handle)


@pytest.mark.parametrize("exit_code,status", [(0, "succeeded"), (7, "failed")])
def test_success_and_nonzero_do_not_retry(exit_code, status):
    result = launcher.supervise(command(f"sys.exit({exit_code})"), 5)
    assert result["status"] == status
    assert result["returncode"] == exit_code
    assert result["released"] and result["cleanup_verified"]
    assert not alive(result["pid"])


def test_timeout_kills_child_and_grandchild(tmp_path):
    pid_file = tmp_path / "grandchild.pid"
    grandchild = "import time; time.sleep(30)"
    code = (
        "import subprocess,time,pathlib; "
        f"p=subprocess.Popen([sys.executable,'-c',{grandchild!r}]); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); time.sleep(30)"
    )
    result = launcher.supervise(command(code), 2)
    assert result["status"] == "timed_out"
    assert result["cleanup_verified"] and result["released"]
    assert result["elapsed_including_cleanup_s"] < 6
    assert pid_file.is_file(), "synthetic grandchild was actually started"
    assert not alive(int(pid_file.read_text()))
    assert not alive(result["pid"])


def test_assignment_failure_never_releases_child(tmp_path, monkeypatch):
    marker = tmp_path / "must-not-exist"
    monkeypatch.setattr(launcher.WindowsJob, "assign", lambda *a: (_ for _ in ()).throw(OSError()))
    result = launcher.supervise(command(f"open({str(marker)!r},'w').close()"), 5)
    assert result["status"] == "supervision_failed"
    assert result["cleanup_verified"] and not result["released"]
    assert not marker.exists() and not alive(result["pid"])


def test_deadline_before_release_never_starts_work(tmp_path, monkeypatch):
    marker = tmp_path / "must-not-exist"
    original = launcher.WindowsJob.assign

    def delayed(self, pid):
        original(self, pid)
        time.sleep(0.1)

    monkeypatch.setattr(launcher.WindowsJob, "assign", delayed)
    result = launcher.supervise(command(f"open({str(marker)!r},'w').close()"), 0.05)
    assert result["status"] == "timed_out_before_release"
    assert not result["released"] and result["cleanup_verified"]
    assert not marker.exists()


def test_interrupt_cleans_up(tmp_path, monkeypatch):
    original = subprocess.Popen.wait

    def interrupt_once(self, timeout=None):
        monkeypatch.setattr(subprocess.Popen, "wait", original)
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess.Popen, "wait", interrupt_once)
    result = launcher.supervise(command("import time; time.sleep(30)"), 5)
    assert result["status"] == "interrupted"
    assert result["cleanup_verified"] and not alive(result["pid"])


def test_supervisor_death_closes_job_and_stops_worker(tmp_path):
    marker = tmp_path / "worker.pid"
    worker = command(
        f"import os,time,pathlib; pathlib.Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(30)"
    )
    parent = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"from scripts.launch_cf60_ingest import supervise; supervise({worker!r},20)",
        ],
        cwd=launcher.ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    pid = None
    try:
        deadline = time.monotonic() + 8
        while not marker.exists() and parent.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.is_file(), "contained synthetic worker started"
        pid = int(marker.read_text())
        assert alive(pid)
        parent.kill()
        parent.wait(timeout=3)
        deadline = time.monotonic() + 3
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not alive(pid)
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=3)


def test_pending_approval_never_spawns(tmp_path, monkeypatch):
    source, auth, output, approval = approval_fixture(tmp_path, monkeypatch)
    approval["status"] = "pending"
    auth.write_text(json.dumps(approval))
    monkeypatch.setattr(launcher, "supervise", lambda *a: pytest.fail("must not dispatch"))
    with pytest.raises(ValueError, match="authorization"):
        launcher.launch(source, auth, output)
    assert not output.exists()
    assert not output.with_name(output.name + ".dispatch").exists()
    assert not (tmp_path / ".cf60-dispatch-consumed-authorizations").exists()


def test_failed_dispatch_preserves_evidence_and_cannot_reuse_id(tmp_path, monkeypatch):
    source, auth, output, approval = approval_fixture(tmp_path, monkeypatch)
    calls = []

    def failure(cmd, limit):
        calls.append(cmd)
        output.write_text("SYNTHETIC partial output: must preserve, never accept")
        return {"status": "timed_out", "cleanup_verified": True}

    monkeypatch.setattr(launcher, "supervise", failure)
    result = launcher.launch(source, auth, output)
    assert result["status"] == "timed_out" and "extract_sha256" not in result
    receipt = output.with_name(output.name + ".dispatch")
    assert (receipt / "intent.json").is_file()
    assert (receipt / "authorization.json").read_bytes() == auth.read_bytes()
    assert json.loads((receipt / "result.json").read_text())["status"] == "timed_out"
    assert output.read_text().startswith("SYNTHETIC partial")
    # Preserve the partial artifact and try another output with the same ID.
    renamed = tmp_path / "renamed.json"
    approval["output_path"] = str(renamed)
    auth.write_text(json.dumps(approval))
    with pytest.raises(FileExistsError):
        launcher.launch(source, auth, renamed)
    assert len(calls) == 1 and not renamed.exists()


def test_worker_without_release_does_not_even_open_approval(tmp_path):
    out = tmp_path / "unused"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(launcher.__file__)),
            "--worker",
            "--source",
            "absent-source",
            "--authorization",
            "absent-approval",
            "--out",
            str(out),
        ],
        input=b"",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )
    assert result.returncode == 2 and not result.stderr and not out.exists()


def test_real_supervised_synthetic_extraction_has_matching_receipt(tmp_path, monkeypatch):
    source, auth, output, approval = approval_fixture(tmp_path, monkeypatch)
    original = launcher.supervise

    def synthetic_worker(cmd, limit):
        # Explicit synthetic-only identity/revision at BOTH process boundaries.
        # Production CLI never has this override and the real source is not opened.
        snapshot = cmd[cmd.index("--authorization") + 1]
        code = (
            "from pathlib import Path; from scripts import extract_cf60_development as e; "
            f"e.SHA256={approval['source_sha256']!r}; e.revision=lambda: '1'*40; "
            f"p=Path({snapshot!r}); "
            f"e.run(Path({str(source)!r}),p,Path({str(output)!r}),approval_bytes=p.read_bytes())"
        )
        return original(command(code), limit)

    monkeypatch.setattr(launcher, "supervise", synthetic_worker)
    result = launcher.launch(source, auth, output)
    assert result["status"] == "succeeded" and result["cleanup_verified"]
    extract = json.loads(output.read_text())
    assert len(extract["rows"]) == 340
    assert extract["ingestion"]["approval_sha256"] == result["approval_sha256"]
    assert extract["extractor_code_sha256"] == launcher.extractor.code_pins()


def test_child_leaving_descendant_is_failed_and_tree_stopped(tmp_path):
    marker = tmp_path / "left.pid"
    code = (
        "import subprocess,pathlib; "
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        f"pathlib.Path({str(marker)!r}).write_text(str(p.pid))"
    )
    result = launcher.supervise(command(code), 5)
    assert result["status"] == "descendants_left_running"
    assert result["cleanup_verified"] and not alive(int(marker.read_text()))


@pytest.mark.parametrize("limit", [True, 0, -1, 121, float("inf"), float("nan")])
def test_invalid_deadlines_cannot_create_a_job(limit, monkeypatch):
    monkeypatch.setattr(launcher, "WindowsJob", lambda: pytest.fail("must not create job"))
    with pytest.raises(ValueError):
        launcher.supervise([], limit)


def test_job_creation_failure_is_fail_closed(monkeypatch):
    def fail():
        raise OSError("SYNTHETIC unavailable containment")

    monkeypatch.setattr(launcher, "WindowsJob", fail)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("must not spawn"))
    result = launcher.supervise([], 1)
    assert result["status"] == "supervision_failed"
    assert not result["released"] and result["cleanup_verified"]


def test_unverified_cleanup_cannot_be_success(monkeypatch):
    original = launcher.WindowsJob.stop

    def failed_receipt(self, grace_s=3):
        original(self, grace_s)
        raise TimeoutError("SYNTHETIC cleanup verification failure after actual stop")

    monkeypatch.setattr(launcher.WindowsJob, "stop", failed_receipt)
    result = launcher.supervise(command("sys.exit(0)"), 5)
    assert result["status"] == "cleanup_unverified" and not result["cleanup_verified"]
    assert not alive(result["pid"])
