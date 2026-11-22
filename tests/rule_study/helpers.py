"""Shared builders for rule-study tests: real F02 records, real simulator, no stubs."""

from dataclasses import replace

from dc_sustainability import schemas as s
from dc_sustainability.rule_study import cases as c
from dc_sustainability.rule_study.scheduler import ScoreKwhConvention, propose_rules_v1

CONV = ScoreKwhConvention()


def job(job_id, power=20, deadline=3, flexible=True, *, duration=1, arrival=0):
    return c._job(job_id, power, deadline, flexible, duration=duration, arrival=arrival)


def case_with(
    jobs,
    *,
    capacity=60,
    background=20,
    scores=(300, 100, 200),
    remaining=200,
    forecast=True,
    pue=1.0,
    case_id="X",
    episode_id="EP-RULEX",
):
    return replace(
        c.CASE_A,
        case_id=case_id,
        episode_id=episode_id,
        capacity_kw=capacity,
        background_kw=background,
        pue=pue,
        jobs=tuple(jobs),
        first_scores=tuple(scores),
        remaining_score=remaining,
        forecast_present=forecast,
    )


def visible(case, *, slot=0, waiting=None, running=(), carbon=None):
    """Build a policy-visible state and the authoritative snapshot for a case."""
    snapshot = case.snapshot()
    if carbon is None:
        table = case.forecasts_by_slot()
        carbon = table[slot] if table else ()
    state = s.VisibleState.from_snapshot(
        snapshot,
        episode_id=case.episode_id,
        current_slot=slot,
        state_version=slot,
        waiting_jobs=tuple(case.jobs if waiting is None else waiting),
        running_jobs=tuple(running),
        carbon_facts=tuple(carbon),
    )
    return state, snapshot


def propose(case, *, slot=0, convention=CONV, **kwargs):
    state, snapshot = visible(case, slot=slot, **kwargs)
    return propose_rules_v1(
        state, snapshot, decision_time_utc=case.decision_time_utc(slot), score_convention=convention
    )


def starts(decision):
    return {p.job_id: p.start_slot for p in decision.plan.starts}


def candidate(decision, **chosen):
    """Find an enumerated candidate by {job_id: start-or-None}."""
    for cand in decision.search.candidates:
        if dict(cand.starts) == chosen:
            return cand
    raise AssertionError(f"no enumerated candidate {chosen}")


# --------------------------------------------------------------------------- runner helpers
from pathlib import Path  # noqa: E402

from dc_sustainability.rule_study.runner import (  # noqa: E402
    RuleStudyRunner,
    make_bindings,
    run_case,
)
from dc_sustainability.simulator import SchedulingSimulator  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


# Unit-test-only commit value: tests run on an uncommitted tree, so they cannot bind a real
# frozen commit. Study traces (demo/verification) always use make_bindings() from a clean HEAD.
TEST_ONLY_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def bindings_for(case):
    return make_bindings(case, REPO_ROOT, code_commit=TEST_ONLY_COMMIT)


def run(tmp_path, case, policy="rules-v1", **kwargs):
    """Run all 30 decisions of a case through the real runner, simulator and checker."""
    return run_case(
        tmp_path, case, policy, bindings=bindings_for(case), score_convention=CONV, **kwargs
    )


def fresh_runner(tmp_path, case, policy="rules-v1", *, simulator=None, reader=None, **kwargs):
    """A runner over a freshly reset real simulator (callers drive ``decide`` themselves)."""
    sim = simulator or SchedulingSimulator(allow_completion_starts=False)
    if simulator is None:
        sim.reset(case.episode(), forecasts_by_slot=case.forecasts_by_slot())
    snapshot = case.snapshot()
    runner = RuleStudyRunner(
        sim,
        reader or (lambda: snapshot),
        tmp_path,
        policy_id=policy,
        case_id=case.case_id,
        decision_time_utc=case.decision_time_utc,
        bindings=bindings_for(case),
        score_convention=CONV,
        case_json=case.case_json(),
        **kwargs,
    )
    return runner, sim
