"""Q10 deterministic selection of decision slots for the manual explanation review.

Implements the sampling frame agreed in issue #22 (Ved's A3 rule, confirmed by Nisha and
accepted by Matty). Whether a slot can be selected depends only on exogenous job timing:
never on capacity, forecasts, either system's outputs or its actual queue. Selection is
made from the frozen manifest before any held-out output is opened, every selected pair
is kept (failures and one-sided no-ops included), and a shortfall is reported, never
topped up.

The separate abstention-boundary stratum for impossible-on-arrival jobs (arrival
option B) is Nisha's #22 proposal, pending Ved's agreement. It is kept apart from the
primary sample and is never used to replace or fill primary pairs.
"""

import dataclasses
import platform
import random
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from dc_sustainability import schemas as s

ALGORITHM = "q10-temporal-window-v1"
GENERATOR = "python random.Random (MT19937)"
SAMPLING_SEED = 20261019
ANALYSIS_SEED = 20261020  # paired bootstrap; frozen with the selection, used later
BOUNDARY_SEED = 20261021  # only if the boundary stratum exceeds BOUNDARY_CAP
SLOTS_PER_EPISODE = 2
TRIALS = (0, 1, 2)
BOUNDARY_CAP = 30
LAST_DECISION_SLOT = s.PROPOSED_DECISION_SLOTS - 1  # 23
END = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS  # 30
REVIEWED_SYSTEMS = ("agent", "plain_llm")


def latest_start(job: s.Job) -> int:
    """Latest start that still finishes by the deadline and boundary 30 (arrival if fixed)."""
    latest = min(job.deadline_slot, END) - job.duration_slots
    return latest if job.flexible else min(latest, job.arrival_slot)


def eligible_slots(episode: s.PrivateEpisode) -> tuple[int, ...]:
    """Slots 0-23 inside at least one job's window ``arrival_slot <= t <= latest_start``."""
    slots: set[int] = set()
    for private in episode.jobs:
        job = private.job
        slots.update(range(job.arrival_slot, min(latest_start(job), LAST_DECISION_SLOT) + 1))
    return tuple(sorted(slots))


def impossible_arrival_slots(episode: s.PrivateEpisode) -> tuple[int, ...]:
    """Arrival slots (0-23) of jobs with no permissible start window at all, by timing only."""
    return tuple(
        sorted(
            {
                p.job.arrival_slot
                for p in episode.jobs
                if p.job.arrival_slot <= LAST_DECISION_SLOT
                and latest_start(p.job) < p.job.arrival_slot
            }
        )
    )


def stratum(episode: s.PrivateEpisode) -> str:
    return f"{episode.scenario_id}|{episode.forecast_visibility}"


@dataclass(frozen=True)
class Selection:
    episode_id: str
    stratum: str
    slot: int
    trial: int


@dataclass(frozen=True)
class SamplingRecord:
    """The private, frozen selection record: what was chosen, how, and what fell short."""

    algorithm: str
    generator: str
    python_version: str
    seed: int
    analysis_seed: int
    manifest_hash: str  # over the episodes' canonical hashes, in episode-ID order
    split: str
    target: int
    eligible: Mapping[str, tuple[int, ...]]  # episode ID -> eligible slots
    selections: tuple[Selection, ...]  # primary sample, by episode ID then slot
    shortfall: Mapping[str, int]  # episode ID -> slots it could not supply
    counts_by_trial: Mapping[int, int]
    counts_by_stratum: Mapping[str, int]
    boundary_status: str
    boundary_eligible: int  # impossible-on-arrival slots in the whole manifest
    boundary: tuple[Selection, ...]  # separate stratum, reported apart

    @property
    def achieved(self) -> int:
        return len(self.selections)

    def to_jsonable(self) -> dict:
        data = dataclasses.asdict(self)
        data["counts_by_trial"] = {str(k): v for k, v in self.counts_by_trial.items()}
        data["achieved"] = self.achieved
        return data


def _assign_trials(items: list[tuple[str, str, int]], rng, trials) -> list[Selection]:
    """Rotate trials through each stratum in turn, so counts differ by at most one both
    within every stratum and overall; the order inside a stratum comes from ``rng``."""
    out, offset = [], 0
    for name in sorted({item[1] for item in items}):
        group = [item for item in items if item[1] == name]
        rng.shuffle(group)
        for i, (episode_id, _, slot) in enumerate(group):
            out.append(Selection(episode_id, name, slot, trials[(offset + i) % len(trials)]))
        offset += len(group)
    return sorted(out, key=lambda x: (x.episode_id, x.slot))


