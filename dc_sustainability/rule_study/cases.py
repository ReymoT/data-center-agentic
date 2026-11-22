"""Independently authored synthetic RULE-01 cases A, B and the B-progress subcase.

Everything here is a newly authored assumption (docs/rule_study/specification.json), not
derived from source, private or old held-out data. Score weights are ARTIFICIAL: they are
encoded in the legacy ``g/kWh``-shaped forecast field only as an adapter encoding and are
never measured emissions. The perfect-artificial-forecast convention is declared: the same
authored profile supplies both the visible forecast and the evaluator's accounting weights.

Slot 0 is mapped to a synthetic UTC instant (``SLOT0_UTC``) as the trusted configured mapping;
each decision slot ``t`` gets a fresh forecast issue time ``SLOT0_UTC + t`` hours.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Optional

from dc_sustainability import schemas as s
from dc_sustainability.rule_study.records import study_json, study_sha256

SLOT0_UTC = datetime(2026, 11, 20, 7, 0, tzinfo=timezone.utc)  # synthetic mapping, 00:00 Phoenix
SOURCE_ID = "SRC-RULESYN"
SITE_ID = "SITE1"
HORIZON = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS


def _semantics() -> s.CarbonSemantics:
    return s.CarbonSemantics(
        pollutant_basis="unresolved",
        interval_convention="unresolved",
        emissions_factor_type="average",
        slot_mapping_status="provisional",
    )


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    episode_id: str
    capacity_kw: int
    background_kw: int
    pue: float
    jobs: tuple[s.Job, ...]
    first_scores: tuple[int, ...]
    remaining_score: int = 200
    forecast_present: bool = True
    fault_starts: tuple[str, ...] = ()  # slot-0 injected proposal (rules-v1 demonstration only)

    @property
    def score_profile(self) -> tuple[int, ...]:
        """30 artificial integer weights; slots after the authored ones use ``remaining_score``."""
        return self.first_scores + (self.remaining_score,) * (HORIZON - len(self.first_scores))

    def decision_time_utc(self, slot: int) -> datetime:
        return SLOT0_UTC + timedelta(hours=slot)

    def source(self) -> s.SourceRef:
        return s.SourceRef(
            source_id=SOURCE_ID,
            path="docs/rule_study/specification.json (artificial score weights, not g/kWh)",
            redistribution_status="permitted",  # team-authored synthetic assumption
        )

    def snapshot(self) -> s.ConstraintSnapshot:
        constraints = [
            s.Constraint(
                constraint_id="CON-CAP-01",
                constraint_type="capacity",
                limit_value=self.capacity_kw,
                unit="kW",
                applies_to_site=SITE_ID,
                source_id=SOURCE_ID,
            ),
            s.Constraint(
                constraint_id="CON-FRESH-01",
                constraint_type="freshness",
                limit_value=2,
                unit="slot",
                applies_to_site=SITE_ID,
                source_id=SOURCE_ID,
            ),
        ]
        for job in self.jobs:
            constraints.append(
                s.Constraint(
                    constraint_id=f"CON-DL-{job.job_id}",
                    constraint_type="deadline",
                    limit_value=job.deadline_slot,
                    unit="slot",
                    applies_to_jobs=(job.job_id,),
                    source_id=SOURCE_ID,
                )
            )
            if not job.flexible:
                constraints.append(
                    s.Constraint(
                        constraint_id=f"CON-NF-{job.job_id}",
                        constraint_type="nonflexible",
                        limit_value=job.arrival_slot,
                        unit="slot",
                        applies_to_jobs=(job.job_id,),
                        source_id=SOURCE_ID,
                    )
                )
        return s.ConstraintSnapshot(
            snapshot_id="SNAP-RULESYN",
            site=s.SiteConfig(
                site_id=SITE_ID,
                background_kw=self.background_kw,
                pue=self.pue,
                slot_hours=1,
            ),
            constraints=tuple(constraints),
            sources=(self.source(),),
        )

    def observations(self) -> tuple[s.CarbonObservation, ...]:
        """Evaluator-view accounting weights (private; never policy-visible)."""
        return tuple(
            s.CarbonObservation(
                fact_id=f"FACT-OBS-SYN-s{slot:02d}",
                value=weight,
                unit="g/kWh",  # adapter encoding of an ARTIFICIAL weight, not a physical unit
                source_id=SOURCE_ID,
                observed_at_utc=SLOT0_UTC + timedelta(hours=slot),
                valid_slot=slot,
                semantics=_semantics(),
                quality_status="unvalidated",
            )
            for slot, weight in enumerate(self.score_profile)
        )

    def forecasts_by_slot(self) -> Optional[dict[int, tuple[s.CarbonForecast, ...]]]:
        """Perfect artificial forecast with a fresh issue time per decision slot."""
        if not self.forecast_present:
            return None
        table = {}
        for decision_slot in range(HORIZON):
            visible_end = min(decision_slot + s.PROPOSED_DECISION_SLOTS, HORIZON)
            table[decision_slot] = tuple(
                s.CarbonForecast(
                    fact_id=f"FACT-SCORE-t{decision_slot:02d}-s{slot:02d}",
                    value=self.score_profile[slot],
                    unit="g/kWh",  # adapter encoding of an ARTIFICIAL weight, not a physical unit
                    source_id=SOURCE_ID,
                    valid_slot=slot,
                    issued_at_utc=self.decision_time_utc(decision_slot),
                    forecast_kind="perfect_foresight",
                    semantics=_semantics(),
                    quality_status="unvalidated",
                )
                for slot in range(decision_slot, visible_end)
            )
        return table

    def episode(self) -> s.PrivateEpisode:
        return s.PrivateEpisode(
            episode_id=self.episode_id,
            scenario_id=f"SCN-{self.case_id}".replace("_", "-"),
            split="development",  # authored example; never an old held-out identity
            seed=0,
            n_decision_slots=s.PROPOSED_DECISION_SLOTS,
            n_completion_slots=s.PROPOSED_COMPLETION_SLOTS,
            snapshot=self.snapshot(),
            jobs=tuple(
                s.PrivateJob(
                    job=job,
                    scenario_id=f"SCN-{self.case_id}".replace("_", "-"),
                    split="development",
                    seed=0,
                    synthetic=True,
                )
                for job in self.jobs
            ),
            realized_carbon=self.observations(),
            forecast_visibility="perfect_foresight" if self.forecast_present else "withheld",
        )

    def case_json(self) -> dict:
        """The canonical ``case.json`` object in exactly the merged trace reader's input shape."""
        data = {
            "case_id": self.case_id,
            "capacity_kw": self.capacity_kw,
            "background_kw": self.background_kw,
            "jobs": [
                {
                    "job_id": job.job_id,
                    "power_kw": _integral(job.power_kw),
                    "duration_slots": job.duration_slots,
                    "arrival_slot": job.arrival_slot,
                    "deadline_slot": job.deadline_slot,
                    "flexible": job.flexible,
                }
                for job in self.jobs
            ],
            "scores": list(self.score_profile) if self.forecast_present else None,
        }
        if self.fault_starts:
            data["fault_starts"] = list(self.fault_starts)
        return data

    def case_sha256(self) -> str:
        """Hash of the canonical ``case.json`` object (the reader recomputes this exactly)."""
        return study_sha256(study_json(self.case_json()))

    def fault_injection(self, state: s.VisibleState) -> Optional[s.Plan]:
        """The authored slot-0 injected proposal, or None (it is never a natural policy output)."""
        if not self.fault_starts or state.current_slot != 0:
            return None
        return s.Plan(
            episode_id=state.episode_id,
            slot=0,
            state_version=state.state_version,
            starts=tuple(
                s.PlannedStart(job_id=job_id, start_slot=0) for job_id in self.fault_starts
            ),
            evidence_ids=(),
            status="proposed",
        )


