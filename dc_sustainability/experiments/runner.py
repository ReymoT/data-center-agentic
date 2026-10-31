"""E02 runner: drive whole episodes through the production execution path.

One unit is one system × episode × trial. For slots 0-23 the policy sees only the
simulator's ``VisibleState`` and the K02 context; its output goes through
``execute_policy_output`` (the real checker, controller and trace store). Slots 24-29
make no decision: a record with no selected stage takes the controller's refusal
path, which advances the simulator exactly once. The final ``EpisodeResult`` is
written atomically.

Resume works per unit: a completed unit is skipped, a failed unit is kept as failed,
and a unit with traces but no result needs reconciliation. None of them is re-run or
replaced silently. Private episode data stays in the run directory.

Plain and Agent units (E02-b) run only with explicit ``ModelInputs``; see
``experiments.models`` for their ledgers, attempt budget and unknown outcomes.
Trained C/D units (E02-c) run only with explicit ``TrainedInputs`` whose artifact
hashes match the run config; see ``experiments.trained``.
"""

import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.experiments import models as m
from dc_sustainability.experiments import registry
from dc_sustainability.experiments import trained as t
from dc_sustainability.experiments.config import (
    EpisodeBundle,
    RunConfig,
    decision_id,
    lf_sha256,
    load_bundle,
    publish,
)
from dc_sustainability.knowledge import retrieve
from dc_sustainability.llm.plain import PlainLLMPolicy
from dc_sustainability.policies import propose
from dc_sustainability.runtime import (
    ExecutionController,
    IndeterminateExecution,
    TraceStore,
    execute_policy_output,
)
from dc_sustainability.simulator import SchedulingSimulator

DECISION_SLOTS = s.PROPOSED_DECISION_SLOTS  # 24
TOTAL_SLOTS = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS  # 30


@dataclass(frozen=True)
class Unit:
    system: str
    episode_id: str
    trial: int | None

    @property
    def key(self) -> str:
        return s.sha256_hex([self.system, self.episode_id, self.trial])[:16]


@dataclass(frozen=True)
class UnitStatus:
    unit: Unit
    status: str  # completed, failed, needs_reconciliation, pending
    detail: str = ""


def run_directory(config: RunConfig, out_dir: Path) -> Path:
    """The run's directory, created with its manifest; a different config is refused."""
    root = Path(out_dir) / config.run_id
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "manifest.json"
    text = json.dumps(config.identity(), sort_keys=True, indent=1) + "\n"
    try:
        publish(manifest, text)
    except FileExistsError:
        if json.loads(manifest.read_text(encoding="utf-8")) != config.identity():
            raise ValueError(f"{root} belongs to a different run configuration") from None
    return root


def units(config: RunConfig) -> list[Unit]:
    out = []
    for system in config.systems:
        trials = config.model_trials if registry.spec(system).trials else (None,)
        out += [Unit(system, e, t) for e, _, _ in config.episodes for t in trials]
    return out


def unit_status(root: Path, unit: Unit) -> UnitStatus:
    folder = root / "units" / unit.key
    if (folder / "result.json").exists():
        s.EpisodeResult.from_json((folder / "result.json").read_text(encoding="utf-8"))
        return UnitStatus(unit, "completed")
    if (folder / "failed.json").exists():
        detail = json.loads((folder / "failed.json").read_text(encoding="utf-8"))["error"]
        return UnitStatus(unit, "failed", detail)
    if (folder / "unknown.json").exists():
        detail = json.loads((folder / "unknown.json").read_text(encoding="utf-8"))["error"]
        return UnitStatus(unit, "needs_reconciliation", detail)
    traces = folder / "traces"
    if traces.exists() and any(p.suffix == ".json" for p in traces.iterdir()):
        return UnitStatus(unit, "needs_reconciliation", "traces without a final result")
    return UnitStatus(unit, "pending")


