"""F02 contract tests: strictness, leakage, observation/forecast separation, hashing, gates."""

import json
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from tests.contracts import fixtures as fx

JOB = dict(
    job_id="J1", arrival_slot=0, duration_slots=2, power_kw=40, deadline_slot=6, flexible=True
)


def job(**over) -> s.Job:
    return s.Job(**{**JOB, **over})


# ---------------------------------------------------------------- 1. infeasible job is valid
def test_infeasible_job_is_structurally_valid_and_serializable():
    j = fx.jobs()["J3"]
    assert j.slack_slots == -1  # arrival 4 + duration 3 > deadline 6
    assert s.Job.from_json(j.to_json()) == j


def test_even_deadline_before_arrival_stays_representable():
    assert job(arrival_slot=5, deadline_slot=2).slack_slots < 0


# ---------------------------------------------------------------- 2. strict scalar types
@pytest.mark.parametrize(
    "field,value",
    [
        ("arrival_slot", True),
        ("arrival_slot", 1.0),
        ("arrival_slot", 1.5),
        ("arrival_slot", "1"),
        ("arrival_slot", -1),
        ("duration_slots", True),
        ("duration_slots", 0),
        ("duration_slots", -2),
        ("deadline_slot", 2.0),
        ("power_kw", True),
        ("power_kw", 0),
        ("power_kw", "40"),
        ("flexible", 1),
        ("flexible", "true"),
        ("job_id", ""),
        ("job_id", "bad id"),
        ("job_id", 7),
    ],
)
def test_job_rejects_invalid_field_values(field, value):
    with pytest.raises(ValueError):
        job(**{field: value})


def test_job_power_int_is_normalised_to_float():
    assert isinstance(job(power_kw=40).power_kw, float)


# ---------------------------------------------------------------- 4. non-finite numbers
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numbers_rejected(bad):
    with pytest.raises(ValueError):
        job(power_kw=bad)
    with pytest.raises(ValueError):
        s.SiteConfig(site_id="S", background_kw=bad, pue=1.0, slot_hours=1)
    with pytest.raises(ValueError):
        fx.forecasts()[0].model_copy(update={}).__class__(
            **{**fx.forecasts()[0].model_dump(), "value": bad}
        )


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_json_rejected(token):
    text = fx.jobs()["J1"].to_json().replace('"power_kw":40.0', f'"power_kw":{token}')
    with pytest.raises(ValueError):
        s.Job.from_json(text)


def test_from_jsonable_rejects_bool_and_float_slots():
    data = fx.jobs()["J1"].to_jsonable()
    for bad in (True, 1.0):
        with pytest.raises(ValueError):
            s.Job.from_jsonable({**data, "arrival_slot": bad})
    with pytest.raises(ValueError):
        s.Job.from_jsonable({**data, "power_kw": float("nan")})


# ---------------------------------------------------------------- 3. duplicate ids
def test_duplicate_ids_rejected():
    j = fx.jobs()
    snap = fx.snapshot()
    state = fx.visible_state(snap).model_dump()
    with pytest.raises(ValueError, match="duplicate"):
        s.VisibleState(**{**state, "waiting_jobs": (j["J1"], j["J1"])})
    with pytest.raises(ValueError, match="duplicate"):  # same id waiting and running
        s.VisibleState(
            **{
                **state,
                "waiting_jobs": (j["J1"],),
                "running_jobs": (s.RunningJobView(job=j["J1"], start_slot=0),),
            }
        )
    with pytest.raises(ValueError, match="duplicate"):
        s.ConstraintSnapshot(
            **{**snap.model_dump(), "constraints": snap.constraints + (snap.constraints[0],)}
        )
    with pytest.raises(ValueError, match="duplicate"):
        s.Plan(
            episode_id="EP-A",
            slot=0,
            state_version=0,
            status="proposed",
            starts=(
                s.PlannedStart(job_id="J1", start_slot=0),
                s.PlannedStart(job_id="J1", start_slot=1),
            ),
        )
    facts = fx.forecasts()
    with pytest.raises(ValueError, match="duplicate"):
        s.VisibleState(**{**state, "carbon_facts": facts + (facts[0],)})
    with pytest.raises(ValueError, match="duplicate"):
        s.PrivateEpisode(
            **{**fx.private_episode().model_dump(), "jobs": fx.private_episode().jobs * 2}
        )


# ---------------------------------------------------------------- 5. strict action records
def test_unexpected_fields_rejected_everywhere():
    for rec in (fx.plan(), fx.approved_actions(), fx.jobs()["J1"], fx.check_pass()):
        data = rec.to_jsonable()
        with pytest.raises(ValueError):
            type(rec).from_jsonable({**data, "surprise": 1})
    with pytest.raises(ValueError):
        s.PlannedStart(job_id="J1", start_slot=0, priority=9)
    data = fx.approved_actions().to_jsonable()
    data["starts"][0]["force"] = True  # nested unexpected action field
    with pytest.raises(ValueError):
        s.ApprovedActions.from_jsonable(data)


def test_approved_actions_only_current_slot_and_bound_to_checked_plan():
    p, chk = fx.plan("approved"), fx.check_pass()
    aa = s.ApprovedActions.from_checked_plan(p, chk, 0)
    assert [(a.job_id, a.start_slot) for a in aa.starts] == [("J1", 0)]  # J2@2 is an intention
    assert [x.job_id for x in p.future_intentions] == ["J2"]
    with pytest.raises(ValueError, match="current slot"):
        s.ApprovedActions(
            episode_id="EP-A",
            slot=0,
            state_version=0,
            plan_hash="0" * 64,
            check_id="CHK-1",
            starts=(s.ApprovedStart(job_id="J2", start_slot=2),),
        )
    with pytest.raises(ValueError, match="not 'pass'"):
        s.ApprovedActions.from_checked_plan(p, fx.check_missing_capacity(p), 0)
    other = fx.abstention_plan()
    with pytest.raises(ValueError, match="different plan"):
        s.ApprovedActions.from_checked_plan(other, chk, 0)
    with pytest.raises(ValueError, match="state version"):
        s.ApprovedActions.from_checked_plan(p, chk, 1)


def test_backdated_and_unknown_job_starts_remain_representable_for_the_checker():
    p = s.Plan(
        episode_id="EP-A",
        slot=3,
        state_version=3,
        status="proposed",
        starts=(
            s.PlannedStart(job_id="J1", start_slot=2),
            s.PlannedStart(job_id="NOPE", start_slot=3),
        ),
    )
    assert [x.job_id for x in p.current_starts] == ["NOPE"]


