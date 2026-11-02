"""Learned C/D inference adapters: reload, schedule, checked A fallback.

Private joblib binaries stay outside Git. Callers pass a local trusted path and
the expected SHA-256 (published development digests are recorded below). This
module never imports the reference solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.policies import greedy
from dc_sustainability.training.schedule import schedule_from_probabilities
from dc_sustainability.training.train import (
    FittedModel,
    SystemKind,
    bind_classifier,
    classifier_for_factory,
    load_artifact_bytes,
)
from dc_sustainability.verification.rules import assess_forecasts

# Published manager-host development digests from docs/handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md.
# Local tests use temporary artifacts; production receiving verifies these hashes.
PUBLISHED_DEVELOPMENT_SHA256: dict[SystemKind, str] = {
    "decision_tree_c": "7e9e5769771f045241317d976f142b936f328399df58b040f9bbf67ba77a8f0b",
    "random_forest_d": "37149e530ef8e026b08279bedae1dd95170f70c279dd59d566637f43df94cf6a",
}

_LEARNED_SYSTEMS = frozenset(PUBLISHED_DEVELOPMENT_SHA256)
_COVERAGE_REASONS = (
    ("beyond-horizon", lambda a, _: bool(a.beyond_horizon_slots)),
    ("future", lambda a, _: bool(a.future_issued_slots)),
    ("stale", lambda a, _: bool(a.stale_slots)),
    (
        "partial",
        lambda a, facts: bool(a.missing_slots) and bool(set(a.required_slots) & facts),
    ),
    ("missing", lambda a, _: bool(a.missing_slots)),
)


@dataclass(frozen=True)
class LearnedArtifact:
    """One frozen C/D model bound to its measured file digest."""

    path: Path
    system: SystemKind
    artifact_sha256: str
    fitted: FittedModel


def file_sha256(path: Path) -> str:
    """Hash the on-disk artifact bytes."""
    return sha256(path.read_bytes()).hexdigest()


def load_verified(path: Path, *, expected_sha256: str) -> LearnedArtifact:
    """Reload a joblib artifact only when its bytes match the expected digest."""
    data = Path(path).read_bytes()
    digest = sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"artifact digest mismatch: got {digest}, expected {expected_sha256}")
    fitted = load_artifact_bytes(data)
    return LearnedArtifact(
        path=path,
        system=fitted.spec.system,
        artifact_sha256=digest,
        fitted=fitted,
    )


def load_published_development(path: Path, *, system: SystemKind) -> LearnedArtifact:
    """Load a local copy that must match the published development SHA-256 for system."""
    expected = PUBLISHED_DEVELOPMENT_SHA256[system]
    artifact = load_verified(path, expected_sha256=expected)
    if artifact.system != system:
        raise ValueError(f"artifact system {artifact.system} does not match requested {system}")
    return artifact


def classifier_for(artifact: LearnedArtifact, *, decision_origin_utc: datetime):
    """TrainedPolicy-compatible factory bound to a verified artifact."""
    return classifier_for_factory(artifact.fitted, decision_origin_utc=decision_origin_utc)


def propose(
    visible_state: s.VisibleState,
    context: s.Context,
    *,
    system: SystemKind,
    artifact: LearnedArtifact,
    decision_time_utc: datetime,
    decision_origin_utc: datetime | None = None,
) -> s.PolicyOutput:
    """Propose with C/D probabilities, or checked greedy A when forecasts fail Q04 coverage."""
    if system not in _LEARNED_SYSTEMS:
        raise ValueError(f"unsupported learned system: {system}")
    if artifact.system != system:
        raise ValueError("artifact system does not match the requested learned system")
    if decision_origin_utc is not None:
        offset = timedelta(hours=visible_state.current_slot * visible_state.site.slot_hours)
        if (
            not isinstance(decision_origin_utc, datetime)
            or decision_origin_utc.utcoffset() != timedelta(0)
            or decision_origin_utc + offset != decision_time_utc
        ):
            raise ValueError("decision origin must match the trusted slot-to-UTC mapping")
    return propose_from_factory(
        visible_state,
        context,
        system=system,
        decision_time_utc=decision_time_utc,
        classifier_factory=lambda state, ctx: bind_classifier(
            artifact.fitted, state, ctx, decision_time_utc=decision_time_utc
        ),
    )


def propose_from_factory(
    visible_state: s.VisibleState,
    context: s.Context,
    *,
    system: SystemKind,
    decision_time_utc: datetime,
    classifier_factory,
) -> s.PolicyOutput:
    """Shared P05/E02 path; coverage fallback precedes scoring, errors propagate."""
    if system not in _LEARNED_SYSTEMS:
        raise ValueError(f"unsupported learned system: {system}")
    if not isinstance(decision_time_utc, datetime) or decision_time_utc.utcoffset() != timedelta(0):
        raise ValueError("an explicit trusted UTC decision time is required")

    visible_state = s.VisibleState.model_validate(
        visible_state.model_dump(mode="python"), strict=True
    )
    context = s.Context.model_validate(context.model_dump(mode="python"), strict=True)
    content = context.content
    snapshot = s.ConstraintSnapshot(
        snapshot_id=content.snapshot_id,
        site=content.site,
        constraints=content.constraints,
        sources=content.sources,
    )
    expected = s.Context.build(visible_state, snapshot, context.representation)
    if expected.content_hash != context.content_hash:
        raise ValueError("context does not match the visible decision state")
    reason = _forecast_gap_reason(visible_state, context, decision_time_utc)
    if reason is not None:
        base = greedy.propose(visible_state, context, system="greedy_a")
        return base.model_copy(
            update={
                "explanation": s.Explanation(
                    source="template",
                    summary=f"learned_fallback:{reason}",
                ),
            }
        )

    bound = classifier_factory(visible_state, context)
    return schedule_from_probabilities(visible_state, context, bound, system=system)


def _forecast_gap_reason(
    visible_state: s.VisibleState,
    context: s.Context,
    decision_time_utc: datetime,
) -> str | None:
    content = context.content
    snapshot = s.ConstraintSnapshot(
        snapshot_id=content.snapshot_id,
        site=content.site,
        constraints=content.constraints,
        sources=content.sources,
    )
    assessment = assess_forecasts(visible_state, snapshot, decision_time_utc=decision_time_utc)
    fact_slots = {fact.valid_slot for fact in visible_state.carbon_facts}
    return next(
        (label for label, matches in _COVERAGE_REASONS if matches(assessment, fact_slots)),
        None,
    )