def run(
    config: RunConfig,
    out_dir: Path,
    models: m.ModelInputs | None = None,
    trained: t.TrainedInputs | None = None,
) -> list[UnitStatus]:
    """Run every pending unit; return each unit's status after this call.

    Model units start only while the run's attempt budget still covers their worst
    case. After an unknown or unsaved attempt no further model unit starts, in this
    call or a later one, until that unit is reconciled.
    """
    for system in config.systems:  # refuse before touching anything
        registry.require_available(
            system, model_inputs=models is not None, trained_inputs=trained is not None
        )
    if models is not None:
        if config.model is None:
            raise ValueError("model inputs were given for a run without model systems")
        m.check_inputs(config.model, models, config.systems)
    if trained is not None:
        if config.trained is None:
            raise ValueError("trained inputs were given for a run without trained systems")
        t.check_inputs(config.trained, trained, config.systems)
    bundles = {}
    for episode_id, path, digest in config.episodes:
        if lf_sha256(path) != digest:
            raise ValueError(f"episode bundle {path} changed since the config was made")
        bundle = load_bundle(path)
        if bundle.episode.episode_id != episode_id:
            raise ValueError(f"{path} holds {bundle.episode.episode_id}, not {episode_id}")
        bundles[episode_id] = bundle
    root = run_directory(config, out_dir)
    results = []
    # A model unit awaiting reconciliation, from this call or an earlier one, halts the rest.
    halted = next(
        (
            st.detail
            for st in (unit_status(root, u) for u in units(config))
            if registry.spec(st.unit.system).trials and st.status == "needs_reconciliation"
        ),
        None,
    )
    for unit in units(config):
        status = unit_status(root, unit)
        model_unit = registry.spec(unit.system).trials
        if status.status == "pending" and model_unit:
            used = m.spent_attempts(root)
            # Admission must use the strictest enforceable per-unit ceiling. The
            # provider ledger can be lower than the 24-slot call-cap maximum.
            need = min(
                m.worst_case_attempts(unit.system),
                config.model.deployment["max_run_attempts"],
            )
            if halted is not None:
                status = UnitStatus(unit, "pending", f"model units halted: {halted}")
            elif used + need > config.model.max_total_attempts:
                status = UnitStatus(
                    unit,
                    "pending",
                    f"run attempt budget: {used} of {config.model.max_total_attempts} used, "
                    f"unit may need {need}",
                )
        if status.status == "pending" and not status.detail:
            status = _run_unit(config, root, unit, bundles[unit.episode_id], models, trained)
            if model_unit and status.status == "needs_reconciliation":
                halted = status.detail
        results.append(status)
    return results


def _run_unit(
    config: RunConfig, root: Path, unit: Unit, bundle: EpisodeBundle, models=None, trained=None
) -> UnitStatus:
    folder = root / "units" / unit.key
    folder.mkdir(parents=True, exist_ok=True)
    policy_errors: list[str] = []
    attempts: list = []
    try:
        result = _drive_episode(
            config, folder, unit, bundle, policy_errors, models, attempts, trained
        )
    except m.UncertainRequest as exc:
        detail = str(exc)
        seen = {a.client_trace_id for a in attempts}
        spent = [*attempts, *(a for a in exc.attempts if a.client_trace_id not in seen)]
        summary = m.attempt_summary(spent, exc.unsaved)
        record = {"unit": unit.__dict__, "error": detail, "attempts": summary}
        publish(folder / "unknown.json", json.dumps(record, indent=1) + "\n")
        return UnitStatus(unit, "needs_reconciliation", detail)
    except IndeterminateExecution as exc:
        return UnitStatus(unit, "needs_reconciliation", str(exc))
    except Exception as exc:  # retained, counted and never silently re-run
        detail = f"{type(exc).__name__}: {exc}"
        publish(folder / "failed.json", json.dumps({"unit": unit.__dict__, "error": detail}))
        return UnitStatus(unit, "failed", detail)
    publish(folder / "result.json", result.to_json() + "\n")
    if attempts:
        summary = json.dumps(m.attempt_summary(attempts), indent=1) + "\n"
        publish(folder / "attempts.json", summary)
    if policy_errors:
        publish(folder / "policy_errors.json", json.dumps(policy_errors, indent=1) + "\n")
    return UnitStatus(unit, "completed")