def test_plan_status_excluded_from_hash_but_content_included():
    assert fx.plan("proposed").plan_hash == fx.plan("approved").plan_hash
    changed = s.Plan(
        **{**fx.plan().model_dump(), "starts": (s.PlannedStart(job_id="J1", start_slot=1),)}
    )
    assert changed.plan_hash != fx.plan().plan_hash
    reordered = s.Plan(**{**fx.plan().model_dump(), "starts": tuple(reversed(fx.plan().starts))})
    assert reordered.plan_hash == fx.plan().plan_hash


def test_job_cannot_be_started_and_deferred():
    with pytest.raises(ValueError, match="both started"):
        s.Plan(
            episode_id="EP-A",
            slot=0,
            state_version=0,
            status="proposed",
            starts=(s.PlannedStart(job_id="J1", start_slot=0),),
            deferrals=(s.Deferral(job_id="J1", reason="capacity"),),
        )


# ---------------------------------------------------------------- 6. private data cannot enter visible records
PRIVATE_FIELDS = [
    "scenario_id",
    "split",
    "seed",
    "synthetic",
    "realized_carbon",
    "future_arrivals",
    "oracle",
]


@pytest.mark.parametrize("field", PRIVATE_FIELDS)
def test_visible_records_have_no_private_fields(field):
    for rec in (fx.visible_state(), fx.jobs()["J1"], fx.forecasts()[0]):
        with pytest.raises(ValueError):
            type(rec).from_jsonable({**rec.to_jsonable(), field: "x"})
    ctx = fx.build_examples()["context_flat"].to_jsonable()
    ctx["content"][field] = "x"
    with pytest.raises(ValueError):
        s.Context.from_jsonable(ctx)


def test_visible_serializations_contain_no_private_keys_or_values():
    ex = fx.build_examples()
    private = {"private_episode", "carbon_observation_private"}
    for name, rec in ex.items():
        text = rec.to_json()
        if name in private:
            continue
        s.assert_no_private_keys(rec.to_jsonable())
        for token in ("scenario_id", "hand-example", "realized", "FACT-OBS", "oracle", "seed"):
            assert token not in text, f"{token!r} leaked into {name}"


def test_private_episode_does_carry_private_data_and_is_not_a_visible_state():
    pe = fx.private_episode()
    assert pe.split == "development" and len(pe.realized_carbon) == 7
    with pytest.raises(ValueError):
        s.VisibleState.from_jsonable(pe.to_jsonable())


def test_assert_no_private_keys_finds_nested_leak():
    with pytest.raises(ValueError, match="seed"):
        s.assert_no_private_keys({"a": [{"b": {"seed": 1}}]})


def test_visible_state_carbon_facts_reject_observations():
    obs = fx.observations()[0].to_jsonable()
    state = fx.visible_state().to_jsonable()
    state["carbon_facts"] = [obs]
    with pytest.raises(ValueError):
        s.VisibleState.from_jsonable(state)


@pytest.mark.parametrize(
    "bad", ["EP-heldout1", "EP-DEV1", "EP-test", "EP-seed7", "EP_1", "J1", "EP-"]
)
def test_episode_id_must_be_opaque_and_well_formed(bad):
    with pytest.raises(ValueError):
        s.VisibleState(**{**fx.visible_state().model_dump(), "episode_id": bad})


# ---------------------------------------------------------------- 7. observation vs forecast
def test_forecast_requires_issue_time_and_observation_forbids_it():
    f = fx.forecasts()[0].to_jsonable()
    del f["issued_at_utc"]
    with pytest.raises(ValueError, match="issued_at_utc"):
        s.CarbonForecast.from_jsonable(f)
    o = fx.observations()[0].to_jsonable()
    with pytest.raises(ValueError):
        s.CarbonObservation.from_jsonable({**o, "issued_at_utc": "2022-01-01T07:00:00Z"})
    f2 = fx.forecasts()[0].to_jsonable()
    with pytest.raises(ValueError):  # observation time must not be reused on a forecast
        s.CarbonForecast.from_jsonable({**f2, "observed_at_utc": "2022-01-01T07:00:00Z"})


def test_fact_kind_has_no_default_confusion():
    f = fx.forecasts()[0].to_jsonable()
    assert f["fact_kind"] == "forecast"
    with pytest.raises(ValueError):
        s.CarbonForecast.from_jsonable({**f, "fact_kind": "observation"})
    with pytest.raises(ValueError):
        s.CarbonObservation.from_jsonable({**f, "fact_kind": "forecast"})
    parsed = s.parse_record(fx.observations()[0].to_jsonable())
    assert isinstance(parsed, s.CarbonObservation)


def test_forecast_needs_semantics_stated_explicitly():
    f = fx.forecasts()[0].to_jsonable()
    del f["semantics"]
    with pytest.raises(ValueError):
        s.CarbonForecast.from_jsonable(f)
    f = fx.forecasts()[0].to_jsonable()
    del f["forecast_kind"]
    with pytest.raises(ValueError):
        s.CarbonForecast.from_jsonable(f)


def test_unresolved_q05_semantics_are_representable_but_not_overclaimed():
    sem = fx.semantics()
    assert (sem.pollutant_basis, sem.interval_convention) == ("unresolved", "unresolved")
    with pytest.raises(ValueError, match="agreed"):
        s.CarbonSemantics(
            pollutant_basis="co2e",
            interval_convention="unresolved",
            emissions_factor_type="average",
            slot_mapping_status="agreed",
        )
    base = fx.forecasts()[0].model_dump()
    with pytest.raises(ValueError, match="interval convention"):  # interval needs a convention
        s.CarbonForecast(
            **{**base, "valid_from_utc": fx.SLOT0_UTC, "valid_to_utc": fx.SLOT0_UTC.replace(hour=8)}
        )
    with pytest.raises(ValueError, match="slot mapping"):
        s.CarbonForecast(
            **{
                **base,
                "semantics": s.CarbonSemantics(
                    pollutant_basis="unresolved",
                    interval_convention="unresolved",
                    emissions_factor_type="average",
                    slot_mapping_status="unresolved",
                ),
            }
        )


