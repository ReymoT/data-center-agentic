"""E02-b model units over real loopback HTTP with a scripted synthetic responder.

The test server is not a model: it answers from the visible context in each request.
Provider, harness, checker, controller, trace store and simulator are the real ones.
Nothing here is evidence of inference, prompt quality or a study result.
"""

import json

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from dc_sustainability.experiments import models as m
from dc_sustainability.experiments import runner
from dc_sustainability.experiments.config import ModelSettings, RunConfig, lf_sha256
from dc_sustainability.llm.plain import prompt_template_sha256
from dc_sustainability.llm.provider import OllamaProvider
from dc_sustainability.runtime import ExecutionController
from tests.experiments.test_runner import result, traces, write_bundle
from tests.llm.test_ollama_provider import deployment, envelope
from tests.llm.test_ollama_provider import server as server  # noqa: F401


# ----------------------------------------------------------------- synthetic responder
def context_of(request) -> s.ContextContent:
    return s.ContextContent.from_json(request["messages"][-1]["content"].splitlines()[-1])


def scripted_plan(c: s.ContextContent, *, overlap: bool) -> s.Plan:
    """Start one waiting job when nothing runs and defer the rest; overlap starts all."""
    waiting = sorted(j.job_id for j in c.waiting_jobs)
    now = waiting if overlap else waiting[:1] if not c.running_jobs else []
    return s.Plan(
        episode_id=c.episode_id,
        slot=c.current_slot,
        state_version=c.state_version,
        status="proposed",
        starts=tuple(s.PlannedStart(job_id=j, start_slot=c.current_slot) for j in now),
        deferrals=tuple(s.Deferral(job_id=j, reason="capacity") for j in waiting if j not in now),
    )


def reply(request, *, overlap: bool) -> str:
    title = request["format"]["title"]
    explanation = s.Explanation(summary="Synthetic test explanation.", source="llm")
    if title == "Explanation":
        return explanation.to_json()
    plan = scripted_plan(context_of(request), overlap=overlap)
    if title == "Plan":
        return plan.to_json()
    return s.PolicyOutput(
        system="plain_llm", output_status="ok", plan=plan, explanation=explanation
    ).to_json()


@pytest.fixture
def model(server, monkeypatch):
    """The loopback server answering from each request; HTTP 500 on chosen calls."""
    server.overlap, server.fail_on = False, set()

    def do_POST(handler):
        request = json.loads(handler.rfile.read(int(handler.headers["Content-Length"])))
        server.requests.append(request)
        if len(server.requests) in server.fail_on:  # sent, outcome uncertain
            handler.respond(b"synthetic failure", 500)
            return
        content = reply(request, overlap=server.overlap)
        handler.respond({**envelope(), "message": {"role": "assistant", "content": content}})

    monkeypatch.setattr(server.RequestHandlerClass, "do_POST", do_POST)
    return server


def messages(context, *args):
    return [
        {"role": "user", "content": "SYNTHETIC TEST, NOT INFERENCE\n" + context.content.to_json()}
    ]


RENDERERS = m.AgentRenderers(proposal=messages, repair=messages, explanation=messages)


def settings(server, trials=(0,), max_total=1000, **pins):
    return ModelSettings(
        seeds=tuple((t, 100 + t) for t in trials),
        decision_seconds=10,
        max_total_attempts=max_total,
        deployment=m.deployment_pins(deployment(server, max_run_attempts=72, **pins)),
        plain_prompt_sha256=prompt_template_sha256(),
        agent_renderer_ref="synthetic-test-renderers",
    )


def inputs(server, **pins):
    def factory():
        # A synthetic counter belongs only to this test; no production tokenizer is implied.
        return OllamaProvider(
            deployment(server, max_run_attempts=72, **pins), count_prompt_tokens=lambda _: 20
        )

    return m.ModelInputs(provider_factory=factory, agent_renderers=RENDERERS)


def model_config(path, ep, server, systems=("plain_llm", "agent"), trials=(0,), **changes):
    return RunConfig(
        "test",
        systems,
        ((ep.episode_id, str(path), lf_sha256(path)),),
        model_trials=trials,
        code_revision="test",
        model=settings(server, trials, **changes),
    )


