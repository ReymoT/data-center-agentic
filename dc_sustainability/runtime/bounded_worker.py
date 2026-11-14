"""Gated Windows worker containment, up to 900 seconds plus separate cleanup.

Reuses the established Job Object release/cleanup algorithm. No model/source
operation occurs here. Callers authenticate permission and consume IDs first.
"""

import math
import subprocess
from time import monotonic

from dc_sustainability.runtime.windows_job import WindowsJob


def supervise(command, limit_s, *, cwd=None):
    """Run a stdin-gated child once; discard output and contain its descendants.

    Deadline starts before Popen. OS process creation itself is not interruptible;
    if it returns late, never release the child. Cleanup has a separate 3s budget.
    The child MUST wait for b'G' before doing any work or spawning descendants.
    """
    if type(limit_s) not in (int, float) or not math.isfinite(limit_s) or not 0 < limit_s <= 900:
        raise ValueError("wall deadline must be positive and at most 900 seconds")
    job, child = None, None
    started = monotonic()
    result = {"status": "failed", "released": False, "cleanup_verified": False}
    try:
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
        result["pid"] = child.pid
        job.assign(child.pid)
        remaining = limit_s - (monotonic() - started)
        if remaining <= 0:
            result["status"] = "timed_out_before_release"
        else:
            child.stdin.write(b"G")
            child.stdin.close()
            result["released"] = True
            try:
                child.wait(timeout=max(0, limit_s - (monotonic() - started)))
                result["returncode"] = child.returncode
                if monotonic() - started >= limit_s:
                    result["status"] = "timed_out"
                else:
                    result["status"] = "succeeded" if child.returncode == 0 else "failed"
                # A successful direct child must not leave background descendants.
                if not job.wait_empty(min(started + limit_s, monotonic() + 0.2)):
                    result["status"] = "descendants_left_running"
            except subprocess.TimeoutExpired:
                result["status"] = "timed_out"
    except KeyboardInterrupt:
        result["status"] = "interrupted"
    except Exception as exc:
        result["status"] = "supervision_failed"
        result["exception"] = type(exc).__name__  # no raw child/CSV output
    finally:
        result["elapsed_before_cleanup_s"] = monotonic() - started
        if result["status"] == "succeeded" and monotonic() - started >= limit_s:
            result["status"] = "timed_out"
        cleanup_deadline = monotonic() + 3
        try:
            if job is not None:
                job.stop()
            if child is not None:
                # Includes assign failure: gated/unassigned child is killed directly.
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=max(0, cleanup_deadline - monotonic()))
            result["cleanup_verified"] = True
        except Exception as exc:
            result["status"] = "cleanup_unverified"
            result["cleanup_exception"] = type(exc).__name__
        finally:
            if child is not None and child.stdin is not None:
                child.stdin.close()
            if job is not None:
                job.close()  # kill-on-close also applies if the supervisor crashes
        result["elapsed_including_cleanup_s"] = monotonic() - started
    return result