# ---------------------------------------------------------------- 8. units, sources, timestamps
def test_required_units_and_sources():
    f = fx.forecasts()[0].to_jsonable()
    for key in ("unit", "source_id", "valid_slot", "fact_id"):
        broken = {k: v for k, v in f.items() if k != key}
        with pytest.raises(ValueError):
            s.CarbonForecast.from_jsonable(broken)
    with pytest.raises(ValueError):
        s.CarbonForecast.from_jsonable({**f, "unit": "kg"})  # wrong dimension for carbon intensity
    with pytest.raises(ValueError):
        s.CarbonForecast.from_jsonable(
            {**f, "unit": "g CO2e/kWh"}
        )  # unit must not smuggle pollutant


@pytest.mark.parametrize(
    "ctype,unit,site,jobs",
    [
        ("capacity", "slot", "SITE1", ()),  # wrong unit
        ("capacity", "kW", None, ("J1",)),  # capacity must apply to a site
        ("deadline", "slot", "SITE1", ()),  # deadline must apply to jobs
        ("deadline", "kW", None, ("J1",)),
        ("freshness", "slot", None, ()),  # applies to nothing
        ("freshness", "slot", "SITE1", ("J1",)),  # applies to both
    ],
)
def test_constraint_type_unit_and_applicability(ctype, unit, site, jobs):
    with pytest.raises(ValueError):
        s.Constraint(
            constraint_id="CON-X-1",
            constraint_type=ctype,
            limit_value=5,
            unit=unit,
            applies_to_site=site,
            applies_to_jobs=jobs,
            source_id="SRC-HAND",
        )


def test_constraint_id_prefix_and_slot_limit_integrality():
    base = dict(
        constraint_type="freshness",
        limit_value=2,
        unit="slot",
        applies_to_site="SITE1",
        source_id="SRC",
    )
    with pytest.raises(ValueError):
        s.Constraint(constraint_id="CAP-1", **base)
    with pytest.raises(ValueError):
        s.Constraint(constraint_id="CON-F", **{**base, "limit_value": 2.5})


@pytest.mark.parametrize(
    "bad",
    [
        "2022-01-01",
        "2022-01-01T07:00:00",
        "2022-01-01T07:00:00-07:00",
        "not a time",
        "",
        1641020400,
        None,
    ],
)
def test_malformed_or_non_utc_timestamps_rejected(bad):
    f = fx.forecasts()[0].to_jsonable()
    with pytest.raises(ValueError):
        s.CarbonForecast.from_jsonable({**f, "issued_at_utc": bad})


def test_utc_timestamps_normalised_and_serialised_with_z():
    f = fx.forecasts()[0].to_jsonable()
    ok = s.CarbonForecast.from_jsonable({**f, "issued_at_utc": "2022-01-01T07:00:00+00:00"})
    assert ok.to_jsonable()["issued_at_utc"] == "2022-01-01T07:00:00Z"


def test_invalid_interval_structure():
    base = fx.observations()[0].model_dump()
    sem = s.CarbonSemantics(
        pollutant_basis="unresolved",
        interval_convention="hour_end",
        emissions_factor_type="average",
        slot_mapping_status="provisional",
    )
    t0 = fx.SLOT0_UTC
    with pytest.raises(ValueError, match="together"):
        s.CarbonObservation(**{**base, "semantics": sem, "valid_from_utc": t0})
    with pytest.raises(ValueError, match="after"):
        s.CarbonObservation(**{**base, "semantics": sem, "valid_from_utc": t0, "valid_to_utc": t0})


def test_site_and_job_structural_ranges():
    with pytest.raises(ValueError):
        s.SiteConfig(site_id="S", background_kw=40, pue=0.9, slot_hours=1)  # PUE below 1
    with pytest.raises(ValueError):
        s.SiteConfig(site_id="S", background_kw=-1, pue=1.0, slot_hours=1)
    with pytest.raises(ValueError):
        s.SiteConfig(site_id="S", background_kw=40, pue=1.0, slot_hours=0)


# ---------------------------------------------------------------- versions
@pytest.mark.parametrize("bad", ["2.0.0", "1.99.0", "0.9.0", "1.0", "v1", "", 1])
def test_invalid_or_unsupported_schema_versions_rejected(bad):
    with pytest.raises(ValueError):
        s.Job.from_jsonable({**fx.jobs()["J1"].to_jsonable(), "schema_version": bad})


def test_older_compatible_minor_versions_accepted_only_if_not_newer():
    assert s.Job.from_jsonable({**fx.jobs()["J1"].to_jsonable(), "schema_version": "1.0.0"})
    assert s.SCHEMA_VERSION == "1.0.0"


def test_parse_record_dispatch_and_unknown_type():
    with pytest.raises(ValueError, match="record_type"):
        s.parse_record({"record_type": "Nope"})
    with pytest.raises(ValueError, match="record_type"):
        s.parse_record({})


# ---------------------------------------------------------------- 9. round trips + committed examples
@pytest.mark.parametrize("name", sorted(fx.build_examples()))
def test_every_example_round_trips_with_stable_names_and_version(name):
    rec = fx.build_examples()[name]
    data = rec.to_jsonable()
    assert data["schema_version"] == s.SCHEMA_VERSION
    assert data["record_type"] == type(rec).model_fields["record_type"].default
    assert s.parse_record(data) == rec
    assert type(rec).from_json(rec.to_json()) == rec
    assert type(rec).from_json(rec.to_json()).to_json() == rec.to_json()
    assert rec.canonical_hash() == s.parse_record(data).canonical_hash()


@pytest.mark.parametrize("name", sorted(fx.build_examples()))
def test_committed_example_files_match_builders(name):
    path = Path(fx.EXAMPLES_DIR) / f"{name}.json"
    assert path.exists(), "run: python -m tests.contracts.fixtures"
    assert json.loads(path.read_text()) == fx.build_examples()[name].to_jsonable()
    assert s.parse_record(json.loads(path.read_text())) == fx.build_examples()[name]


# ---------------------------------------------------------------- 10. context hashing
def test_context_hash_deterministic_and_order_independent():
    snap, state = fx.snapshot(), fx.visible_state()
    a = s.Context.build(state, snap, "flat")
    b = s.Context.build(state, snap, "flat")
    assert a.content_hash == b.content_hash and a.to_json() == b.to_json()
    shuffled_state = s.VisibleState(
        **{
            **state.model_dump(),
            "waiting_jobs": tuple(reversed(state.waiting_jobs)),
            "carbon_facts": tuple(reversed(state.carbon_facts)),
            "constraint_ids": tuple(reversed(state.constraint_ids)),
        }
    )
    shuffled_snap = s.ConstraintSnapshot(
        **{**snap.model_dump(), "constraints": tuple(reversed(snap.constraints))}
    )
    c = s.Context.build(shuffled_state, shuffled_snap, "flat")
    assert c.content_hash == a.content_hash
    assert shuffled_state.canonical_hash() == state.canonical_hash()


