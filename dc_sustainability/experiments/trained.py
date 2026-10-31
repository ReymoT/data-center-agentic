"""E02-c: the trained C/D systems inside the runner, from explicit trained inputs.

Nothing here loads or trains a model. The caller supplies, for each trained system,
the SHA256 of Edison's P04 artifact and a function that returns that model's P03
classifier for one decision. The runner checks the hash against the frozen run
config, then proposes through P03's ``schedule_from_probabilities`` and executes
through the same ``execute_policy_output`` path as Greedy A/B: the real checker and
controller decide. A classifier error is a recorded failed output, never a fallback.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from dc_sustainability import schemas as s
from dc_sustainability.experiments.config import TrainedSettings
from dc_sustainability.training import schedule_from_probabilities


@dataclass(frozen=True)
class TrainedPolicy:
    """One trained system: its artifact hash and a per-decision classifier factory.

    ``classifier_for(state, context)`` returns an object with
    ``selection_probability(job, start_slot) -> float in [0, 1]`` (the P03 contract).
    It sees only the policy-visible state and flat context.
    """

    artifact_sha256: str
    classifier_for: Callable[[s.VisibleState, s.Context], object]


@dataclass(frozen=True)
class TrainedInputs:
    policies: Mapping[str, TrainedPolicy]


def check_inputs(settings: TrainedSettings, inputs: TrainedInputs, systems) -> None:
    """Refuse trained inputs that do not match the frozen artifact hashes."""
    expected = {system for system, _ in settings.artifacts if system in systems}
    supplied = set(inputs.policies)
    if supplied != expected:
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        raise ValueError(
            f"trained inputs must match listed systems; missing={missing}, extra={extra}"
        )
    for system, digest in settings.artifacts:
        if system not in systems:
            continue
        policy = inputs.policies.get(system)
        if policy.artifact_sha256 != digest:
            raise ValueError(f"{system} artifact differs from the hash frozen in the run config")
        if not callable(policy.classifier_for):
            raise ValueError(f"{system} classifier_for must be callable")


def propose(
    system: str, inputs: TrainedInputs, state: s.VisibleState, context: s.Context
) -> s.PolicyOutput:
    """The trained system's own output for one decision; errors propagate to the caller."""
    classifier = inputs.policies[system].classifier_for(state, context)
    return schedule_from_probabilities(state, context, classifier, system=system)
