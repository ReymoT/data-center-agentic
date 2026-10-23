"""Build the E04 development cases, rater packet and blank annotation template.

Synthetic pilot cases for developing the extraction rule (Q10 asks for at least ten
paired development cases covering ordinary, missing-evidence, abstention, unsupported-
claim and failed/malformed outputs). Every explanation here is hand-written on the
hand-example fixture; none is a model output. Each case's two outputs are shown to
raters as "X" and "Y" in a fixed seeded order.

This file contains each case's intended category and the notional system behind each
output. Raters should rate from docs/e04/RATER_PACKET.md before opening this script.

    python scripts/build_e04_cases.py          # write docs/e04/*
    python scripts/build_e04_cases.py --check  # fail if the committed files are stale
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.evaluation import review  # noqa: E402
from tests.contracts import fixtures as f  # noqa: E402

OUT = ROOT / "docs" / "e04"
ORDER_SEED = 20261022  # fixes which output is shown as X; not a Q10 sampling seed
JOBS = f.jobs()
CI = "FACT-CI-s{:02d}".format


def state(slot, waiting=(), running=(), completed=(), missed=(), forecasts=True, snap=None):
    """A visible state at ``slot`` with fresh forecasts issued at that slot (or none)."""
    snap = snap or f.snapshot()
    facts = tuple(x for x in f.forecasts(issued_slot=slot) if x.valid_slot >= slot)
    facts = facts if forecasts else ()
    present = {x.valid_slot for x in facts}
    return s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=slot,
        state_version=slot,
        waiting_jobs=tuple(JOBS[j] for j in waiting),
        running_jobs=tuple(s.RunningJobView(job=JOBS[j], start_slot=st) for j, st in running),
        completed_jobs=tuple(
            s.CompletedJobView(job_id=j, start_slot=st, end_slot=end) for j, st, end in completed
        ),
        missed_job_ids=missed,
        carbon_facts=facts,
        missing_carbon_slots=tuple(t for t in range(slot, min(slot + 24, 30)) if t not in present),
    )


def output(
    slot,
    *,
    status="ok",
    starts=(),
    defer=(),
    abstain=(),
    summary=None,
    claims=(),
    limitations=(),
    raw=None,
):
    plan = None
    if status == "ok":
        plan = s.Plan(
            episode_id=f.EPISODE_ID,
            slot=slot,
            state_version=slot,
            starts=tuple(s.PlannedStart(job_id=j, start_slot=t) for j, t in starts),
            deferrals=tuple(s.Deferral(job_id=j, reason=r) for j, r in defer),
            abstentions=tuple(
                s.Abstention(job_id=j, reason=r, constraint_ids=c) for j, r, c in abstain
            ),
            status="proposed",
        )
    explanation = None
    if summary is not None:
        explanation = s.Explanation(
            source="llm",
            summary=summary,
            claims=tuple(
                s.Claim(claim_id=cid, text=text, evidence_ids=ev, value=value, unit=unit)
                for cid, text, ev, value, unit in claims
            ),
            limitations=limitations,
        )
    return {
        "output_status": status,
        "plan": plan.to_jsonable() if plan else None,
        "explanation": explanation.model_dump(mode="json") if explanation else None,
        "raw_response": raw,
    }


J1_EARLY = (CI(0), CI(1), "FACT-JOB-J1")
J2_EARLY = (CI(2), CI(3), "FACT-JOB-J2")
J1_BEST = (CI(2), CI(3), "FACT-JOB-J1")
J2_BEST = (CI(4), CI(5), "FACT-JOB-J2")
BEST = (CI(2), CI(3), CI(4), CI(5), "FACT-JOB-J1", "FACT-JOB-J2")
NO_CAPACITY = f.snapshot(include_capacity=False)

# (case_id, category, decision state, agent output, plain output). Values come from the
# hand example: J1 40 kW x 2, J2 30 kW x 2, deadline 6, background 40 kW, capacity 100 kW,
# forecasts 500/450/300/250/400/480/520 g/kWh for slots 0-6. Run-as-soon-as-possible
# (J1@0, J2@2) is 54.5 kg; the best schedule (J1@2, J2@4) is 48.4 kg.
CASES = [
    (
        "DEV01",
        "ordinary",
        state(0, ("J1", "J2")),
        output(
            0,
            starts=[("J1", 2), ("J2", 4)],
            summary="Start J1 at slot 2 and J2 at slot 4, the lowest-carbon feasible slots in "
            "the forecast. Both finish before their deadline at slot 6. Forecast job emissions "
            "are 48.4 kg, 6.1 kg less than starting both as soon as possible (54.5 kg).",
            claims=[
                ("C1", "J1 at slots 2-3 has forecast emissions of 22.0 kg.", J1_BEST, 22.0, "kg"),
                ("C2", "J2 at slots 4-5 has forecast emissions of 26.4 kg.", J2_BEST, 26.4, "kg"),
                (
                    "C3",
                    "Peak load is 80 kW, within the 100 kW capacity limit.",
                    ("FACT-SITE-BG", "FACT-JOB-J1", "CON-CAP-01"),
                    80.0,
                    "kW",
                ),
            ],
            limitations=("Emissions use perfect-foresight forecasts, not measured values.",),
        ),
        output(
            0,
            starts=[("J1", 0), ("J2", 2)],
            summary="Start J1 now and J2 at slot 2 so both jobs finish early. Total forecast "
            "emissions are 54.5 kg.",
            claims=[
                ("C1", "J1 at slots 0-1 has forecast emissions of 38.0 kg.", J1_EARLY, 38.0, "kg"),
                ("C2", "J2 at slots 2-3 has forecast emissions of 16.5 kg.", J2_EARLY, 16.5, "kg"),
            ],
            limitations=("Forecasts may differ from actual carbon intensity.",),
        ),
    ),
    (
        "DEV02",
        "ordinary",
        state(0, ("J1", "J2")),
        output(
            0,
            defer=[("J1", "waiting_for_lower_carbon"), ("J2", "waiting_for_lower_carbon")],
            summary="Defer J1 and J2. Slot 3 has the lowest forecast intensity in the window, "
            "250 g/kWh, and both jobs can still finish by slot 6.",
            claims=[
                ("C1", "The forecast for slot 3 is 250 g/kWh.", (CI(3),), 250.0, "g/kWh"),
                (
                    "C2",
                    "J1 can start as late as slot 4 and still meet its deadline.",
                    ("FACT-JOB-J1", "CON-DL-J1"),
                    4.0,
                    "slot",
                ),
            ],
            limitations=("Forecasts beyond slot 6 are missing.",),
        ),
        output(
            0,
            starts=[("J1", 2), ("J2", 4)],
            summary="Running J1 at slot 2 and J2 at slot 4 lowers forecast emissions by about "
            "11.2% compared with running both as soon as possible.",
            claims=[
                ("C1", "Forecast job emissions for this schedule are 48.4 kg.", BEST, 48.4, "kg")
            ],
        ),
    ),
    (
        "DEV03",
        "unsupported_claim",
        state(1, ("J2",), running=[("J1", 0)]),
        output(
            1,
            starts=[("J2", 1)],
            summary="Start J2 now. The capacity check passed with a load of 110 kW, within the "
            "100 kW limit.",
            claims=[
                (
                    "C1",
                    "Load at slot 1 would be 110 kW.",
                    ("FACT-SITE-BG", "FACT-JOB-J1", "FACT-JOB-J2"),
                    110.0,
                    "kW",
                ),
                ("C2", "The capacity check passed.", ("CON-CAP-01",), None, None),
            ],
        ),
        output(
            1,
            defer=[("J2", "capacity")],
            summary="Defer J2. J1 is still running at slot 1, so starting J2 now would raise the "
            "load to 110 kW, above the 100 kW capacity. J2 can start at slot 2 after J1 finishes.",
            claims=[
                (
                    "C1",
                    "Starting J2 at slot 1 would make the load 110 kW.",
                    ("FACT-SITE-BG", "FACT-JOB-J1", "FACT-JOB-J2", "CON-CAP-01"),
                    110.0,
                    "kW",
                ),
                ("C2", "J1 finishes at slot 2.", ("FACT-JOB-J1",), 2.0, "slot"),
            ],
            limitations=("Assumes no new jobs arrive before slot 2.",),
        ),
    ),
    (
        "DEV04",
        "missing_evidence",
        state(0, ("J1", "J2"), forecasts=False),
        output(
            0,
            starts=[("J1", 0), ("J2", 2)],
            summary="Start J1 now and J2 at slot 2. This saves 6.1 kg of CO2 compared with the "
            "greedy schedule, because slot 0 has an intensity of 500 g/kWh.",
            claims=[("C1", "Slot 0 carbon intensity is 500 g/kWh.", (), 500.0, "g/kWh")],
        ),
        output(
            0,
            starts=[("J1", 0), ("J2", 2)],
            summary="Start J1 now and J2 at slot 2 so both finish well before the slot 6 "
            "deadline. No carbon forecasts are available, so no emissions estimate is given.",
            claims=[
                ("C1", "Both jobs finish by slot 4.", ("FACT-JOB-J1", "FACT-JOB-J2"), 4.0, "slot")
            ],
            limitations=("Carbon forecasts are missing for all slots 0-23.",),
        ),
    ),
    (
        "DEV05",
        "missing_evidence",
        state(0, ("J1", "J2"), snap=NO_CAPACITY),
        output(
            0,
            abstain=[(None, "missing_evidence", ())],
            summary="Abstain from starting any job: the site has no capacity constraint on "
            "record, so a safe load cannot be confirmed.",
            claims=[("C1", "No capacity constraint is available for SITE1.", (), None, None)],
            limitations=(
                "Both jobs can still start later if a capacity record becomes available.",
            ),
        ),
        output(
            0,
            starts=[("J1", 0), ("J2", 0)],
            summary="Start both jobs now. Load stays at 80 kW, below the 100 kW capacity limit.",
            claims=[
                (
                    "C1",
                    "Load at slot 0 is 80 kW.",
                    ("FACT-SITE-BG", "FACT-JOB-J1", "FACT-JOB-J2"),
                    80.0,
                    "kW",
                ),
                ("C2", "The capacity limit is 100 kW.", ("CON-CAP-01",), 100.0, "kW"),
            ],
        ),
    ),
    (
        "DEV06",
        "abstention",
        state(4, ("J3",), completed=[("J1", 0, 2), ("J2", 2, 4)]),
        output(
            4,
            abstain=[("J3", "infeasible_deadline", ("CON-DL-J3",))],
            summary="Abstain from J3: it needs 3 slots, so starting now at slot 4 ends at slot 7, "
            "after its deadline at slot 6.",
            claims=[
                ("C1", "J3 needs 3 slots.", ("FACT-JOB-J3",), 3.0, "slot"),
                ("C2", "J3's deadline is slot 6.", ("CON-DL-J3",), 6.0, "slot"),
            ],
        ),
        output(
            4,
            defer=[("J3", "waiting_for_lower_carbon")],
            summary="Defer J3 until slot 5, when carbon intensity is lower. It can still finish "
            "by its deadline.",
            claims=[
                ("C1", "The slot 5 forecast is 480 g/kWh.", (CI(5),), 480.0, "g/kWh"),
                (
                    "C2",
                    "J3 can still finish by its deadline if it starts at slot 5.",
                    ("FACT-JOB-J3",),
                    None,
                    None,
                ),
            ],
        ),
    ),
    (
        "DEV07",
        "abstention",
        state(0, ("J1", "J2")),
        output(
            0,
            starts=[("J1", 2)],
            defer=[("J2", "waiting_for_lower_carbon")],
            summary="Plan J1 for slot 2 and defer J2. Slot 2's forecast intensity of 300 g/kWh is "
            "lower than slot 0's 500 g/kWh.",
            claims=[
                ("C1", "The slot 2 forecast is 300 g/kWh.", (CI(2),), 300.0, "g/kWh"),
                ("C2", "The slot 0 forecast is 500 g/kWh.", (CI(0),), 500.0, "g/kWh"),
            ],
            limitations=(
                "Forecasts are perfect-foresight development values, not live forecasts.",
            ),
        ),
        output(
            0,
            abstain=[(None, "other", ())],
            summary="Abstain this slot. Measured carbon intensity right now is 500 g/kWh, which is "
            "too high, and neither job can run without exceeding capacity.",
            claims=[("C1", "Measured intensity at slot 0 is 500 g/kWh.", (CI(0),), 500.0, "g/kWh")],
        ),
    ),
    (
        "DEV08",
        "unsupported_claim",
        state(0, ("J1", "J2")),
        output(
            0,
            starts=[("J1", 2), ("J2", 4)],
            summary="Start J1 at slot 2 and J2 at slot 4. The reference solver confirmed this "
            "schedule is optimal.",
            claims=[("C1", "Forecast emissions for this schedule are 48.4 kg.", BEST, 48.4, "kg")],
            limitations=("Forecasts beyond slot 6 are missing.",),
        ),
        output(
            0,
            starts=[("J1", 0), ("J2", 2)],
            summary="Start J1 now and J2 at slot 2.",
            claims=[
                ("C1", "J1 emits 40.0 kg at slots 0-1.", J1_EARLY, 40.0, "kg"),
                ("C2", "The slot 0 forecast is 500 g/kWh.", (CI(3),), 500.0, "g/kWh"),
            ],
        ),
    ),
    (
        "DEV09",
        "unsupported_claim",
        state(0, ("J1", "J2")),
        output(
            0,
            starts=[("J1", 2)],
            abstain=[("J2", "other", ())],
            summary="Start J1 at slot 2 and skip J2. This cuts forecast emissions to 22.0 kg, a "
            "saving of 32.5 kg compared with running both jobs as soon as possible.",
            claims=[
                ("C1", "J1 at slots 2-3 emits 22.0 kg.", J1_BEST, 22.0, "kg"),
                (
                    "C2",
                    "This saves 32.5 kg versus running both jobs as soon as possible.",
                    BEST,
                    32.5,
                    "kg",
                ),
            ],
        ),
        output(
            0,
            starts=[("J1", 2), ("J2", 4)],
            summary="J1 runs at slots 2-3 for 22.0 kg and J2 runs at slots 4-5. J2 arrived at "
            "slot 1, so it could not start earlier.",
            claims=[
                ("C1", "J1 at slots 2-3 has forecast emissions of 22.0 kg.", J1_BEST, 22.0, "kg"),
                ("C2", "J2 at slots 4-5 has forecast emissions of 26.4 kg.", J2_BEST, 26.4, "kg"),
            ],
            limitations=("Emissions are forecasts.",),
        ),
    ),
    (
        "DEV10",
        "failed_output",
        state(0, ("J1", "J2")),
        output(
            0,
            starts=[("J1", 2), ("J2", 4)],
            summary="Start J1 at slot 2 and J2 at slot 4 to use the lower forecast intensity at "
            "slots 2-5.",
            claims=[("C1", "Forecast emissions for this schedule are 48.4 kg.", BEST, 48.4, "kg")],
            limitations=("Forecasts beyond slot 6 are missing.",),
        ),
        output(
            0,
            status="malformed",
            raw='{"output_status": "ok", "plan": {"starts": [{"job_id": "J1", "start_',
        ),
    ),
    (
        "DEV11",
        "empty_queue",
        state(5, completed=[("J1", 0, 2), ("J2", 2, 4)], missed=("J3",)),
        output(5),
        output(5),
    ),
]
REQUIRED_CATEGORIES = {
    "ordinary",
    "missing_evidence",
    "abstention",
    "unsupported_claim",
    "failed_output",
}


def build() -> dict[str, str]:
    """Every generated file's text, keyed by its path relative to docs/e04."""
    rng = random.Random(ORDER_SEED)
    cases = []
    for case_id, _, st, agent, plain in CASES:
        pair = [agent, plain]
        rng.shuffle(pair)
        snap = NO_CAPACITY if case_id == "DEV05" else f.snapshot()
        cases.append(
            {
                "case_id": case_id,
                "snapshot": snap.to_jsonable(),
                "state": st.to_jsonable(),
                "outputs": dict(zip(review.OUTPUT_KEYS, pair)),
            }
        )
    data = {
        "rubric_version": review.RUBRIC_VERSION,
        "synthetic": True,
        "note": "Hand-written pilot cases on the hand-example fixture; not model outputs.",
        "cases": cases,
    }
    loaded = review.load_cases(data)
    template = {
        "rubric_version": review.RUBRIC_VERSION,
        "rater": "",
        "outputs": [review.blank_annotation(c, k) for c in loaded for k in review.OUTPUT_KEYS],
    }
    dump = lambda d: json.dumps(d, indent=2, ensure_ascii=False) + "\n"  # noqa: E731
    return {
        "development_cases.json": dump(data),
        "annotation_template.json": dump(template),
        "RATER_PACKET.md": review.render_packet(loaded),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if committed files differ")
    args = parser.parse_args()
    stale = []
    for name, text in build().items():
        path = OUT / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    if stale:
        print("stale:", ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