def test_graph_and_flat_representations_share_one_content_hash():
    snap, state = fx.snapshot(), fx.visible_state()
    graph = s.Context.build(state, snap, "graph")
    flat = s.Context.build(state, snap, "flat")
    assert graph.representation != flat.representation
    assert graph.content_hash == flat.content_hash


def test_context_hash_changes_when_a_fact_or_constraint_changes():
    state = fx.visible_state()
    base = s.Context.build(state, fx.snapshot(), "flat").content_hash
    cap70 = fx.snapshot(capacity_kw=70.0)
    assert s.Context.build(state, cap70, "flat").content_hash != base  # K03 precondition
    changed = fx.visible_state(current_slot=1)
    assert s.Context.build(changed, fx.snapshot(), "flat").content_hash != base


def test_context_detects_tampered_hash_and_mismatched_inputs():
    ctx = s.Context.build(fx.visible_state(), fx.snapshot(), "flat").to_jsonable()
    ctx["content_hash"] = "f" * 64
    with pytest.raises(ValueError, match="content_hash"):
        s.Context.from_jsonable(ctx)
    with pytest.raises(ValueError, match="snapshot"):
        s.Context.build(
            fx.visible_state(),
            s.ConstraintSnapshot(**{**fx.snapshot().model_dump(), "snapshot_id": "OTHER"}),
            "flat",
        )
    with pytest.raises(ValueError, match="constraint ids"):
        s.Context.build(fx.visible_state(), fx.snapshot(include_capacity=False), "flat")


def test_context_evidence_ids_cover_visible_records_only():
    ids = set(s.Context.build(fx.visible_state(), fx.snapshot(), "flat").content.evidence_ids)
    assert {"FACT-JOB-J1", "FACT-JOB-J2", "FACT-CI-s00", "CON-CAP-01", "FACT-SITE-BG"} <= ids
    assert not any(i.startswith("FACT-OBS") for i in ids) and "FACT-JOB-J3" not in ids


# ---------------------------------------------------------------- visible state invariants
def test_visible_state_invariants():
    st = fx.visible_state().model_dump()
    j = fx.jobs()
    with pytest.raises(ValueError, match="not arrived"):  # future arrival cannot be 'waiting'
        s.VisibleState(**{**st, "waiting_jobs": (j["J3"],)})
    with pytest.raises(ValueError, match="after the current slot"):
        s.VisibleState(
            **{
                **st,
                "waiting_jobs": (),
                "running_jobs": (s.RunningJobView(job=j["J1"], start_slot=3),),
            }
        )
    with pytest.raises(ValueError, match="both present and listed missing"):
        s.VisibleState(**{**st, "missing_carbon_slots": (0,)})


def test_running_occupancy_is_half_open():
    j = fx.jobs()
    st = s.VisibleState(
        **{
            **fx.visible_state(current_slot=1).model_dump(),
            "waiting_jobs": (),
            "running_jobs": (s.RunningJobView(job=j["J1"], start_slot=0),),
        }
    )
    assert [st.running_job_load_kw(i) for i in range(3)] == [40.0, 40.0, 0.0]


def test_visible_state_rejects_running_jobs_that_have_already_ended():
    j = fx.jobs()["J1"]  # starts at 0, duration 2, exclusive end 2
    base = fx.visible_state(current_slot=2).model_dump()
    with pytest.raises(ValueError, match="must still occupy the current slot"):
        s.VisibleState(
            **{
                **base,
                "waiting_jobs": (),
                "running_jobs": (s.RunningJobView(job=j, start_slot=0),),
            }
        )


def test_visible_state_rejects_invalid_completed_job_intervals():
    base = fx.visible_state(current_slot=2).model_dump()
    bad_intervals = (
        s.CompletedJobView(job_id="J9", start_slot=2, end_slot=2),
        s.CompletedJobView(job_id="J9", start_slot=0, end_slot=3),
    )
    for completed in bad_intervals:
        with pytest.raises(ValueError, match="completed jobs must have"):
            s.VisibleState(
                **{
                    **base,
                    "waiting_jobs": (),
                    "completed_jobs": (completed,),
                }
            )
    good = s.VisibleState(
        **{
            **base,
            "waiting_jobs": (),
            "completed_jobs": (s.CompletedJobView(job_id="J9", start_slot=0, end_slot=2),),
        }
    )
    assert good.completed_jobs[0].end_slot == 2


def test_missing_forecast_slots_are_explicit_not_fabricated():
    st = s.VisibleState(
        **{
            **fx.visible_state().model_dump(),
            "carbon_facts": fx.forecasts()[:5],
            "missing_carbon_slots": (5, 6),
        }
    )
    assert len(st.carbon_facts) == 5 and st.missing_carbon_slots == (5, 6)


# ---------------------------------------------------------------- capacity evidence (K03 groundwork)
def test_capacity_is_a_single_authoritative_constraint_and_absence_is_not_unlimited():
    assert fx.snapshot().capacity_kw == 100.0
    assert fx.snapshot(capacity_kw=70.0).capacity_kw == 70.0
    with pytest.raises(s.MissingEvidenceError):
        fx.snapshot(include_capacity=False).capacity_kw
    assert "capacity_kw" not in s.SiteConfig.model_fields  # no second copy that could disagree


def test_snapshot_rejects_unknown_site_or_source():
    snap = fx.snapshot().model_dump()
    bad = {**snap["constraints"][0], "applies_to_site": "OTHER"}
    with pytest.raises(ValueError, match="unknown site"):
        s.ConstraintSnapshot(**{**snap, "constraints": (s.Constraint(**bad),)})
    bad = {**snap["constraints"][0], "source_id": "SRC-MISSING"}
    with pytest.raises(ValueError, match="unknown sources"):
        s.ConstraintSnapshot(**{**snap, "constraints": (s.Constraint(**bad),)})