def _integral(value) -> int:
    """The reader's case shape is integer-only; fail instead of silently truncating."""
    if value != int(value):
        raise ValueError(f"non-integral power {value!r} cannot be written to case.json")
    return int(value)


def _job(job_id, power, deadline, flexible, *, duration=1, arrival=0) -> s.Job:
    return s.Job(
        job_id=job_id,
        arrival_slot=arrival,
        duration_slots=duration,
        power_kw=power,
        deadline_slot=deadline,
        flexible=flexible,
    )


CASE_A = CaseSpec(
    case_id="A",
    episode_id="EP-RULEA",
    capacity_kw=60,
    background_kw=20,
    pue=1.0,
    jobs=(_job("J1", 20, 3, True), _job("J2", 20, 1, False)),
    first_scores=(300, 100, 200),
)
CASE_B = CaseSpec(
    case_id="B",
    episode_id="EP-RULEB",
    capacity_kw=60,
    background_kw=20,
    pue=1.0,
    jobs=(_job("J1", 30, 1, False), _job("J2", 30, 1, False)),
    first_scores=(300, 100, 200),
)
CASE_B_FAULT = replace(CASE_B, case_id="B-fault", episode_id="EP-RULEBF", fault_starts=("J1", "J2"))
CASE_B_PROGRESS = replace(
    CASE_B,
    case_id="B-progress",
    episode_id="EP-RULEBP",
    jobs=(_job("J1", 30, 1, False), _job("J2", 30, 2, True)),
)
AUTHORED_CASES = {case.case_id: case for case in (CASE_A, CASE_B, CASE_B_FAULT, CASE_B_PROGRESS)}
