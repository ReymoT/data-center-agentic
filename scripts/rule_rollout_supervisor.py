"""Contained, stdin-gated offline worker with time/output stop monitoring.

No CLI and no research authority: the caller authenticates an exact single-use
request first. Output is a stop threshold, not a filesystem quota; writes may
overshoot between observations. Cleanup has a separate three-second allowance.
"""

import math
import stat
import subprocess
from pathlib import Path
from time import monotonic

from dc_sustainability.runtime.windows_job import WindowsJob


def output_bytes(root, *, deadline=None):
    def check_time():
        if deadline is not None and monotonic() >= deadline:
            raise TimeoutError("output inventory deadline reached")

    check_time()
    root = Path(root)
    if any(p.is_symlink() or p.is_junction() for p in (root, *root.parents)):
        raise ValueError("linked output refused")
    total, count = 0, 0
    if not root.exists():
        return 0
    for item in root.rglob("*"):
        check_time()
        count += 1
        if count > 100000:
            raise ValueError("unsafe or excessive output inventory")
        try:
            info = item.lstat()
        except FileNotFoundError:
            # Exclusive publication links a completed temp then unlinks its temp
            # name. A disappearing entry is not a supervision failure. The next
            # periodic scan and the mandatory exit scan observe retained names.
            check_time()
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("unsafe or excessive output inventory")
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
        check_time()
    return total


def supervise(command, limit_s, *, output, limit_bytes, cwd, deadline=None):
    if type(limit_s) not in (int, float) or not math.isfinite(limit_s) or not 0 < limit_s <= 900:
        raise ValueError("positive deadline up to 900 seconds required")
    if type(limit_bytes) is not int or not 0 < limit_bytes <= 256 * 1024 * 1024:
        raise ValueError("positive output stop threshold up to 256 MiB required")
    started, job, child = monotonic(), None, None
    deadline = min(started + limit_s, deadline) if deadline is not None else started + limit_s
    if not math.isfinite(deadline) or deadline <= started:
        raise ValueError("expired or invalid absolute deadline")
    next_scan = started
    result = {"status": "failed", "released": False, "cleanup_verified": False}
    try:
        output_bytes(output, deadline=deadline)
        job = WindowsJob()
        child = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        job.assign(child.pid)
        if monotonic() >= deadline:
            result["status"] = "timed_out_before_release"
        else:
            child.stdin.write(b"G")
            child.stdin.close()
            result["released"] = True
            while True:
                if monotonic() >= deadline:
                    result["status"] = "timed_out"
                    break
                if monotonic() >= next_scan or child.poll() is not None:
                    size = output_bytes(output, deadline=deadline)
                    result["observed_output_bytes"] = size
                    next_scan = monotonic() + 1
                    if size > limit_bytes:
                        result["status"] = "output_limit"
                        break
                if child.poll() is not None:
                    result["returncode"] = child.returncode
                    result["status"] = "succeeded" if child.returncode == 0 else "failed"
                    if not job.wait_empty(min(deadline, monotonic() + 0.2)):
                        result["status"] = "descendants_left_running"
                    break
                try:
                    child.wait(timeout=min(0.1, max(0.001, deadline - monotonic())))
                except subprocess.TimeoutExpired:
                    pass
    except TimeoutError as exc:
        result["status"] = "timed_out"
        result["message"] = str(exc)
    except BaseException as exc:
        result["status"] = "supervision_failed"
        result["exception"] = type(exc).__name__
        result["message"] = str(exc)[:2000]
    finally:
        result["elapsed_before_cleanup_s"] = monotonic() - started
        if result["status"] == "succeeded" and monotonic() >= deadline:
            result["status"] = "timed_out"
        deadline = monotonic() + 3
        try:
            if job is not None:
                job.stop()
                result["cleanup_verified"] = job.wait_empty(deadline)
                job.close()
            if child is not None:
                child.wait(timeout=max(0.001, deadline - monotonic()))
        except BaseException:
            result["cleanup_verified"] = False
        result["elapsed_total_s"] = monotonic() - started
    return result