# ---------------------------------------------------------------- check results
def test_check_result_consistency_rules():
    p = fx.plan()
    base = dict(
        check_id="CHK-1",
        episode_id=p.episode_id,
        slot=0,
        state_version=0,
        plan_hash=p.plan_hash,
        impact_claim_support="not_assessed",
    )
    cap = (s.EvidenceItem(kind="capacity", status="available", ids=("CON-CAP-01",)),)
    ok = tuple(
        s.PerformedCheck(
            name=name,
            outcome="pass",
            constraint_ids=("CON-CAP-01",) if name == "capacity" else (),
        )
        for name in ("schema", "ids", "timing", "deadline", "nonflexible", "capacity")
    )
    with pytest.raises(ValueError, match="actually performed"):  # unperformed checks never pass
        s.CheckResult(**base, status="pass", evidence=cap)
    with pytest.raises(ValueError, match="capacity evidence"):  # missing capacity != unlimited
        s.CheckResult(
            **base,
            status="pass",
            performed=ok,
            evidence=(s.EvidenceItem(kind="capacity", status="missing"),),
        )
    with pytest.raises(ValueError, match="capacity evidence"):
        s.CheckResult(**base, status="pass", performed=ok)
    with pytest.raises(ValueError, match="violation"):
        s.CheckResult(**base, status="fail", performed=ok, evidence=cap)
    with pytest.raises(ValueError, match="error"):
        s.CheckResult(**base, status="error", evidence=cap)
    with pytest.raises(ValueError, match="failed/error"):
        s.CheckResult(
            **base,
            status="pass",
            evidence=cap,
            performed=(s.PerformedCheck(name="capacity", outcome="fail"),),
        )
    fail = s.CheckResult(
        **base,
        status="fail",
        evidence=cap,
        performed=(
            s.PerformedCheck(name="capacity", outcome="fail", constraint_ids=("CON-CAP-01",)),
        ),
        violations=(
            s.Violation(
                violation_type="capacity",
                job_ids=("J1", "J2"),
                constraint_ids=("CON-CAP-01",),
                slot=0,
                message="110 kW > 100 kW",
            ),
        ),
    )
    assert fail.status == "fail"
    with pytest.raises(ValueError, match="failed performed check"):
        s.CheckResult(
            **base,
            status="fail",
            evidence=cap,
            performed=ok,
            violations=fail.violations,
        )


def test_feasibility_and_impact_claim_support_are_separate_fields():
    chk = fx.check_pass()
    unsupported = s.CheckResult(
        **{**chk.model_dump(), "impact_claim_support": "unsupported", "evidence": chk.evidence + ()}
    )
    assert unsupported.status == "pass" and unsupported.impact_claim_support == "unsupported"


# ---------------------------------------------------------------- decision records
def test_decision_record_never_implies_passing_stages():
    rec = fx.decision_record()
    assert rec.repaired is None and rec.fallback is None
    assert set(rec.not_applicable_stages) == {"repaired", "fallback"}
    stage = s.StageRecord(plan=fx.plan())
    assert stage.check is None  # unchecked stays unchecked


def test_decision_record_execution_gate_consistency():
    d = fx.decision_record().model_dump()
    with pytest.raises(ValueError, match="passing execution_check"):
        s.DecisionRecord(**{**d, "execution_check": None})
    with pytest.raises(ValueError, match="passing execution_check"):
        s.DecisionRecord(**{**d, "execution_check": fx.check_missing_capacity()})
    with pytest.raises(ValueError, match="exactly match"):
        s.DecisionRecord(**{**d, "executed_starts": (s.ApprovedStart(job_id="J2", start_slot=0),)})
    with pytest.raises(ValueError, match="exactly match"):
        s.DecisionRecord(**{**d, "executed_starts": ()})
    with pytest.raises(ValueError, match="not applicable"):
        s.DecisionRecord(**{**d, "not_applicable_stages": ("initial",)})
    other = fx.abstention_plan()
    with pytest.raises(ValueError, match="different plan"):
        s.StageRecord(plan=other, check=fx.check_pass())


def test_decision_record_numbers_validated():
    d = fx.decision_record().model_dump()
    for key, bad in (
        ("latency_ms", -1.0),
        ("cost_usd", float("nan")),
        ("model_call_count", True),
        ("prompt_tokens", 1.5),
        ("repair_count", -1),
    ):
        with pytest.raises(ValueError):
            s.DecisionRecord(**{**d, key: bad})


def test_policy_output_envelope():
    with pytest.raises(ValueError, match="requires a plan"):
        s.PolicyOutput(system="plain_llm", output_status="ok")
    with pytest.raises(ValueError, match="may only accompany"):
        s.PolicyOutput(
            system="plain_llm", output_status="malformed", plan=fx.plan(), raw_response="{"
        )
    bad = s.PolicyOutput(system="plain_llm", output_status="malformed", raw_response="not json")
    assert bad.plan is None
    with pytest.raises(ValueError):
        s.PolicyOutput(system="model_x", output_status="ok", plan=fx.plan())


def test_explanation_claim_value_needs_unit_and_unique_ids():
    with pytest.raises(ValueError, match="together"):
        s.Claim(claim_id="C1", text="x", value=1.0)
    c = s.Claim(claim_id="C1", text="x")
    with pytest.raises(ValueError, match="duplicate"):
        s.Explanation(source="llm", summary="x", claims=(c, c))


# ---------------------------------------------------------------- solver results
def solver(**over):
    base = fx.solver_result().model_dump()
    return s.SolverResult(**{**base, **over})


def test_solver_statuses_are_distinct_and_never_inferred_from_timeouts():
    assert solver().status == "certified_optimal"
    inf = solver(
        status="certified_infeasible",
        objective_kg=None,
        schedule=None,
        certification_basis="infeasibility proof",
    )
    assert inf.status == "certified_infeasible"
    unresolved = solver(
        status="unresolved",
        objective_kg=None,
        schedule=None,
        certification_basis=None,
        unresolved_reason="time limit",
        termination="time_limit",
    )
    assert unresolved.schedule is None
    for status in ("unresolved", "insufficient_evidence"):
        with pytest.raises(ValueError, match="unresolved_reason"):
            solver(status=status, objective_kg=None, schedule=None, certification_basis=None)
        with pytest.raises(ValueError):  # a timeout incumbent is not a certified optimum
            solver(status=status, unresolved_reason="time limit", certification_basis=None)


