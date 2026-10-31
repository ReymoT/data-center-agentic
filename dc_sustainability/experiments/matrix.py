"""E02/I02: the planned held-out matrix as one frozen ``RunConfig``.

``build`` turns held-out episode bundles plus the frozen model and trained settings
into one run configuration; ``check`` refuses anything but the planned design
(MASTER_NISHA I02, the I02 freeze manifest's ``run_matrix``):

- 30 distinct held-out episodes: 24 core, each of 6 dates x 4 scenarios exactly
  once with forecasts visible, plus 6 missing-forecast episodes (withheld forecasts,
  which D03 defines for normal demand);
- all six systems, model trials 0-2 with one seed each;
- 300 units, at most 2,160 Plain and 6,480 Agent calls, and a run attempt budget
  equal to those maxima with a per-unit ledger cap that never trims them.

A smaller matrix is a protocol change to agree and freeze first, never something
this check lets through. Nothing here runs a unit or opens a model.
"""

from datetime import timedelta
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.experiments import models as m
from dc_sustainability.experiments import runner
from dc_sustainability.experiments.config import (
    ModelSettings,
    RunConfig,
    TrainedSettings,
    lf_sha256,
    load_bundle,
)

SYSTEMS = ("greedy_a", "greedy_b", "decision_tree_c", "random_forest_d", "plain_llm", "agent")
TRIALS = (0, 1, 2)
DATES, SCENARIOS, MISSING_FORECAST = 6, ("infeasible", "limited", "normal", "spike"), 6
TOTAL_RUNS = 300
MAXIMUM_CALLS = {"plain_llm": 2160, "agent": 6480}
PHOENIX = timedelta(hours=-7)  # slot 0 is Phoenix midnight (no daylight saving)


def build(
    name: str,
    bundles,
    *,
    model: ModelSettings,
    trained: TrainedSettings,
    code_revision: str,
    lock_sha256: str | None,
) -> RunConfig:
    """One run config over the given bundle paths, in the given order."""
    episodes = []
    for path in bundles:
        bundle = load_bundle(Path(path))
        episodes.append((bundle.episode.episode_id, str(path), lf_sha256(path)))
    return RunConfig(
        name,
        SYSTEMS,
        tuple(episodes),
        model_trials=TRIALS,
        code_revision=code_revision,
        lock_sha256=lock_sha256,
        model=model,
        trained=trained,
    )


def local_date(bundle) -> str:
    return (bundle.slot0_utc + PHOENIX).date().isoformat()


def check(config: RunConfig) -> list[str]:
    """Every way ``config`` differs from the planned matrix; empty when it matches."""
    problems = []
    if tuple(config.systems) != SYSTEMS:
        problems.append(f"systems must be exactly {', '.join(SYSTEMS)}")
    if tuple(config.model_trials) != TRIALS:
        problems.append("model trials must be exactly 0, 1, 2")
    bundles = []
    for episode_id, path, digest in config.episodes:
        if lf_sha256(path) != digest:
            problems.append(f"{episode_id}: bundle changed since the config was made")
            continue
        bundles.append(load_bundle(Path(path)))
    if len(config.episodes) != DATES * len(SCENARIOS) + MISSING_FORECAST:
        problems.append(f"{len(config.episodes)} episodes; the plan has 30")
    for b in bundles:
        if b.episode.split != "held_out":
            problems.append(f"{b.episode.episode_id}: split is {b.episode.split}, not held_out")
    core = [b for b in bundles if b.episode.forecast_visibility != "withheld"]
    missing = [b for b in bundles if b.episode.forecast_visibility == "withheld"]
    cells = sorted((local_date(b), b.episode.scenario_id) for b in core)
    dates = sorted({d for d, _ in cells})
    expected = sorted((d, x) for d in dates for x in SCENARIOS)
    if len(dates) != DATES or cells != expected:
        problems.append("core episodes must cover 6 dates x 4 scenarios, each exactly once")
    if len(missing) != MISSING_FORECAST or any(b.episode.scenario_id != "normal" for b in missing):
        problems.append("6 missing-forecast episodes are required, all normal demand")
    if any(b.forecasts_by_slot.get(slot) for b in missing for slot in b.forecasts_by_slot):
        problems.append("a missing-forecast bundle exposes forecasts")
    problems += _counts(config)
    return problems


def _counts(config: RunConfig) -> list[str]:
    problems = []
    units = runner.units(config)
    if len(units) != TOTAL_RUNS:
        problems.append(f"{len(units)} runs; the plan has {TOTAL_RUNS}")
    calls = {
        system: s.PROPOSED_DECISION_SLOTS
        * m.CALL_CAP[system]
        * sum(u.system == system for u in units)
        for system in MAXIMUM_CALLS
    }
    if calls != MAXIMUM_CALLS:
        problems.append(f"maximum calls are {calls}; the plan has {MAXIMUM_CALLS}")
    if config.model is not None:
        if config.model.max_total_attempts != sum(MAXIMUM_CALLS.values()):
            problems.append("the run attempt budget must equal the planned 8,640 maximum calls")
        ledger = config.model.deployment.get("max_run_attempts", 0)
        for system in MAXIMUM_CALLS:
            if ledger < s.PROPOSED_DECISION_SLOTS * m.CALL_CAP[system]:
                problems.append(f"the per-unit ledger cap would trim {system} units")
    return problems
