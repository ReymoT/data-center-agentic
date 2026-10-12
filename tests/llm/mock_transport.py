"""Replay opaque provider outcomes offline without selecting an SDK or domain schema."""

from collections import deque
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class RecordedCall:
    """A test-only snapshot of arguments supplied to the fake callable."""

    args: tuple[object, ...]
    kwargs: dict[str, object]


class ScriptedTransport:
    """Return each scripted object or raise each scripted Exception exactly once.

    This callable is a test helper, not an adopted provider interface. Requests and
    responses remain opaque; callers adapt it to the eventual SDK/F02 boundary.
    Exhaustion raises AssertionError rather than returning an unscripted success.
    There is no network, delay, parsing, repair, retry, token or cost calculation.
    """

    def __init__(self, outcomes: Iterable[object]):
        self._outcomes = deque(
            item if isinstance(item, Exception) else deepcopy(item) for item in outcomes
        )
        self._calls: list[RecordedCall] = []

    def __call__(self, *args: object, **kwargs: object) -> object:
        self._calls.append(RecordedCall(deepcopy(args), deepcopy(kwargs)))
        if not self._outcomes:
            raise AssertionError(
                f"Unexpected provider call {self.attempt_count}: scripted outcomes exhausted"
            )
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return deepcopy(outcome)

    @property
    def calls(self) -> tuple[RecordedCall, ...]:
        """Return detached snapshots, including failed and unexpected attempts."""
        return tuple(deepcopy(self._calls))

    @property
    def attempt_count(self) -> int:
        return len(self._calls)

    @property
    def remaining_count(self) -> int:
        return len(self._outcomes)

    def assert_consumed(self) -> None:
        """Fail a test when a required scripted stage was never exercised."""
        if self._outcomes:
            raise AssertionError(f"{self.remaining_count} scripted provider outcomes were not used")
