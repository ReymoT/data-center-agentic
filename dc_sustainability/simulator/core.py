"""Deterministic S01 transitions; approval authority stays with the runtime gate."""

from dataclasses import dataclass
from typing import Mapping

from dc_sustainability.schemas import (
    ApprovedActions,
    CarbonForecast,
    CompletedJobView,
    Context,
    EpisodeResult,
    EpisodeTotals,
    PrivateEpisode,
    RunningJobView,
    SlotRecord,
    VisibleState,
)


@dataclass(frozen=True)
class Transition:
    """Local diagnostic, not a shared contract or independent feasibility verdict."""

    slot: SlotRecord
    rejection: str | None
    missed_job_ids: tuple[str, ...]
    nonflexible_violation_ids: tuple[str, ...]


class SchedulingSimulator:
    """Trusted, single-run simulator. Callers must serialize reset/state/step.

    ApprovedActions is a trusted runtime capability, not cryptographic proof of approval.
    Arbitrary Plan/dict inputs are rejected. This class does not issue approvals.
    Q01 permits starts only in slots 0–23; slots 24–29 drain running work.
    """

    def __init__(self, *, allow_completion_starts: bool):
        if type(allow_completion_starts) is not bool:
            raise ValueError("completion-start choice must be explicit Boolean")
        if allow_completion_starts:
            raise ValueError("Q01 forbids allow_completion_starts=True; use False")
        self._episode = None

    def reset(
        self,
        episode: PrivateEpisode,
        *,
        forecasts_by_slot: Mapping[int, tuple[CarbonForecast, ...]] | None = None,
    ) -> VisibleState:
        """Reset atomically. Forecast issuance/projection is explicit caller input (Q04).

        Omitted forecasts mean unavailable evidence, never conversion of private actuals.
        """
        if not isinstance(episode, PrivateEpisode):
            raise ValueError("reset requires PrivateEpisode")
        episode = PrivateEpisode.model_validate(episode.model_dump())
        if (episode.n_decision_slots, episode.n_completion_slots) != (24, 6):
            raise ValueError("S01 requires 24 decision and six completion slots")
        capacity = episode.snapshot.capacity_kw
        if episode.snapshot.site.background_kw > capacity:
            raise ValueError("background exceeds site capacity")
        if episode.snapshot.site.slot_hours != 1:
            raise ValueError("S01 uses hourly slots")
        jobs = {p.job.job_id: p.job for p in episode.jobs}
        if any(j.arrival_slot >= 18 or j.deadline_slot > 30 for j in jobs.values()):
            raise ValueError("arrivals must precede 18 and deadlines must not exceed 30")
        for constraint in episode.snapshot.constraints:
            for job_id in constraint.applies_to_jobs:
                if job_id not in jobs:
                    raise ValueError("constraint references unknown job")
                job = jobs[job_id]
                expected = {
                    "arrival": job.arrival_slot,
                    "deadline": job.deadline_slot,
                    "nonflexible": job.arrival_slot,
                }.get(constraint.constraint_type)
                if expected is not None and (
                    constraint.limit_value != expected
                    or (constraint.constraint_type == "nonflexible" and job.flexible)
                ):
                    raise ValueError("constraint conflicts with job")
        forecasts = {}
        for slot, facts in (forecasts_by_slot or {}).items():
            if type(slot) is not int or not 0 <= slot < 30:
                raise ValueError("forecast decision slot outside episode")
            facts = tuple(CarbonForecast.model_validate(f.model_dump()) for f in facts)
            if episode.forecast_visibility == "withheld" and facts:
                raise ValueError("withheld episode cannot expose forecasts")
            view = VisibleState.from_snapshot(
                episode.snapshot,
                episode_id=episode.episode_id,
                current_slot=slot,
                state_version=slot,
                carbon_facts=facts,
            )
            Context.build(view, episode.snapshot, representation="flat")
            forecasts[slot] = facts
        self._episode = episode
        self._jobs = jobs
        self._forecasts = forecasts
        self._slot = 0
        self._running = {}
        self._completed = {}
        self._missed = set()
        self._history = []
        self._mark_missed()
        return self.state()

    def _require_reset(self):
        if self._episode is None:
            raise RuntimeError("reset must be called first")

    def _mark_missed(self):
        new = []
        for job_id, job in self._jobs.items():
            if job.arrival_slot > self._slot or job_id in (
                self._running.keys() | self._completed.keys() | self._missed
            ):
                continue
            latest = min(job.deadline_slot, 30) - job.duration_slots
            latest = min(latest, 23)
            if not job.flexible:
                latest = min(latest, job.arrival_slot)
            # Option B exposes even impossible arrivals for their arrival decision.
            # Start validation still rejects them; ordinary expiry timing is unchanged.
            if self._slot > latest and self._slot > job.arrival_slot:
                self._missed.add(job_id)
                new.append(job_id)
        return tuple(sorted(new))

    def state(self) -> VisibleState:
        self._require_reset()
        facts = self._forecasts.get(self._slot, ())
        present = {f.valid_slot for f in facts}
        return VisibleState.from_snapshot(
            self._episode.snapshot,
            episode_id=self._episode.episode_id,
            current_slot=self._slot,
            state_version=self._slot,
            waiting_jobs=tuple(
                j
                for jid, j in sorted(self._jobs.items())
                if j.arrival_slot <= self._slot
                and jid not in self._running
                and jid not in self._completed
                and jid not in self._missed
            ),
            running_jobs=tuple(self._running[k] for k in sorted(self._running)),
            completed_jobs=tuple(self._completed[k] for k in sorted(self._completed)),
            missed_job_ids=tuple(sorted(self._missed)),
            carbon_facts=facts,
            missing_carbon_slots=tuple(
                s for s in range(self._slot, min(self._slot + 24, 30)) if s not in present
            ),
        )

    @property
    def history(self) -> tuple[Transition, ...]:
        self._require_reset()
        return tuple(self._history)

    def step(self, approved_starts: ApprovedActions) -> Transition:
        """Reject the whole batch on error, then advance existing work exactly one slot."""
        self._require_reset()
        if self._slot >= 30:
            raise RuntimeError("episode is finished")
        starts = []
        rejection = None
        try:
            if not isinstance(approved_starts, ApprovedActions):
                raise ValueError("requires runtime-approved ApprovedActions")
            action = ApprovedActions.model_validate(approved_starts.model_dump())
            if (action.episode_id, action.slot, action.state_version) != (
                self._episode.episode_id,
                self._slot,
                self._slot,
            ):
                raise ValueError("action episode/slot/version mismatch")
            if action.starts and self._slot >= 24:
                raise ValueError("Q01 permits new starts only in slots 0–23")
            waiting = {j.job_id: j for j in self.state().waiting_jobs}
            for start in action.starts:
                job = waiting.get(start.job_id)
                if job is None:
                    raise ValueError("start does not identify a waiting job")
                if self._slot + job.duration_slots > min(job.deadline_slot, 30):
                    raise ValueError("start exceeds deadline or episode end")
                if not job.flexible and self._slot != job.arrival_slot:
                    raise ValueError("nonflexible start must equal arrival")
                starts.append(RunningJobView(job=job, start_slot=self._slot))
            for slot in range(self._slot, 30):
                load = self._episode.snapshot.site.background_kw + sum(
                    r.job.power_kw
                    for r in (*self._running.values(), *starts)
                    if r.start_slot <= slot < r.end_slot
                )
                if load > self._episode.snapshot.capacity_kw:
                    raise ValueError("start exceeds IT capacity")
        except (ValueError, TypeError, AttributeError) as exc:
            rejection = str(exc)
            starts = []
        for running in starts:
            self._running[running.job.job_id] = running
        completed = tuple(
            sorted(jid for jid, r in self._running.items() if r.end_slot == self._slot + 1)
        )
        record = SlotRecord(
            slot=self._slot,
            phase="decision" if self._slot < 24 else "completion",
            job_load_kw=sum(r.job.power_kw for r in self._running.values()),
            background_load_kw=self._episode.snapshot.site.background_kw,
            started_job_ids=tuple(sorted(r.job.job_id for r in starts)),
            running_job_ids=tuple(sorted(self._running)),
            completed_job_ids=completed,
        )
        for jid in completed:
            running = self._running.pop(jid)
            self._completed[jid] = CompletedJobView(
                job_id=jid, start_slot=running.start_slot, end_slot=running.end_slot
            )
        self._slot += 1
        missed = self._mark_missed()
        transition = Transition(
            slot=record,
            rejection=rejection,
            missed_job_ids=missed,
            nonflexible_violation_ids=tuple(j for j in missed if not self._jobs[j].flexible),
        )
        self._history.append(transition)
        return transition

    def result(self, *, run_id: str, system: str) -> EpisodeResult:
        """Trusted runner output after all 30 slots; impact fields remain uncomputed (S02)."""
        self._require_reset()
        if self._slot != 30:
            raise RuntimeError("result requires all 30 slots")
        return EpisodeResult(
            episode_id=self._episode.episode_id,
            run_id=run_id,
            system=system,
            n_decision_slots=24,
            n_completion_slots=6,
            slots=tuple(t.slot for t in self._history),
            totals=EpisodeTotals(),
            job_count_total=len(self._jobs),
            completed_job_ids=tuple(sorted(self._completed)),
            deadline_missed_job_ids=tuple(sorted(self._missed)),
            unfinished_job_ids=tuple(sorted(self._jobs.keys() - self._completed.keys())),
        )
