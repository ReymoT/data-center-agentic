"""The six experiment systems and whether this runner can execute each one yet.

Every system is registered so a run configuration can name it. A system that is not
available refuses with its reason; the runner never substitutes another system or a
placeholder output. The two model systems run only when the caller supplies explicit
model inputs (a provider and, for the agent, reviewed renderers); nothing here builds
them, so the CLI cannot reach a model.
"""

from dataclasses import dataclass
from typing import Literal

from dc_sustainability import schemas as s


@dataclass(frozen=True)
class SystemSpec:
    system: s.SystemId
    kind: Literal["deterministic", "trained", "model"]
    short: str  # used inside decision IDs
    available: bool
    reason: str = ""  # why it is not available yet

    @property
    def trials(self) -> bool:
        """Model systems repeat over trials; deterministic and trained systems run once."""
        return self.kind == "model"


SYSTEMS: dict[str, SystemSpec] = {
    spec.system: spec
    for spec in (
        SystemSpec("greedy_a", "deterministic", "ga", True),
        SystemSpec("greedy_b", "deterministic", "gb", True),
        SystemSpec(
            "decision_tree_c", "trained", "dt", False, "needs Edison's trained P04 artifact"
        ),
        SystemSpec(
            "random_forest_d", "trained", "rf", False, "needs Edison's trained P04 artifact"
        ),
        SystemSpec(
            "plain_llm",
            "model",
            "pl",
            False,
            "needs explicit model inputs: accepted A01 and a run authorization",
        ),
        SystemSpec(
            "agent",
            "model",
            "ag",
            False,
            "needs explicit model inputs: accepted A01 and a run authorization",
        ),
    )
}


def spec(system: str) -> SystemSpec:
    if system not in SYSTEMS:
        raise ValueError(f"unknown system {system!r}")
    return SYSTEMS[system]


def require_available(system: str, *, model_inputs: bool = False) -> SystemSpec:
    found = spec(system)
    if found.kind == "model" and model_inputs:
        return found
    if not found.available:
        raise NotImplementedError(f"{system} is not available in this runner: {found.reason}")
    return found