def test_solver_certification_and_visibility_rules():
    with pytest.raises(ValueError, match="certification_basis"):
        solver(certification_basis=None)
    with pytest.raises(ValueError, match="certified_optimal requires"):
        solver(schedule=None)
    with pytest.raises(ValueError, match="cannot carry an objective"):
        solver(status="certified_infeasible")
    with pytest.raises(ValueError, match="future arrivals"):
        solver(kind="visible", uses_future_arrivals=True)
    with pytest.raises(ValueError, match="hindsight"):
        solver(kind="hindsight", uses_future_arrivals=False)
    with pytest.raises(ValueError):
        solver(offline_only=False)
    with pytest.raises(ValueError):  # offline references can never be a visible-state field
        s.VisibleState.from_jsonable(
            {**fx.visible_state().to_jsonable(), "solver_result": solver().to_jsonable()}
        )


# ---------------------------------------------------------------- episode results
def test_episode_result_shape_and_partitions():
    r = fx.episode_result().model_dump()
    with pytest.raises(ValueError, match="contiguous"):
        s.EpisodeResult(**{**r, "slots": r["slots"][:-1]})
    bad_phase = list(r["slots"])
    bad_phase[24] = {**bad_phase[24], "phase": "decision"}
    with pytest.raises(ValueError, match="phase"):
        s.EpisodeResult(**{**r, "slots": bad_phase})
    with pytest.raises(ValueError, match="both completed and missed"):
        s.EpisodeResult(**{**r, "deadline_missed_job_ids": ("J1",)})
    with pytest.raises(ValueError, match="more completed"):
        s.EpisodeResult(**{**r, "job_count_total": 1})
    assert fx.episode_result().totals.site_emissions_kg is None  # no invented calculations
    with pytest.raises(ValueError):
        s.CompletedWork(value=1.0, unit="kWh")  # definition (Q03) is required


def test_extra_fields_cannot_smuggle_calculations_into_slot_records():
    with pytest.raises(ValueError):
        s.SlotRecord(
            slot=0, phase="decision", job_load_kw=0, background_load_kw=40, emissions_factor=1.2
        )

# ---------------------------------------------------------------- additional F02 review regressions

def test_policy_context_does_not_leak_constraints_for_future_jobs():
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    context = s.Context.build(state, snap, "flat")
    visible_constraint_ids = {c.constraint_id for c in context.content.constraints}
    assert "CON-DL-J3" not in visible_constraint_ids
    assert "CON-DL-J3" not in state.constraint_ids
    serialized = context.to_json()
    assert "J3" not in serialized


def test_job_constraint_becomes_visible_after_job_arrives():
    snap = fx.snapshot()
    state = fx.visible_state(
        snap,
        current_slot=4,
        waiting_job_ids=("J3",),
        completed_job_ids=("J1", "J2"),
    )
    context = s.Context.build(state, snap, "flat")
    visible_constraint_ids = {c.constraint_id for c in context.content.constraints}
    assert "CON-DL-J3" in visible_constraint_ids
    assert "FACT-JOB-J3" in context.content.evidence_ids


def test_context_contains_referenced_source_provenance():
    context = s.Context.build(fx.visible_state(), fx.snapshot(), "flat")
    source_ids = {source.source_id for source in context.content.sources}
    assert "SRC-HAND" in source_ids
    assert all(source.redistribution_status for source in context.content.sources)


def test_checked_plan_rejects_check_from_different_episode_or_slot():
    plan = fx.plan("approved")
    check = fx.check_pass(plan)
    with pytest.raises(ValueError, match="episode"):
        s.ApprovedActions.from_checked_plan(
            plan,
            check.model_copy(update={"episode_id": "EP-OTHER"}),
            expected_state_version=0,
        )
    with pytest.raises(ValueError, match="slot"):
        s.ApprovedActions.from_checked_plan(
            plan,
            check.model_copy(update={"slot": 1}),
            expected_state_version=0,
        )


def test_decision_record_rejects_execution_check_from_different_episode_or_slot():
    record = fx.decision_record()
    bad_episode_check = record.execution_check.model_copy(update={"episode_id": "EP-OTHER"})
    with pytest.raises(ValueError, match="episode"):
        s.DecisionRecord(
            **{**record.model_dump(), "execution_check": bad_episode_check}
        )
    bad_slot_check = record.execution_check.model_copy(update={"slot": 1})
    with pytest.raises(ValueError, match="slot"):
        s.DecisionRecord(
            **{**record.model_dump(), "execution_check": bad_slot_check}
        )


