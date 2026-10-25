"""Bounded graceful teardown for synthetic loopback HTTP tests, never production.

For these Content-Length-framed responses, wait for client EOF before sending FIN.
This avoids using a successful send or early write shutdown as delivery evidence.
The client still owns its original response/deadline/byte-limit assertions.
"""

import socket
import threading
import time
from http.server import ThreadingHTTPServer


class DrainingHTTPServer(ThreadingHTTPServer):
    drain_timeout = 10.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdown_started = threading.Event()
        self._shutdown_condition = threading.Condition()
        self.shutdown_outcomes = []

    def wait_for_shutdowns(self, count, timeout):
        with self._shutdown_condition:
            return self._shutdown_condition.wait_for(
                lambda: len(self.shutdown_outcomes) >= count, timeout=timeout
            )

    def shutdown_request(self, request):
        started = time.monotonic()
        deadline = started + self.drain_timeout
        outcome = "error"
        try:
            self.shutdown_started.set()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    outcome = "timeout"
                    break
                request.settimeout(remaining)
                if not request.recv(1024):
                    outcome = "peer_eof"
                    break
        except TimeoutError:
            outcome = "timeout"
        except OSError:
            # Expected for deliberately disconnected/reset synthetic clients.
            # Record it rather than inventing a successful graceful drain.
            outcome = "error"
        finally:
            try:
                request.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            self.close_request(request)
            with self._shutdown_condition:
                self.shutdown_outcomes.append(
                    {"outcome": outcome, "seconds": time.monotonic() - started}
                )
                self._shutdown_condition.notify_all()
