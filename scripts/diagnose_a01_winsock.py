"""Read-only TCP_INFO_v0 around four original synthetic HTTP tests, once."""

import argparse
import ctypes
import hashlib
import http.client
import json
import platform
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pytest  # noqa: E402

# Microsoft mstcpip.h: _WSAIORW(IOC_VENDOR, 39); version DWORD = 0.
SIO_TCP_INFO = 0xD8000027
U32 = ctypes.c_uint32
U64 = ctypes.c_uint64
U8 = ctypes.c_ubyte


class TCPInfo(ctypes.Structure):
    _fields_ = [
        ("State", U32),
        ("Mss", U32),
        ("ConnectionTimeMs", U64),
        ("TimestampsEnabled", U8),
        ("RttUs", U32),
        ("MinRttUs", U32),
        ("BytesInFlight", U32),
        ("Cwnd", U32),
        ("SndWnd", U32),
        ("RcvWnd", U32),
        ("RcvBuf", U32),
        ("BytesOut", U64),
        ("BytesIn", U64),
        ("BytesReordered", U32),
        ("BytesRetrans", U32),
        ("FastRetrans", U32),
        ("DupAcksIn", U32),
        ("TimeoutEpisodes", U32),
        ("SynRetrans", U8),
    ]


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("this optional diagnostic requires Windows Winsock")
    assert ctypes.sizeof(TCPInfo) == 88
    assert TCPInfo.BytesOut.offset == 48 and TCPInfo.BytesIn.offset == 56
    api = ctypes.WinDLL("Ws2_32.dll")
    api.WSAIoctl.argtypes = [
        ctypes.c_size_t,
        U32,
        ctypes.c_void_p,
        U32,
        ctypes.c_void_p,
        U32,
        ctypes.POINTER(U32),
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    api.WSAIoctl.restype = ctypes.c_int
    api.WSAGetLastError.argtypes = []
    api.WSAGetLastError.restype = ctypes.c_int
    events, tests = [], []
    lock = threading.Lock()
    started = time.monotonic()
    current = None
    original_read = http.client.HTTPResponse.read1
    original_send = socket.socket.sendall
    original_shutdown = socket.socket.shutdown

    def snapshot(sock):
        if sock is None:
            return {"unavailable": "response socket is absent"}
        result = {}
        try:
            result["local"] = sock.getsockname()
            result["peer"] = sock.getpeername()
            result["tcp_nodelay"] = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
            result["send_buffer"] = sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
            result["receive_buffer"] = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
            linger = sock.getsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 4)
            result["linger_on"] = int.from_bytes(linger[:2], "little")
            result["linger_seconds"] = int.from_bytes(linger[2:], "little")
            version, returned, info = U32(0), U32(), TCPInfo()
            code = api.WSAIoctl(
                sock.fileno(),
                SIO_TCP_INFO,
                ctypes.byref(version),
                4,
                ctypes.byref(info),
                ctypes.sizeof(info),
                ctypes.byref(returned),
                None,
                None,
            )
            result["ioctl_result"] = code
            result["returned_bytes"] = returned.value
            if code != 0:
                result["winsock_error"] = api.WSAGetLastError()
            elif returned.value != ctypes.sizeof(info):
                result["layout_error"] = "TCP_INFO_v0 returned size differs from 88"
            else:
                result["tcp"] = {name: getattr(info, name) for name, _ in info._fields_}
        except (OSError, ValueError) as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    def record(kind, sock=None, **fields):
        entry = {"event": kind, "test": current, "seconds": time.monotonic() - started}
        if sock is not None:
            entry["snapshot"] = snapshot(sock)
        entry.update(fields)
        with lock:
            events.append(entry)

    def read(response, size=-1):
        sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
        before = response.length
        record("read_start", sock, remaining=before)
        try:
            value = original_read(response, size)
        except Exception as exc:
            record("read_error", sock, remaining=response.length, error=str(exc))
            raise
        record("read_returned", sock, bytes=len(value), remaining=response.length)
        return value

    def send(sock, value, *positional, **keywords):
        observed = len(value) > 5000
        if observed:
            record("server_body_send_start", sock, bytes=len(value))
        try:
            result = original_send(sock, value, *positional, **keywords)
        except Exception as exc:
            if observed:
                record("server_body_send_error", sock, error=str(exc))
            raise
        if observed:
            record("server_body_send_returned", sock, bytes=len(value))
        return result

    def shutdown(sock, how):
        record("shutdown_start", sock, how=how)
        try:
            result = original_shutdown(sock, how)
        except Exception as exc:
            record("shutdown_error", error=str(exc), how=how)
            raise
        record("shutdown_returned", sock, how=how)
        return result

    class Identity:
        def pytest_runtest_setup(self, item):
            nonlocal current
            current = item.nodeid
            record("test_start")

        def pytest_runtest_logreport(self, report):
            if report.when == "call":
                tests.append({"test": report.nodeid, "outcome": report.outcome})

    report = {
        "evidence_kind": "read_only_winsock_tcp_info_original_test_observation",
        "python": sys.version,
        "platform": platform.platform(),
        "model_calls": 0,
        "tcp_info_v0_size": ctypes.sizeof(TCPInfo),
        "field_offsets": {name: getattr(TCPInfo, name).offset for name, _ in TCPInfo._fields_},
        "source_sha256_lf": digest(Path(__file__)),
        "provider_sha256_lf": digest(ROOT / "dc_sustainability/llm/provider.py"),
        "fixture_sha256_lf": digest(ROOT / "tests/llm/test_ollama_provider.py"),
        "observations": events,
        "test_results": tests,
        "completed": False,
        "limits": "Observer changes timing. TCP counters are not packet capture or proof of "
        "application delivery/root cause. API errors/unavailable snapshots retained. "
        "SO_ERROR is not read because reading error state could consume it. "
        "No settings, tests, assertions, payloads or deadlines changed; four cases once.",
        "sources": [
            "https://learn.microsoft.com/en-us/windows/win32/winsock/sio-tcp-info",
            "https://learn.microsoft.com/en-us/windows/win32/api/mstcpip/ns-mstcpip-tcp_info_v0",
            "https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/shared/mstcpip.h",
        ],
    }
    # Reserve before monkeypatches or measurement. Previous evidence cannot be erased.
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        try:
            http.client.HTTPResponse.read1 = read
            socket.socket.sendall = send
            socket.socket.shutdown = shutdown
            target = str(ROOT / "tests/llm/test_ollama_provider.py")
            code = int(
                pytest.main(
                    [
                        target + "::test_deep_json_failure_is_recorded_and_exhausts_run_budget",
                        "-q",
                        "--tb=short",
                    ],
                    plugins=[Identity()],
                )
            )
            report["pytest_exit_code"] = code
            report["completed"] = len(tests) == 4
        finally:
            http.client.HTTPResponse.read1 = original_read
            socket.socket.sendall = original_send
            socket.socket.shutdown = original_shutdown
            json.dump(report, handle, indent=2)
            handle.write("\n")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
