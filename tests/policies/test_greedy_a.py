"""Observable greedy_a plans built from the shared contract fixtures."""

from dc_sustainability import schemas as s
from dc_sustainability.policies import propose
from tests.contracts import fixtures as f


def _job(**fields):
    return f.jobs()["J2"].model_copy(update=fields)


def _run(waiting, *, capacity_kw=100.0, running=(), background_kw=None, pue=1.0):
    snap = f.snapshot(capacity_kw=capacity_kw, pue=pue)
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=tuple(waiting),
        running_jobs=tuple(running),
    )
    context = s.Context.build(state, snap, "flat")
    if background_kw is not None:
        state = state.model_copy(
            update={"site": state.site.model_copy(update={"background_kw": background_kw})}
        )
    return propose(state, context)


def _ids(output):
    return tuple(start.job_id for start in output.plan.starts)


def test_nonflexible_before_flexible():
    nonflexible = _job(job_id="JN", flexible=False)
    flexible = _job(job_id="JF", flexible=True)
    assert _ids(_run((flexible, nonflexible))) == ("JN", "JF")


def test_earlier_latest_start_first():
    sooner = _job(job_id="JS", deadline_slot=6, duration_slots=2)
    later = _job(job_id="JL", deadline_slot=12, duration_slots=2)
    assert _ids(_run((later, sooner))) == ("JS", "JL")


def test_earlier_deadline_first():
    earlier = _job(job_id="JE", deadline_slot=6, duration_slots=2)
    later = _job(job_id="JD", deadline_slot=8, duration_slots=4)
    assert _ids(_run((later, earlier))) == ("JE", "JD")


def test_j2_before_j10():
    j2 = _job(job_id="J2")
    j10 = _job(job_id="J10")
    ids = _ids(_run((j10, j2)))
    assert ids.index("J2") < ids.index("J10"), "J2 before J10"


def test_start_over_it_capacity_is_absent():
    oversized = _job(job_id="JH", power_kw=150, duration_slots=1)
    fitting = _job(job_id="JO", power_kw=30)
    ids = _ids(_run((oversized, fitting), capacity_kw=100))
    assert "JH" not in ids
    assert ids == ("JO",)


def test_running_job_is_not_a_new_start():
    running = s.RunningJobView(job=f.jobs()["J1"], start_slot=0)
    ids = _ids(_run((_job(job_id="J2"),), running=(running,)))
    assert "J1" not in ids
    assert ids == ("J2",)


def test_empty_waiting_queue():
    output = _run(())
    assert output.system == "greedy_a"
    assert output.plan.status == "proposed" and output.plan.starts == (), "greedy_a plan proposed"


def test_shuffled_waiting_jobs_return_the_same_start_job_ids():
    jobs = (
        _job(job_id="J2", flexible=False),
        _job(job_id="J4", deadline_slot=8),
        _job(job_id="J10", deadline_slot=12),
    )
    shuffled = (jobs[2], jobs[0], jobs[1])
    assert _ids(_run(jobs)) == _ids(_run(shuffled))


def test_large_background_kw_does_not_block_it_fit():
    job = _job(job_id="J2", power_kw=60)
    output = _run((job,), capacity_kw=100, background_kw=10_000, pue=2.0)
    assert _ids(output) == ("J2",)
