"""Windows process-tree containment; no source, model or approval operations.

See https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects .
The caller must gate the child until assign() succeeds. No breakaway is enabled.
"""

import ctypes as c
import os
import time
from ctypes import wintypes as w


class BasicLimits(c.Structure):
    _fields_ = [
        ("process_time", c.c_int64),
        ("job_time", c.c_int64),
        ("flags", w.DWORD),
        ("min_working", c.c_size_t),
        ("max_working", c.c_size_t),
        ("active_limit", w.DWORD),
        ("affinity", c.c_size_t),
        ("priority", w.DWORD),
        ("scheduling", w.DWORD),
    ]


class IoCounters(c.Structure):
    _fields_ = [
        (name, c.c_uint64)
        for name in (
            "read_ops",
            "write_ops",
            "other_ops",
            "read_bytes",
            "write_bytes",
            "other_bytes",
        )
    ]


class ExtendedLimits(c.Structure):
    _fields_ = [
        ("basic", BasicLimits),
        ("io", IoCounters),
        ("process_memory", c.c_size_t),
        ("job_memory", c.c_size_t),
        ("peak_process_memory", c.c_size_t),
        ("peak_job_memory", c.c_size_t),
    ]


class Accounting(c.Structure):
    _fields_ = [
        ("user", c.c_int64),
        ("kernel", c.c_int64),
        ("period_user", c.c_int64),
        ("period_kernel", c.c_int64),
        ("faults", w.DWORD),
        ("total", w.DWORD),
        ("active", w.DWORD),
        ("terminated", w.DWORD),
    ]


class WindowsJob:
    def __init__(self):
        if os.name != "nt":
            raise OSError("CF60 hard-timeout launcher requires Windows")
        self.api = c.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([c.c_void_p, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
            "QueryInformationJobObject": (
                [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p],
                w.BOOL,
            ),
            "CloseHandle": ([w.HANDLE], w.BOOL),
            "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise c.WinError(c.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
            error = c.WinError(c.get_last_error())
            self.close()
            raise error

    def assign(self, pid):
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE, per AssignProcessToJobObject.
        process = self.api.OpenProcess(0x0100 | 0x0001, False, pid)
        if not process:
            raise c.WinError(c.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise c.WinError(c.get_last_error())
        finally:
            self.api.CloseHandle(process)

    def active(self):
        info = Accounting()
        if not self.api.QueryInformationJobObject(
            self.handle, 1, c.byref(info), c.sizeof(info), None
        ):
            raise c.WinError(c.get_last_error())
        return info.active

    def wait_empty(self, deadline):
        while self.active():
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return True

    def stop(self, grace_s=3):
        deadline = time.monotonic() + grace_s
        # Keep synchronization handles BEFORE termination: job accounting may reach
        # zero before the corresponding process objects become signaled.
        buffer = c.create_string_buffer(8 + 128 * c.sizeof(c.c_size_t))
        if not self.api.QueryInformationJobObject(self.handle, 3, buffer, len(buffer), None):
            raise c.WinError(c.get_last_error())
        count = w.DWORD.from_buffer(buffer, 4).value
        handles = []
        try:
            for index in range(count):
                pid = c.c_size_t.from_buffer(buffer, 8 + index * c.sizeof(c.c_size_t)).value
                handle = self.api.OpenProcess(0x100000, False, pid)
                if handle:
                    handles.append(handle)
                elif c.get_last_error() != 87:  # ERROR_INVALID_PARAMETER: already gone
                    raise c.WinError(c.get_last_error())
            if not self.api.TerminateJobObject(self.handle, 1):
                raise c.WinError(c.get_last_error())
            for handle in handles:
                remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
                if self.api.WaitForSingleObject(handle, remaining_ms) != 0:
                    raise TimeoutError("process exit unverified")
            if not self.wait_empty(deadline):
                raise TimeoutError("process-tree cleanup unverified")
        finally:
            for handle in handles:
                self.api.CloseHandle(handle)

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            if not self.api.CloseHandle(handle):
                raise c.WinError(c.get_last_error())