def saved_attempts(root, unit):
    folder = root / unit.key / "traces" / "provider-attempts"
    return [json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")]


# ----------------------------------------------------------------- full episodes
def test_plain_and_agent_units_run_whole_episodes_with_a_ledger_per_trial(tmp_path, model):
    ep, path = write_bundle(tmp_path)
    cfg = model_config(path, ep, model, trials=(0, 1))
    statuses = runner.run(cfg, tmp_path / "out", inputs(model))
    assert [st.status for st in statuses] == ["completed"] * 4
    root = tmp_path / "out" / cfg.run_id / "units"
    total = 0
    for st in statuses:
        records = traces(root, st.unit)
        assert [d.slot for d in records] == list(range(30))
        assert all(d.system == st.unit.system and d.trial == st.unit.trial for d in records)
        assert all(d.model_call_count == 0 for d in records[24:])  # completion slots
        assert all(d.model_call_count <= m.CALL_CAP[st.unit.system] for d in records)
        calls = sum(d.model_call_count for d in records)
        assert calls > 0  # trial 1 is not blocked by trial 0's per-decision caps
        saved = saved_attempts(root, st.unit)
        summary = json.loads((root / st.unit.key / "attempts.json").read_text(encoding="utf-8"))
        assert len(saved) == len(summary) == calls
        assert {a["outcome"] for a in summary} == {"ok"}
        assert {a["decision_id"] for a in saved} <= {d.decision_id for d in records}
        assert {a["seed"] for a in saved} == {100 + st.unit.trial}
        res = result(root, st.unit)
        assert res.completed_job_ids == ("J1", "J2") and res.trial == st.unit.trial
        rep = r.replay_episode(ep, r.executed_starts(records, ep.episode_id), Q03_OPTION_B)
        assert rep.valid and r.compare_result(rep, res) == ()
        total += calls
    assert len(model.requests) == total
    assert {q["options"]["seed"] for q in model.requests} == {100, 101}


def test_plain_has_one_call_and_no_repair_or_fallback(tmp_path, model):
    model.overlap = True  # every plan overloads capacity at slot 0
    ep, path = write_bundle(tmp_path)
    cfg = model_config(path, ep, model, systems=("plain_llm",))
    [st] = runner.run(cfg, tmp_path / "out", inputs(model))
    records = traces(tmp_path / "out" / cfg.run_id / "units", st.unit)
    first = records[0]
    assert first.final_status == "blocked" and first.initial.check.status == "fail"
    assert first.model_call_count == 1 and first.repaired is None and first.fallback is None
    assert all(set(d.not_applicable_stages) >= {"repaired", "fallback"} for d in records)
    assert len(model.requests) == sum(d.model_call_count for d in records)
    assert first.raw_response is not None  # the original output is kept for scoring


def test_agent_falls_back_to_real_greedy_a_within_three_calls(tmp_path, model):
    model.overlap = True
    ep, path = write_bundle(tmp_path)
    cfg = model_config(path, ep, model, systems=("agent",))
    [st] = runner.run(cfg, tmp_path / "out", inputs(model))
    first = traces(tmp_path / "out" / cfg.run_id / "units", st.unit)[0]
    assert first.initial.check.status == "fail" and first.repaired.check.status == "fail"
    assert first.fallback.check.status == "pass" and first.final_status == "executed"
    assert first.model_call_count == 3 and first.repair_count == 1
    assert first.explanation is not None


# ----------------------------------------------------------------- unknown outcomes
def test_uncertain_request_stops_the_unit_and_halts_model_units(tmp_path, model):
    model.fail_on = {1}
    ep, path = write_bundle(tmp_path)
    cfg = model_config(path, ep, model, systems=("greedy_a", "plain_llm"), trials=(0, 1))
    out = tmp_path / "out"
    ga, t0, t1 = runner.run(cfg, out, inputs(model))
    assert ga.status == "completed"  # deterministic units are unaffected
    assert t0.status == "needs_reconciliation" and "unknown outcome" in t0.detail
    assert t1.status == "pending" and "halted" in t1.detail
    assert len(model.requests) == 1  # never retried
    root = out / cfg.run_id / "units"
    [record] = traces(root, t0.unit)
    assert record.slot == 0 and record.final_status == "blocked" and record.model_call_count == 1
    unknown = json.loads((root / t0.unit.key / "unknown.json").read_text(encoding="utf-8"))
    assert [a["outcome"] for a in unknown["attempts"]] == ["unknown"]
    assert len(saved_attempts(root, t0.unit)) == 1
    assert not (root / t0.unit.key / "result.json").exists()

    # A later call keeps both: still unreconciled, still halted, nothing sent.
    again = runner.run(cfg, out, inputs(model))
    assert [st.status for st in again] == ["completed", "needs_reconciliation", "pending"]
    assert len(model.requests) == 1


def test_uncertain_agent_proposal_sends_nothing_more_and_needs_reconciliation(tmp_path, model):
    model.fail_on, model.overlap = {1}, True  # repair would be routed if the call were failed
    ep, path = write_bundle(tmp_path)
    cfg = model_config(path, ep, model, systems=("agent",))
    [st] = runner.run(cfg, tmp_path / "out", inputs(model))
    assert st.status == "needs_reconciliation" and "unknown outcome" in st.detail
    assert len(model.requests) == 1  # no repair, explanation or retry
    root = tmp_path / "out" / cfg.run_id / "units"
    [record] = traces(root, st.unit)
    assert record.final_status == "blocked" and record.model_call_count == 1
    assert record.initial is None and record.repaired is None and record.fallback is None
    assert record.repair_count == 0 and not record.executed_starts
    unknown = json.loads((root / st.unit.key / "unknown.json").read_text(encoding="utf-8"))
    assert [a["outcome"] for a in unknown["attempts"]] == ["unknown"]
    assert len(saved_attempts(root, st.unit)) == 1


@pytest.mark.parametrize("system", ["plain_llm", "agent"])
def test_unsaved_attempt_stops_the_unit_halts_model_units_and_keeps_budget(
    tmp_path, model, monkeypatch, system
):
    def fail(self, attempt, **link):
        raise OSError("synthetic attempt-storage failure")

    monkeypatch.setattr(ExecutionController, "record_attempt", fail)
    ep, path = write_bundle(tmp_path)
    cfg = model_config(path, ep, model, systems=(system,), trials=(0, 1))
    out = tmp_path / "out"
    t0, t1 = runner.run(cfg, out, inputs(model))
    assert t0.status == "needs_reconciliation" and "could not be saved" in t0.detail
    assert t1.status == "pending" and "halted" in t1.detail
    assert len(model.requests) == 1  # no later slot or unit dispatches
    root = out / cfg.run_id / "units"
    assert not (root / t0.unit.key / "result.json").exists()
    assert [d.slot for d in traces(root, t0.unit)] in ([], [0])  # the agent traces slot 0
    assert all(d.final_status == "blocked" for d in traces(root, t0.unit))
    assert not saved_attempts(root, t0.unit)
    unknown = json.loads((root / t0.unit.key / "unknown.json").read_text(encoding="utf-8"))
    assert [(a["outcome"], a["saved"]) for a in unknown["attempts"]] == [("ok", False)]
    assert m.spent_attempts(out / cfg.run_id) == 1  # the lost request still counts

    again = runner.run(cfg, out, inputs(model))
    assert [st.status for st in again] == ["needs_reconciliation", "pending"]
    assert len(model.requests) == 1


# ----------------------------------------------------------------- budget and refusals
def test_run_attempt_budget_counts_persisted_attempts_across_calls(tmp_path, model):
    ep, path = write_bundle(tmp_path)
    # Plain's worst case is 24 per unit; trial 0 spends 3, so trial 1 would exceed 25.
    cfg = model_config(path, ep, model, systems=("plain_llm",), trials=(0, 1), max_total=25)
    t0, t1 = runner.run(cfg, tmp_path / "out", inputs(model))
    assert t0.status == "completed"
    assert t1.status == "pending" and "run attempt budget: 3 of 25 used" in t1.detail
    sent = len(model.requests)
    t0, t1 = runner.run(cfg, tmp_path / "out", inputs(model))  # a new process, same budget
    assert t1.status == "pending" and len(model.requests) == sent


def test_model_systems_refuse_without_explicit_inputs_before_writing(tmp_path, model):
    ep, path = write_bundle(tmp_path)
    cfg = model_config(path, ep, model)
    with pytest.raises(NotImplementedError, match="explicit model inputs"):
        runner.run(cfg, tmp_path / "out")
    no_renderers = m.ModelInputs(provider_factory=inputs(model).provider_factory)
    with pytest.raises(ValueError, match="renderers"):
        runner.run(cfg, tmp_path / "out", no_renderers)
    with pytest.raises(ValueError, match="pins"):
        runner.run(cfg, tmp_path / "out", inputs(model, runtime_version="other-runtime"))
    plain = model_config(path, ep, model, systems=("plain_llm",))
    changed = RunConfig(**{**plain.__dict__, "model": ModelSettings(
        **{**plain.model.__dict__, "plain_prompt_sha256": "0" * 64})})  # fmt: skip
    with pytest.raises(ValueError, match="prompt files"):
        runner.run(changed, tmp_path / "out", inputs(model))
    assert not (tmp_path / "out").exists() and model.requests == []


def test_model_settings_are_required_validated_and_in_the_run_identity(tmp_path, server):
    ep, path = write_bundle(tmp_path)
    episodes = ((ep.episode_id, str(path), lf_sha256(path)),)
    with pytest.raises(ValueError, match="model settings"):
        RunConfig("test", ("plain_llm",), episodes)
    with pytest.raises(ValueError, match="model settings"):
        RunConfig("test", ("greedy_a",), episodes, model=settings(server))
    with pytest.raises(ValueError, match="one seed for each"):
        RunConfig("test", ("plain_llm",), episodes, model_trials=(0, 1), model=settings(server))
    with pytest.raises(ValueError, match="positive"):
        settings(server).__class__(**{**settings(server).__dict__, "decision_seconds": 0})
    with pytest.raises(ValueError, match="address"):
        ModelSettings(**{**settings(server).__dict__, "deployment": {"base_url": "x"}})
    a = model_config(path, ep, server, systems=("plain_llm",))
    b = model_config(path, ep, server, systems=("plain_llm",), max_total=999)
    assert a.identity()["model"]["seeds"] == [[0, 100]]
    assert a.run_id != b.run_id  # a different budget is a different run
    assert "model" not in RunConfig("test", ("greedy_a",), episodes).identity()