def test_versioned_json_deserialization_requires_explicit_envelope():
    data = fx.jobs()["J1"].to_jsonable()
    missing_type = dict(data)
    del missing_type["record_type"]
    with pytest.raises(ValueError, match="record_type"):
        s.Job.from_jsonable(missing_type)
    missing_version = dict(data)
    del missing_version["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        s.Job.from_jsonable(missing_version)
    with pytest.raises(ValueError, match="record_type"):
        s.Job.from_json(json.dumps(missing_type))
    with pytest.raises(ValueError, match="schema_version"):
        s.Job.from_json(json.dumps(missing_version))


def test_schema_version_rejects_trailing_newline():
    data = fx.jobs()["J1"].to_jsonable()
    with pytest.raises(ValueError, match="schema_version"):
        s.Job.from_jsonable({**data, "schema_version": "1.0.0\n"})


def test_nested_unordered_constraint_jobs_hash_identically():
    c1 = s.Constraint(
        constraint_id="CON-NF-J1-J2",
        constraint_type="nonflexible",
        limit_value=0,
        unit="slot",
        applies_to_jobs=("J1", "J2"),
        source_id="SRC-HAND",
    )
    c2 = s.Constraint(
        **{**c1.model_dump(), "applies_to_jobs": tuple(reversed(c1.applies_to_jobs))}
    )
    assert c1.canonical_hash() == c2.canonical_hash()
    snap = fx.snapshot()
    snap1 = s.ConstraintSnapshot(
        **{**snap.model_dump(), "constraints": snap.constraints + (c1,)}
    )
    snap2 = s.ConstraintSnapshot(
        **{**snap.model_dump(), "constraints": snap.constraints + (c2,)}
    )
    assert snap1.canonical_hash() == snap2.canonical_hash()


def test_solver_schedule_and_per_slot_job_id_sets_hash_identically_when_reordered():
    result = fx.solver_result()
    reversed_schedule = s.SolverResult(
        **{
            **result.model_dump(),
            "schedule": tuple(reversed(result.schedule)),
        }
    )
    assert result.canonical_hash() == reversed_schedule.canonical_hash()

    episode = fx.episode_result()
    slots = list(episode.slots)
    slots[0] = s.SlotRecord(
        **{
            **slots[0].model_dump(),
            "started_job_ids": ("J1", "J2"),
            "running_job_ids": ("J2", "J1"),
            "completed_job_ids": ("J1", "J2"),
        }
    )
    reordered = s.EpisodeResult(**{**episode.model_dump(), "slots": tuple(slots)})
    slots[0] = s.SlotRecord(
        **{
            **slots[0].model_dump(),
            "started_job_ids": ("J2", "J1"),
            "running_job_ids": ("J1", "J2"),
            "completed_job_ids": ("J2", "J1"),
        }
    )
    reordered_ids = s.EpisodeResult(**{**episode.model_dump(), "slots": tuple(slots)})
    assert reordered.canonical_hash() == reordered_ids.canonical_hash()


def test_unordered_episode_job_id_collections_hash_identically():
    result = fx.episode_result()
    reordered = s.EpisodeResult(
        **{
            **result.model_dump(),
            "completed_job_ids": tuple(reversed(result.completed_job_ids)),
        }
    )
    assert result.canonical_hash() == reordered.canonical_hash()


def test_plan_future_intentions_excludes_backdated_starts():
    plan = s.Plan(
        episode_id="EP-A",
        slot=3,
        state_version=3,
        status="proposed",
        starts=(
            s.PlannedStart(job_id="J1", start_slot=2),
            s.PlannedStart(job_id="J2", start_slot=4),
        ),
    )
    assert [start.job_id for start in plan.future_intentions] == ["J2"]


def test_context_rejects_conflicting_job_and_deadline_constraint():
    snap = fx.snapshot()
    altered = tuple(
        s.Constraint(**{**c.model_dump(), "limit_value": 5})
        if c.constraint_id == "CON-DL-J1"
        else c
        for c in snap.constraints
    )
    inconsistent_snap = s.ConstraintSnapshot(
        **{**snap.model_dump(), "constraints": altered}
    )
    state = fx.visible_state(inconsistent_snap)
    with pytest.raises(ValueError, match="deadline limit conflicts"):
        s.Context.build(state, inconsistent_snap, "flat")


def test_constraint_snapshot_rejects_missing_source_records():
    snap = fx.snapshot()
    with pytest.raises(ValueError, match="unknown sources"):
        s.ConstraintSnapshot(**{**snap.model_dump(), "sources": ()})


def test_context_rejects_visible_fact_with_unresolved_source_reference():
    snap = fx.snapshot()
    forecasts = tuple(
        s.CarbonForecast(**{**f.model_dump(), "source_id": "SRC-MISSING"})
        for f in fx.forecasts()
    )
    state = fx.visible_state(snap)
    state = s.VisibleState(**{**state.model_dump(), "carbon_facts": forecasts})
    with pytest.raises(ValueError, match="missing source records"):
        s.Context.build(state, snap, "flat")


def test_decision_record_rejects_execution_check_for_unrecorded_plan():
    record = fx.decision_record()
    bad_check = record.execution_check.model_copy(update={"plan_hash": "f" * 64})
    with pytest.raises(ValueError, match="recorded stage plan"):
        s.DecisionRecord(**{**record.model_dump(), "execution_check": bad_check})


def test_deserialized_context_cannot_drop_source_provenance_or_evidence_ids():
    context = s.Context.build(fx.visible_state(), fx.snapshot(), "flat")
    data = context.to_jsonable()

    without_sources = json.loads(json.dumps(data))
    without_sources["content"]["sources"] = []
    without_sources["content_hash"] = s.ContextContent.from_jsonable(
        without_sources["content"]
    ).canonical_hash()
    with pytest.raises(ValueError, match="source provenance"):
        s.Context.from_jsonable(without_sources)

    without_evidence = json.loads(json.dumps(data))
    without_evidence["content"]["evidence_ids"] = []
    without_evidence["content_hash"] = s.ContextContent.from_jsonable(
        without_evidence["content"]
    ).canonical_hash()
    with pytest.raises(ValueError, match="evidence IDs"):
        s.Context.from_jsonable(without_evidence)


def test_deserialized_context_rejects_hidden_job_constraint_even_with_rehashed_content():
    context = s.Context.build(fx.visible_state(), fx.snapshot(), "flat")
    data = context.to_jsonable()
    hidden_constraint = next(
        constraint.model_dump(mode="json")
        for constraint in fx.snapshot().constraints
        if constraint.constraint_id == "CON-DL-J3"
    )
    data["content"]["constraints"].append(hidden_constraint)
    data["content"]["evidence_ids"].append("CON-DL-J3")
    data["content_hash"] = s.ContextContent.from_jsonable(data["content"]).canonical_hash()
    with pytest.raises(ValueError, match="not-yet-visible job"):
        s.Context.from_jsonable(data)


def test_context_rejects_unreferenced_source_records_that_could_leak_private_metadata():
    context = s.Context.build(fx.visible_state(), fx.snapshot(), "flat")
    data = context.to_jsonable()
    extra_source = fx.source().model_dump(mode="json")
    extra_source["source_id"] = "SRC-FUTURE"
    extra_source["path"] = "private/future-job-fixture.csv"
    data["content"]["sources"].append(extra_source)
    data["content_hash"] = s.ContextContent.from_jsonable(
        data["content"]
    ).canonical_hash()
    with pytest.raises(ValueError, match="unrelated source records"):
        s.Context.from_jsonable(data)


def test_context_content_rejects_duplicate_nested_identifiers():
    context = s.Context.build(fx.visible_state(), fx.snapshot(), "flat")
    content = context.content.model_dump()
    content["sources"] = context.content.sources + context.content.sources
    with pytest.raises(ValueError, match="duplicate context source ids"):
        s.ContextContent(**content)



def test_visible_state_from_snapshot_projects_only_currently_visible_constraint_ids():
    snap = fx.snapshot()
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id=fx.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=(fx.jobs()["J1"], fx.jobs()["J2"]),
        carbon_facts=fx.forecasts(),
    )
    assert "CON-DL-J1" in state.constraint_ids
    assert "CON-DL-J3" not in state.constraint_ids
    assert "CON-DL-J3" not in s.Context.build(state, snap, "flat").to_json()


def test_context_rejects_constraint_ids_copied_from_the_full_snapshot():
    snapshot = fx.snapshot()
    state = fx.visible_state(snapshot)
    leaked_state = s.VisibleState(
        **{
            **state.model_dump(),
            "constraint_ids": state.constraint_ids + ("CON-DL-J3",),
        }
    )
    # VisibleState stores constraint IDs without the associated Constraint records, so its
    # standalone structure cannot prove the projection. Context construction has the full
    # authoritative snapshot and must reject a future-job ID copied into that state.
    with pytest.raises(ValueError, match="constraint ids"):
        s.Context.build(leaked_state, snapshot, "flat")