def select(
    episodes: Iterable[s.PrivateEpisode],
    *,
    seed: int = SAMPLING_SEED,
    trials: tuple[int, ...] = TRIALS,
) -> SamplingRecord:
    """Select two eligible slots per episode and balance them over trials and strata.

    Input order does not matter: episodes are processed by (stratum, episode ID).
    """
    episodes = [
        s.PrivateEpisode.model_validate(e.model_dump(mode="python", warnings="none"), strict=True)
        for e in episodes
    ]
    ids = [e.episode_id for e in episodes]
    if not episodes or len(ids) != len(set(ids)):
        raise ValueError("the manifest needs at least one episode and unique episode IDs")
    if len({e.split for e in episodes}) != 1:
        raise ValueError("the manifest mixes splits")
    if any(
        (e.n_decision_slots, e.n_completion_slots)
        != (s.PROPOSED_DECISION_SLOTS, s.PROPOSED_COMPLETION_SLOTS)
        for e in episodes
    ):
        raise ValueError("selection requires the proposal's 24 decision and 6 completion slots")
    if not trials or len(set(trials)) != len(trials):
        raise ValueError("trials must be distinct")

    rng = random.Random(seed)
    episodes.sort(key=lambda e: (stratum(e), e.episode_id))
    eligible, shortfall, chosen = {}, {}, []
    for episode in episodes:
        slots = eligible_slots(episode)
        eligible[episode.episode_id] = slots
        k = min(SLOTS_PER_EPISODE, len(slots))
        if k < SLOTS_PER_EPISODE:
            shortfall[episode.episode_id] = SLOTS_PER_EPISODE - k
        for slot in sorted(rng.sample(slots, k)):
            chosen.append((episode.episode_id, stratum(episode), slot))
    selections = _assign_trials(chosen, rng, trials)

    # Separate abstention-boundary stratum: a census in canonical order, trials rotated.
    census = [
        (episode.episode_id, stratum(episode), slot)
        for episode in episodes
        for slot in impossible_arrival_slots(episode)
    ]
    kept = census
    if len(census) > BOUNDARY_CAP:
        kept = sorted(random.Random(BOUNDARY_SEED).sample(census, BOUNDARY_CAP))
    boundary = tuple(
        Selection(e, name, slot, trials[i % len(trials)]) for i, (e, name, slot) in enumerate(kept)
    )

    return SamplingRecord(
        algorithm=ALGORITHM,
        generator=GENERATOR,
        python_version=platform.python_version(),
        seed=seed,
        analysis_seed=ANALYSIS_SEED,
        manifest_hash=s.sha256_hex(
            [e.canonical_hash() for e in sorted(episodes, key=lambda e: e.episode_id)]
        ),
        split=episodes[0].split,
        target=SLOTS_PER_EPISODE * len(episodes),
        eligible=dict(sorted(eligible.items())),
        selections=tuple(selections),
        shortfall=dict(sorted(shortfall.items())),
        counts_by_trial={t: sum(x.trial == t for x in selections) for t in trials},
        counts_by_stratum=dict(sorted(Counter(x.stratum for x in selections).items())),
        boundary_status="proposed in #22, pending Ved; reported separately",
        boundary_eligible=len(census),
        boundary=boundary,
    )


@dataclass(frozen=True)
class PairRecord:
    """A selected pair after the run: kept whatever happened, with both actual queues."""

    selection: Selection
    queue_counts: Mapping[str, int]  # system -> waiting jobs in its actual state
    state_hashes: Mapping[str, str]  # system -> canonical hash of that state
    not_applicable: tuple[str, ...]  # systems whose queue was empty: no-op, counted, unrated

    @property
    def both_nonempty(self) -> bool:
        return not self.not_applicable


def pair_record(selection: Selection, states: Mapping[str, s.VisibleState]) -> PairRecord:
    """Record both systems' actual states for a selected pair. An empty queue does not
    remove the pair; that side is marked not applicable."""
    if set(states) != set(REVIEWED_SYSTEMS):
        raise ValueError(f"a pair needs exactly the states of {REVIEWED_SYSTEMS}")
    for system, state in states.items():
        if (state.episode_id, state.current_slot) != (selection.episode_id, selection.slot):
            raise ValueError(f"the {system} state is not the selected episode and slot")
    systems = sorted(states)
    return PairRecord(
        selection=selection,
        queue_counts={k: len(states[k].waiting_jobs) for k in systems},
        state_hashes={k: states[k].canonical_hash() for k in systems},
        not_applicable=tuple(k for k in systems if not states[k].waiting_jobs),
    )
