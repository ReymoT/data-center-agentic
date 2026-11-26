"""Read-only authenticated parent/suffix accounting; never execute a research policy.

Use --receipt <JSON> --sha256 <reviewed raw receipt hash> --out <absent directory>.
The external receipt binds the suffix request and a complete suffix output inventory.
Original authorities/statuses remain separate. Coverage is not scientific acceptance.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import prepare_rule_study_rollout as w  # noqa: E402
from scripts import rule04_suffix as suffix  # noqa: E402
from scripts import rule04_summary_core as core  # noqa: E402


def inventory(folder):
    """Bounded, link-refusing raw inventory; never modify retained files."""
    result = {}
    for path in w.safe_path(folder).rglob("*"):
        w.safe_path(path)
        if path.is_file():
            if len(result) >= 100000:
                raise ValueError("excessive artifact inventory")
            result[path.relative_to(folder).as_posix()] = core._sha(path)
    return result


def authority(request, digest):
    """Corroborate the consumed canonical ledger, including verified cleanup."""
    plan = request["plan"]
    entry = (
        w.ROOT.parent
        / "RuleStudy_Run_Ledger"
        / (w.pf.sha(plan["proposed_authorization_id"].encode()) + ".json")
    )
    consumed, outcome = w.read_json(entry), w.read_json(entry.with_suffix(".result.json"))
    receipt = consumed["receipt"]
    expected = {
        "request_sha256": digest,
        "code_commit": plan["code_commit"],
        "authorization_id": plan["proposed_authorization_id"],
        "limits": request["limits"],
        "output_directory": plan["output_directory"],
        "freeze_reference": request["freeze_reference"],
        "operation": "retained_development_unexecuted_suffix_execution_and_replay",
        "actor": "MattyAnd",
        "decision": "approved",
        "protocol_freeze_authenticated": True,
    }
    if (
        receipt != expected
        or outcome.get("authenticated_request_sha256") != digest
        or outcome.get("cleanup_verified") is not True
        or outcome.get("retry_allowed") is not False
    ):
        raise ValueError("consumed suffix authority/cleanup differs")
    return outcome


def build(receipt_path, digest):
    receipt = suffix.bound_json(receipt_path, digest, "union receipt")
    if set(receipt) != {"kind", "request", "artifacts"} or receipt["kind"] != "rule04_union_v1":
        raise ValueError("exact union receipt required")
    binding = receipt["request"]
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("exact suffix request binding required")
    if not isinstance(binding["path"], str) or not Path(binding["path"]).is_absolute():
        raise ValueError("absolute suffix request path required")
    request = suffix.bound_json(binding["path"], binding["sha256"], "suffix request")
    if request["kind"] != w.SUFFIX_KIND:
        raise ValueError("only an authenticated original-parent suffix is supported")
    inputs = w.pair()
    selected = suffix.selection(request, full=True, loaded=inputs)
    parent = suffix.bound_json(
        request["parent"]["path"], request["parent"]["sha256"], "parent receipt"
    )
    original = suffix.bound_json(
        parent["request"]["path"], parent["request"]["sha256"], "parent request"
    )
    for role, (_, expected) in w.INPUTS.items():
        if request["plan"]["inputs"][role]["sha256"] != expected:
            raise ValueError("suffix input differs")
    baseline = w.read_json(w.ROOT / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json")
    if any(
        request["plan"]["code_sha256"].get(k) != v
        for k, v in baseline["baseline_code_sha256"].items()
    ):
        raise ValueError("suffix scientific binding differs")
    outcome = authority(request, binding["sha256"])
    if not Path(request["plan"]["output_directory"]).is_absolute():
        raise ValueError("absolute suffix output required")
    folder = w.safe_path(request["plan"]["output_directory"])
    if inventory(folder) != receipt["artifacts"]:
        raise ValueError("suffix inventory differs")
    old = core.load_run(Path(parent["output"]))
    new = core.load_run(folder)
    expected = [(c, p) for c in inputs[2] for p in w.POLICIES]
    groups = []
    for data, req, sha, location, order in (
        (old, original, parent["request"]["sha256"], Path(parent["output"]), expected),
        (new, request, binding["sha256"], folder, selected),
    ):
        metrics = {(m["case_id"], m["policy_id"]): m for m in data["metrics"]}
        ordered = [key for key in order if key in metrics]
        if ordered != order[: len(ordered)] or data["recovered_unacknowledged_pairs"]:
            raise ValueError("only acknowledged ordered completed prefixes may be combined")
        remaining = order[len(ordered) :]
        for failed in data["failed"]:
            key = failed.get("case_id"), failed.get("policy_id")
            if not remaining or key != remaining[0]:
                raise ValueError("failed/in-flight pair must be the next selected pair")
        if len(data["failed"]) > 1:
            raise ValueError("serial attempt cannot have multiple active failed pairs")
        if data["authenticated_request_sha256"] != sha and metrics:
            raise ValueError("attempt authority differs")
        counters = {"states": 0, "transitions": 0}
        signatures = {}
        for key in ordered:
            value = w.read_json(location / f"{key[0]}-{key[1]}" / "pair-result.json")
            metric = metrics[key]
            if (
                metric["code_commit"] != req["plan"]["code_commit"]
                or metric["bindings"]["code_commit"] != req["plan"]["code_commit"]
                or value["authenticated_request_sha256"] != sha
            ):
                raise ValueError("pair source/authority differs")
            for name in counters:
                count = value["budget"][name + "_used"]
                if type(count) is not int or count < 0:
                    raise ValueError("invalid completed counter")
                counters[name] += count
            if inputs[2][key[0]].scores is None:
                signatures[key] = value["execution_signature"]
        status_file = next(
            location / name
            for name in (
                "rollout-supervisor-failure.json",
                "rollout-failure.json",
                "rollout-report.json",
            )
            if (location / name).exists()
        )
        status = w.read_json(status_file)
        recorded = status.get("charged_steps_completed_pairs_only", status.get("charged_steps"))
        if recorded != counters or any(counters[n] > req["limits"][n] for n in counters):
            raise ValueError("attempt charged counters differ or exceed limits")
        groups.append(
            {
                "request_sha256": sha,
                "authorization_id": req["plan"]["proposed_authorization_id"],
                "code_commit": req["plan"]["code_commit"],
                "status": status,
                "status_sha256": core._sha(status_file),
                "completed_pairs": len(ordered),
                "completed_pair_counters": counters,
                "additional_partial_work": "not established by completed-pair counters",
                "keys": ordered,
                "control_signatures": signatures,
            }
        )
    a, b = groups
    if set(a["keys"]) & set(b["keys"]) or a["authorization_id"] == b["authorization_id"]:
        raise ValueError("overlapping pairs or reused authority")
    if new["run_status"] == "PASS" and (
        outcome.get("status") != "succeeded" or b["keys"] != selected
    ):
        raise ValueError("suffix PASS not corroborated by host outcome and selected pairs")
    signatures = {}
    for group in groups:
        for (case, _), signature in group.pop("control_signatures").items():
            if case in signatures and signatures[case] != signature:
                raise ValueError("cross-attempt missing-forecast control differs")
            signatures[case] = signature
        group.pop("keys")
    metrics = old["metrics"] + new["metrics"]
    if old["strata"] != new["strata"]:
        raise ValueError("attempt strata differ")
    complete = len(metrics) == len(expected) and not new["failed"] and new["run_status"] == "PASS"
    result = core.summarize(
        {
            "metrics": metrics,
            "strata": old["strata"],
            "failed": old["failed"] + new["failed"],
            "complete": complete,
            "run_status": "COMBINED_COVERAGE_ONLY",
            "stop_message": "Original incomplete attempt retained; coverage is not study acceptance.",
            "recovered_unacknowledged_pairs": 0,
            "authenticated_request_sha256": None,
            "inputs": [("union_receipt", digest)],
        }
    )
    result.update(
        record_kind="rule04_union_summary_v1",
        attempts=groups,
        scientific_acceptance="PENDING independent receiving/reproduction and final audit",
        cumulative_completed_pair_counters={
            k: sum(g["completed_pair_counters"][k] for g in groups)
            for k in ("states", "transitions")
        },
        cumulative_total_work="not established; partial work and eligibility costs excluded",
        comparison_source_rule="Original producer bindings retained. Cross-source split-case "
        "comparisons remain unavailable under the existing equal-work checker; no normalization.",
    )
    # Recheck retained bytes after arithmetic. No new authority is created or consumed.
    if (
        inventory(folder) != receipt["artifacts"]
        or suffix.selection(request, full=True, loaded=inputs) != selected
        or suffix.bound_json(receipt_path, digest, "union receipt") != receipt
        or suffix.bound_json(binding["path"], binding["sha256"], "suffix request") != request
        or authority(request, binding["sha256"]) != outcome
        or w.pair()[0:2] != inputs[0:2]
        or w.read_json(w.ROOT / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json")
        != baseline
    ):
        raise ValueError("retained evidence changed during union validation")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ValueError("output must be absent")
        result = build(args.receipt, args.sha256)
        receipt = suffix.bound_json(args.receipt, args.sha256, "union receipt")
        request = suffix.bound_json(
            receipt["request"]["path"], receipt["request"]["sha256"], "suffix request"
        )
        parent = suffix.bound_json(
            request["parent"]["path"], request["parent"]["sha256"], "parent receipt"
        )
        out = w.safe_path(args.out)
        for source in (Path(parent["output"]), Path(request["plan"]["output_directory"])):
            if out.is_relative_to(source) or source.is_relative_to(out):
                raise ValueError("output must be separate from retained attempts")
        for path in core.write_outputs(result, out):
            print(f"wrote {path}")
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