def test_visible_state_rejects_past_or_out_of_episode_carbon_slots():
    state = fx.visible_state()
    with pytest.raises(ValueError, match="visible episode horizon"):
        s.VisibleState(
            **{**state.model_dump(), "current_slot": 1, "carbon_facts": fx.forecasts()}
        )
    future_forecast = s.CarbonForecast(
        **{**fx.forecasts()[0].model_dump(), "valid_slot": 30}
    )
    with pytest.raises(ValueError, match="visible episode horizon"):
        s.VisibleState(**{**state.model_dump(), "carbon_facts": (future_forecast,)})
    with pytest.raises(ValueError, match="visible episode horizon"):
        s.VisibleState(**{**state.model_dump(), "missing_carbon_slots": (30,)})


def test_passing_check_requires_every_core_safety_check_and_traceable_capacity():
    baseline = fx.check_pass().to_jsonable()
    baseline["performed"] = [
        check for check in baseline["performed"] if check["name"] != "nonflexible"
    ]
    with pytest.raises(ValueError, match="core checks"):
        s.CheckResult.from_jsonable(baseline)

    baseline = fx.check_pass().to_jsonable()
    baseline["evidence"] = [
        {**evidence, "ids": ["FACT-CI-s00"]} if evidence["kind"] == "capacity" else evidence
        for evidence in baseline["evidence"]
    ]
    with pytest.raises(ValueError, match="capacity evidence"):
        s.CheckResult.from_jsonable(baseline)


def test_constraint_snapshot_rejects_multiple_capacity_limits():
    snap = fx.snapshot()
    capacity = next(item for item in snap.constraints if item.constraint_type == "capacity")
    second = s.Constraint(
        **{**capacity.to_jsonable(), "constraint_id": "CON-CAP-02", "limit_value": 70.0}
    )
    with pytest.raises(ValueError, match="at most one capacity"):
        s.ConstraintSnapshot(
            **{**snap.to_jsonable(), "constraints": (*snap.constraints, second)}
        )


def test_deserialized_context_rejects_conflicting_job_constraint():
    context = s.Context.build(fx.visible_state(), fx.snapshot(), "flat")
    data = context.to_jsonable()
    changed = []
    for constraint in data["content"]["constraints"]:
        if constraint["constraint_id"] == "CON-DL-J1":
            constraint = {**constraint, "limit_value": 5.0}
        changed.append(constraint)
    data["content"]["constraints"] = changed
    content = s.ContextContent.from_jsonable(data["content"])
    data["content_hash"] = content.canonical_hash()
    with pytest.raises(ValueError, match="deadline limit conflicts"):
        s.Context.from_jsonable(data)


def test_decision_record_rejects_stage_plan_from_another_episode_or_slot():
    record = fx.decision_record()
    original = record.model_dump()
    for changes in (
        {"episode_id": "EP-OTHER"},
        {"slot": 1},
    ):
        bad_plan = s.Plan(
            **{
                **fx.plan().model_dump(),
                **changes,
                "status": "proposed",
            }
        )
        changed = {
            **original,
            "execution_check": None,
            "final_status": "blocked",
            "executed_starts": (),
            "initial": s.StageRecord(plan=bad_plan),
        }
        with pytest.raises(ValueError, match="plan episode/slot"):
            s.DecisionRecord(**changed)


def test_execution_recheck_can_use_a_newer_state_version_for_the_same_slot():
    # The plan was proposed at version 0. The execution gate rechecks it against version 1
    # before applying, then binds ApprovedActions to that exact current version.
    plan = fx.plan("approved")
    original_check = fx.check_pass(plan)
    latest_check = s.CheckResult.from_jsonable(
        {**original_check.to_jsonable(), "check_id": "CHK-LATEST-1", "state_version": 1}
    )
    actions = s.ApprovedActions.from_checked_plan(
        plan, latest_check, expected_state_version=1
    )
    assert actions.state_version == 1
    assert actions.plan_hash == plan.plan_hash

    record = fx.decision_record()
    latest_record = s.DecisionRecord.from_jsonable(
        {**record.to_jsonable(), "execution_check": latest_check.to_jsonable()}
    )
    assert latest_record.execution_check.state_version == 1

    with pytest.raises(ValueError, match="latest expected state version"):
        s.ApprovedActions.from_checked_plan(
            plan, latest_check, expected_state_version=0
        )
    with pytest.raises(ValueError, match="non-negative integer"):
        s.ApprovedActions.from_checked_plan(
            plan, latest_check, expected_state_version=True
        )


def test_executed_trace_must_record_all_and_only_approved_current_starts():
    plan = s.Plan(
        episode_id=fx.EPISODE_ID,
        slot=0,
        state_version=0,
        starts=(
            s.PlannedStart(job_id="J1", start_slot=0),
            s.PlannedStart(job_id="J2", start_slot=0),
        ),
        status="approved",
    )
    check = fx.check_pass(plan)
    with pytest.raises(ValueError, match="exactly match"):
        s.DecisionRecord(
            decision_id="DEC-HAND1-00",
            system="greedy_a",
            run_id="RUN-HAND",
            episode_id=fx.EPISODE_ID,
            slot=0,
            initial=s.StageRecord(plan=plan, check=check),
            not_applicable_stages=("repaired", "fallback"),
            execution_check=check,
            final_status="executed",
            executed_starts=(s.ApprovedStart(job_id="J1", start_slot=0),),
        )


def test_accepted_noop_step_can_be_recorded_as_executed():
    # The clock/running work advances on an accepted empty action set. A plan with only
    # future intentions has no current starts, but the checked step itself can execute.
    p = s.Plan(
        episode_id=fx.EPISODE_ID,
        slot=0,
        state_version=0,
        starts=(s.PlannedStart(job_id="J2", start_slot=2),),
        status="approved",
    )
    chk = fx.check_pass(p)
    record = s.DecisionRecord(
        decision_id="DEC-HAND1-00",
        system="greedy_a",
        run_id="RUN-HAND",
        episode_id=fx.EPISODE_ID,
        slot=0,
        initial=s.StageRecord(plan=p, check=chk),
        not_applicable_stages=("repaired", "fallback"),
        execution_check=chk,
        final_status="executed",
        executed_starts=(),
    )
    assert record.final_status == "executed" and record.executed_starts == ()
