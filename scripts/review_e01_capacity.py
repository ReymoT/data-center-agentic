"""Reproduce A03/E01 comparisons on an explicitly selected E01 draft worktree.

Synthetic hand cases only, not policy/model outputs or scientific acceptance. E01
is imported from the selected checkout, never installed/copied into main. Expected
outcomes below are independent hand arithmetic; neither implementation is truth.
"""

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path


def review(root: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    if git("status", "--porcelain"):
        raise ValueError("Review checkout must be clean")
    head = git("rev-parse", "HEAD")
    if head != "f5a2542c1816ed0f34d8f784053453ae9b26c1f6":
        raise ValueError("This dated review requires the exact PR #23 head")
    for path in ("dc_sustainability/schemas.py", "dc_sustainability/verification/checker.py"):
        if git("diff", "91eead1", head, "--", path):
            raise ValueError(f"Production input differs from the reviewed main base: {path}")
    sys.path.insert(0, str(root.resolve()))
    s = importlib.import_module("dc_sustainability.schemas")
    v = importlib.import_module("dc_sustainability.evaluation.validator")
    check_schedule = importlib.import_module(
        "dc_sustainability.verification.checker"
    ).check_schedule
    f = importlib.import_module("tests.contracts.fixtures")
    rows = []

    def case(name, *, starts, expected_capacity, expected_e01, expected_slots=(), **kwargs):
        snap = f.snapshot(
            capacity_kw=kwargs.pop("capacity", 100.0),
            include_capacity=kwargs.pop("include_capacity", True),
            pue=kwargs.pop("pue", 1.0),
        )
        slot = kwargs.pop("slot", 0)
        view = s.VisibleState.from_snapshot(
            snap,
            episode_id=f.EPISODE_ID,
            current_slot=slot,
            state_version=slot,
            waiting_jobs=kwargs.pop("waiting", (f.jobs()["J1"], f.jobs()["J2"])),
            **kwargs,
        )
        plan = s.Plan(
            episode_id=view.episode_id,
            slot=slot,
            state_version=slot,
            starts=tuple(s.PlannedStart(job_id=j, start_slot=t) for j, t in starts),
            status="proposed",
        )
        production = check_schedule(plan, view, snap)
        independent = v.validate_plan(plan, v.facts_from_state(view, snap), v.Q03_DRAFT)
        capacity = next(c.outcome for c in production.performed if c.name == "capacity")
        overload_slots = sorted(
            violation.slot
            for violation in production.violations
            if violation.violation_type == "capacity"
        )
        if (capacity, independent.status, overload_slots) != (
            expected_capacity,
            expected_e01,
            list(expected_slots),
        ):
            raise AssertionError((name, capacity, independent.status, overload_slots))
        rows.append(
            {
                "case": name,
                "a03_capacity": capacity,
                "a03_overall": production.status,
                "a03_overload_slots": overload_slots,
                "e01_status": independent.status,
                "e01_codes": [x.code for x in independent.findings],
                "overall_comparison": v.compare_with_check(independent, production),
            }
        )

    case(
        "sequential_80_then_70_kw",
        starts=(("J1", 0), ("J2", 2)),
        expected_capacity="pass",
        expected_e01="valid",
    )
    case(
        "future_only_110_kw",
        starts=(("J1", 2), ("J2", 2)),
        expected_capacity="fail",
        expected_e01="invalid",
        expected_slots=(2, 3),
    )
    case(
        "running_plus_future_110_kw",
        slot=1,
        waiting=(f.jobs()["J2"],),
        running_jobs=(s.RunningJobView(job=f.jobs()["J1"], start_slot=0),),
        starts=(("J2", 1),),
        expected_capacity="fail",
        expected_e01="invalid",
        expected_slots=(1,),
    )
    j2 = f.jobs()["J2"].model_copy(update={"power_kw": 20.0})
    case(
        "exact_100_kw_before_pue",
        waiting=(f.jobs()["J1"], j2),
        pue=1.2,
        starts=(("J1", 2), ("J2", 2)),
        expected_capacity="pass",
        expected_e01="valid",
    )
    case(
        "changed_capacity_70_kw",
        waiting=(f.jobs()["J1"],),
        capacity=70.0,
        starts=(("J1", 2),),
        expected_capacity="fail",
        expected_e01="invalid",
        expected_slots=(2, 3),
    )
    late = s.Job(
        job_id="LATE",
        arrival_slot=23,
        duration_slots=7,
        power_kw=20.0,
        deadline_slot=30,
        flexible=True,
    )
    case(
        "slot23_finishes_at30",
        slot=23,
        waiting=(late,),
        starts=(("LATE", 23),),
        capacity=60.0,
        expected_capacity="pass",
        expected_e01="valid",
    )
    case(
        "missing_capacity",
        include_capacity=False,
        starts=(("J1", 0), ("J2", 2)),
        expected_capacity="error",
        expected_e01="invalid",
    )
    case(
        "omission_is_not_full_checker_agreement",
        starts=(("J1", 0),),
        expected_capacity="pass",
        expected_e01="invalid",
    )
    tiny_over = s.Job(
        job_id="EPS",
        arrival_slot=0,
        duration_slots=1,
        power_kw=60.0000000001,
        deadline_slot=6,
        flexible=True,
    )
    case(
        "capacity_slack_disagreement",
        waiting=(tiny_over,),
        starts=(("EPS", 2),),
        expected_capacity="fail",
        expected_e01="valid",
        expected_slots=(2,),
    )
    return {
        "review_date": "2026-10-20",
        "evidence_kind": "synthetic_hand_case_compatibility_not_acceptance",
        "production_base": git("rev-parse", "91eead1"),
        "draft_head": head,
        "protocol": v.Q03_DRAFT.name,
        "review_script_sha256_lf": hashlib.sha256(
            Path(__file__).read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest(),
        "cases": rows,
        "model_calls": 0,
        "full_e01_accepted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = review(args.draft_root)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Verified {len(result['cases'])} hand cases; one documented slack disagreement")


if __name__ == "__main__":
    main()
