"""Collect development decision samples from Reimo's SchedulingSimulator.

Each sample is one policy-visible state and the Q07 feature rows for that state.
Labels are absent on purpose. Ved attaches certified selections later under O02.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from dc_sustainability import schemas as s
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.training.features import FeatureRow, candidate_features

_EPISODE_SLOTS = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS


@dataclass(frozen=True)
class CollectedDecision:
    """One development decision without any training label."""

    episode_id: str
    slot: int
    state_version: int
    state: s.VisibleState
    context: s.Context
    decision_time_utc: datetime
    rows: tuple[FeatureRow, ...]

    @property
    def candidate_keys(self) -> tuple[tuple[str, int], ...]:
        """Stable (job_id, start_slot) keys for later O02 label attachment."""
        return tuple((row.job_id, row.start_slot) for row in self.rows)


def collect_decisions(
    episode: s.PrivateEpisode,
    *,
    decision_time_utc: Callable[[int], datetime],
    approve: Callable[[s.VisibleState, s.Context], s.ApprovedActions],
    forecasts_by_slot: Mapping[int, tuple[s.CarbonForecast, ...]] | None = None,
    allow_completion_starts: bool = False,
) -> tuple[CollectedDecision, ...]:
    """Walk one private episode and emit unlabeled feature samples at every slot."""
    if not callable(decision_time_utc):
        raise TypeError("decision_time_utc must be a callable slot mapper")
    if not callable(approve):
        raise TypeError("approve must be a callable ApprovedActions producer")
    simulator = SchedulingSimulator(allow_completion_starts=allow_completion_starts)
    simulator.reset(episode, forecasts_by_slot=forecasts_by_slot)
    samples: list[CollectedDecision] = []
    for _ in range(_EPISODE_SLOTS):
        state = simulator.state()
        context = s.Context.build(state, episode.snapshot, representation="flat")
        decision_time = decision_time_utc(state.current_slot)
        if not isinstance(decision_time, datetime) or decision_time.utcoffset() != timedelta(0):
            raise ValueError("an explicit trusted UTC decision time is required")
        rows = candidate_features(state, context, decision_time_utc=decision_time)
        samples.append(
            CollectedDecision(
                episode_id=state.episode_id,
                slot=state.current_slot,
                state_version=state.state_version,
                state=state,
                context=context,
                decision_time_utc=decision_time,
                rows=rows,
            )
        )
        action = approve(state, context)
        if not isinstance(action, s.ApprovedActions):
            raise TypeError("approve must return ApprovedActions")
        simulator.step(action)
    return tuple(samples)
