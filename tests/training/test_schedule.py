"""Observable schedule_from_probabilities plans from shared contract fixtures."""

from dc_sustainability import schemas as s
from dc_sustainability.training.schedule import schedule_from_probabilities
from tests.contracts import fixtures as f


class _Classifier:
    def __init__(self, table=None, default=0.5):
        self._table = table or {}
        self._default = default

    def selection_probability(self, job, start_slot):
        return self._table.get((job.job_id, start_slot), self._default)


def _job(**fields):
    return f.jobs()["J2"].model_copy(update=fields)


def _run(waiting, classifier, *, capacity_kw=100.0, running=(), background_kw=None, current_slot=0):
    snap = f.snapshot(capacity_kw=capacity_kw)
    if background_kw is not None:
        snap = snap.model_copy(
            update={"site": snap.site.model_copy(update={"background_kw": background_kw})}
        )
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=current_slot,
        state_version=0,
        waiting_jobs=tuple(waiting),
        running_jobs=tuple(running),
    )
    context = s.Context.build(state, snap, "flat")
    return schedule_from_probabilities(state, context, classifier, system="decision_tree_c")


def _ids(output):
    return tuple(start.job_id for start in output.plan.starts)


def _starts(output):
    return tuple((start.job_id, start.start_slot) for start in output.plan.starts)


def test_injected_classifier_schedules_without_artifact():
    job = _job(job_id="J2")
    output = _run((job,), _Classifier({("J2", 0): 0.9}))
    assert output.system == "decision_tree_c"
    assert output.output_status == "ok"
    assert output.plan.status == "proposed"
    assert _starts(output) == (("J2", 0),), "injected classifier schedules without an artifact"


def test_higher_probability_first():
    low = _job(job_id="JA")
    high = _job(job_id="JB")
    classifier = _Classifier({("JA", 0): 0.2, ("JB", 0): 0.8})
    assert _ids(_run((low, high), classifier)) == ("JB", "JA")


def test_earlier_start_on_probability_tie():
    job = _job(job_id="JT", flexible=True, deadline_slot=8)
    classifier = _Classifier({("JT", 0): 0.5, ("JT", 1): 0.5, ("JT", 2): 0.5})
    assert _starts(_run((job,), classifier)) == (("JT", 0),)


def test_j2_before_j10_when_probability_and_start_tied():
    j2 = _job(job_id="J2")
    j10 = _job(job_id="J10")
    classifier = _Classifier({("J2", 0): 0.5, ("J10", 0): 0.5})
    ids = _ids(_run((j10, j2), classifier))
    assert ids.index("J2") < ids.index("J10")


def test_nonflexible_before_flexible_despite_higher_probability():
    nonflexible = _job(job_id="JN", flexible=False)
    flexible = _job(job_id="JF", flexible=True)
    classifier = _Classifier({("JN", 0): 0.1, ("JF", 0): 0.9})
    assert _ids(_run((flexible, nonflexible), classifier)) == ("JN", "JF")


def test_one_copy_of_duplicate_job_id():
    job = _job(job_id="JD", flexible=True, deadline_slot=10)
    classifier = _Classifier({("JD", 0): 0.9, ("JD", 1): 0.8, ("JD", 2): 0.7})
    output = _run((job,), classifier)
    assert _starts(output) == (("JD", 0),)


def test_capacity_conflict_omits_nonfitting_job():
    oversized = _job(job_id="JH", power_kw=150, duration_slots=1, deadline_slot=6)
    fitting = _job(job_id="JO", power_kw=30, duration_slots=1, deadline_slot=6)
    classifier = _Classifier({("JH", 0): 0.9, ("JO", 0): 0.1})
    assert _ids(_run((oversized, fitting), classifier, capacity_kw=100)) == ("JO",)


def test_future_arrival_is_absent():
    snap = f.snapshot()
    present = _job(job_id="JP")
    future = _job(job_id="JF", arrival_slot=3)
    base = s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=(present,),
    )
    context = s.Context.build(base, snap, "flat")
    state = s.VisibleState.model_construct(
        episode_id=base.episode_id,
        current_slot=base.current_slot,
        state_version=base.state_version,
        site=base.site,
        constraint_snapshot_id=base.constraint_snapshot_id,
        constraint_ids=base.constraint_ids,
        waiting_jobs=(present, future),
        running_jobs=base.running_jobs,
        completed_jobs=base.completed_jobs,
        missed_job_ids=base.missed_job_ids,
        carbon_facts=base.carbon_facts,
        missing_carbon_slots=base.missing_carbon_slots,
    )
    classifier = _Classifier(default=0.5)
    ids = _ids(schedule_from_probabilities(state, context, classifier, system="decision_tree_c"))
    assert "JF" not in ids
    assert ids == ("JP",)