def _drive_episode(
    config, folder, unit, bundle, policy_errors, models=None, attempts=None, trained=None
) -> s.EpisodeResult:
    episode = bundle.episode
    simulator = SchedulingSimulator(allow_completion_starts=False)
    simulator.reset(episode, forecasts_by_slot=bundle.forecasts_by_slot)
    controller = ExecutionController(
        simulator, lambda: episode.snapshot, TraceStore(folder / "traces")
    )
    step = None
    if registry.spec(unit.system).trials:
        step = _model_step(config, unit, models, controller, episode, policy_errors)
    for slot in range(TOTAL_SLOTS):
        view = simulator.state()
        if view.current_slot != slot:
            raise RuntimeError(f"simulator is at slot {view.current_slot}, expected {slot}")
        dec_id = decision_id(config, unit.system, unit.episode_id, unit.trial, slot)
        if slot < DECISION_SLOTS and step is not None:
            spent = step(view, dec_id)
            attempts.extend(spent)
            m.raise_if_unreconciled(slot, spent, folder / "traces" / "provider-attempts")
        elif slot < DECISION_SLOTS:
            output = _policy_output(unit.system, view, episode, bundle, policy_errors, trained)
            execute_policy_output(
                controller,
                output,
                view,
                episode.snapshot,
                requested_system=unit.system,
                decision_id=dec_id,
                run_id=config.run_id,
                trial=unit.trial,
            )
        else:
            record = s.DecisionRecord(
                decision_id=dec_id,
                run_id=config.run_id,
                trial=unit.trial,
                system=unit.system,
                episode_id=unit.episode_id,
                slot=slot,
                not_applicable_stages=("initial", "repaired", "fallback"),
                final_status="blocked",
                errors=("completion slot: no decision",),
            )
            controller.execute_step(record, stage=None, expected_state_version=view.state_version)
    result = simulator.result(run_id=config.run_id, system=unit.system)
    data = result.model_dump(mode="python")
    data["trial"] = unit.trial
    return s.EpisodeResult.model_validate(data, strict=True)


def _policy_output(system, view, episode, bundle, policy_errors, trained=None) -> s.PolicyOutput:
    """The policy's own output from visible inputs only; an exception is a failed output."""
    try:
        context = retrieve(view, episode.snapshot).context
        if registry.spec(system).kind == "trained":
            return t.propose(system, trained, view, context)
        decision_time = bundle.slot0_utc + timedelta(hours=view.current_slot)
        return propose(
            view,
            context,
            system=system,
            decision_time_utc=decision_time if system == "greedy_b" else None,
        )
    except Exception as exc:
        policy_errors.append(f"slot {view.current_slot}: {type(exc).__name__}: {exc}")
        return s.PolicyOutput(system=system, output_status="error")


def _model_step(config, unit, models, controller, episode, policy_errors):
    """The decision function for one model unit, over a fresh ledger for this unit."""
    settings = config.model
    provider = m.new_provider(settings, models)
    common = dict(run_id=config.run_id, trial=unit.trial, seed=settings.seed(unit.trial))
    if unit.system == "agent":
        harness = m.new_harness(provider, controller, models.agent_renderers)

        def agent(view, dec_id):
            _, spent = m.agent_step(
                harness,
                view,
                episode.snapshot,
                decision_id=dec_id,
                decision_deadline=m.deadline(settings),
                **common,
            )
            return spent

        return agent
    policy = PlainLLMPolicy(provider)

    def plain(view, dec_id):
        try:
            context = retrieve(view, episode.snapshot).context
        except Exception as exc:  # a recorded blocked decision with no call
            policy_errors.append(f"slot {view.current_slot}: {type(exc).__name__}: {exc}")
            record = s.DecisionRecord(
                decision_id=dec_id,
                run_id=config.run_id,
                trial=unit.trial,
                system="plain_llm",
                episode_id=view.episode_id,
                slot=view.current_slot,
                not_applicable_stages=("repaired", "fallback"),
                final_status="blocked",
                errors=(f"context retrieval failed: {exc}",),
            )
            controller.execute_step(record, stage=None, expected_state_version=view.state_version)
            return ()
        _, spent = m.plain_step(
            controller,
            policy,
            provider,
            view,
            episode.snapshot,
            context,
            decision_id=dec_id,
            decision_deadline=m.deadline(settings),
            **common,
        )
        return spent

    return plain


def status(config: RunConfig, out_dir: Path) -> list[UnitStatus]:
    root = Path(out_dir) / config.run_id
    if not (root / "manifest.json").exists():
        return [UnitStatus(u, "pending") for u in units(config)]
    run_directory(config, out_dir)  # refuses a mismatched config
    return [unit_status(root, u) for u in units(config)]
