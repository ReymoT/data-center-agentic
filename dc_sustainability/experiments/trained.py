"""E02-c: the trained C/D systems inside the runner, through P05 learned inference.

Nothing here trains a model. The caller loads each of Edison's P04 artifacts with
``policies.learned.load_verified`` (which hashes the exact bytes it deserializes)
and passes the resulting ``LearnedArtifact``. The runner checks that measured hash
and the artifact's own system against the frozen run config, then proposes through
``policies.learned.propose`` with the trusted slot-to-UTC decision time. That is the
one definition of C/D: P03 probabilities when forecasts cover the decision, or a
checked Greedy A plan, which ``execute_policy_output`` records as the fallback stage.
A policy error is a recorded failed output, never a silent substitute.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from dc_sustainability import schemas as s
from dc_sustainability.experiments.config import TrainedSettings
from dc_sustainability.policies import learned


@dataclass(frozen=True)
class TrainedPolicy:
    """One trained system: the verified artifact loaded by P05."""

    artifact: learned.LearnedArtifact

    @property
    def artifact_sha256(self) -> str:
        """The SHA256 measured over the bytes that were deserialized."""
        return self.artifact.artifact_sha256


@dataclass(frozen=True)
class TrainedInputs:
    policies: Mapping[str, TrainedPolicy]


def check_inputs(settings: TrainedSettings, inputs: TrainedInputs, systems) -> None:
    """Refuse trained inputs that do not match the frozen artifact hashes and systems."""
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
        policy = inputs.policies[system]
        if not isinstance(policy, TrainedPolicy) or not isinstance(
            policy.artifact, learned.LearnedArtifact
        ):
            raise ValueError(f"{system} needs a verified P05 LearnedArtifact")
        if policy.artifact.system != system:
            raise ValueError(f"{system} input holds a {policy.artifact.system} artifact")
        if policy.artifact_sha256 != digest:
            raise ValueError(f"{system} artifact differs from the hash frozen in the run config")


def propose(
    system: str,
    inputs: TrainedInputs,
    state: s.VisibleState,
    context: s.Context,
    *,
    decision_time_utc: datetime,
) -> s.PolicyOutput:
    """The trained system's own output for one decision; errors propagate to the caller."""
    return learned.propose(
        state,
        context,
        system=system,
        artifact=inputs.policies[system].artifact,
        decision_time_utc=decision_time_utc,
    )
