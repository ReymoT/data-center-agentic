"""Authenticate a retained successful prefix; select only its unexecuted suffix.

No runner, replay, generator or model is called here. The parent inventory must be
prepared from reviewed retained bytes; its hash is part of the fresh request.
"""

from pathlib import Path


def bound_json(path, digest, label):
    """Hash and parse one read, avoiding a second, unverified read."""
    from scripts import prepare_rule_study_rollout as w

    raw = w.pf.bounded_bytes(w.safe_path(path))
    if w.pf.sha(raw) != digest:
        raise ValueError(f"{label} changed")
    return w.decode_json(raw)


def selection(request, *, full=False, loaded=None):
    from scripts import prepare_rule_study_rollout as w

    _, _, parsed = loaded if loaded is not None else w.pair()
    expected = [(c, p) for c in parsed for p in w.POLICIES]
    if request["kind"] == w.KIND:
        if set(request) != w.FIELDS:
            raise ValueError("unexpected full-batch fields")
        return expected
    if request["kind"] != w.SUFFIX_KIND or set(request) != w.FIELDS | {"parent"}:
        raise ValueError("fixed full-batch or suffix request required")
    parent = request["parent"]
    if not isinstance(parent, dict) or set(parent) != {"path", "sha256"}:
        raise ValueError("exact parent receipt binding required")
    if not isinstance(parent["path"], str) or not Path(parent["path"]).is_absolute():
        raise ValueError("absolute parent receipt path required")
    path = w.safe_path(parent["path"])
    receipt = bound_json(path, parent["sha256"], "parent receipt")
    if set(receipt) != {"kind", "output", "request", "status_sha256", "pairs", "artifacts"}:
        raise ValueError("exact parent receipt fields required")
    if receipt["kind"] != "rule04_retained_prefix_v1":
        raise ValueError("unsupported parent receipt")
    prior = receipt["request"]
    if not isinstance(prior, dict) or set(prior) != {"path", "sha256"}:
        raise ValueError("parent request binding required")
    old_path = w.safe_path(prior["path"])
    old = bound_json(old_path, prior["sha256"], "parent request")
    if old["kind"] != w.KIND or set(old) != w.FIELDS:
        raise ValueError("only an original full development attempt may be continued")
    for role, (name, digest) in w.INPUTS.items():
        if old["plan"]["inputs"][role]["sha256"] != digest:
            raise ValueError("parent input differs")
    # All scientific component pins must be preserved; controller changes are allowed.
    baseline = w.read_json(w.ROOT / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json")
    if any(
        old["plan"]["code_sha256"].get(k) != v for k, v in baseline["baseline_code_sha256"].items()
    ):
        raise ValueError("parent scientific baseline differs")
    folder = w.safe_path(receipt["output"])
    if folder != w.safe_path(old["plan"]["output_directory"]):
        raise ValueError("parent output differs")
    new_out = request["plan"]["output_directory"]
    if isinstance(new_out, str):
        new = w.safe_path(new_out)
        if new.is_relative_to(folder) or folder.is_relative_to(new):
            raise ValueError("continuation output must be separate from parent")
    if request["plan"]["proposed_authorization_id"] == old["plan"]["proposed_authorization_id"]:
        raise ValueError("parent authorization cannot be reused")
    ledger = w.ROOT.parent / "RuleStudy_Run_Ledger"
    entry = ledger / (w.pf.sha(old["plan"]["proposed_authorization_id"].encode()) + ".json")
    authority, outcome = w.read_json(entry), w.read_json(entry.with_suffix(".result.json"))
    if (
        authority["receipt"]["request_sha256"] != prior["sha256"]
        or authority["receipt"]["code_commit"] != old["plan"]["code_commit"]
        or authority["receipt"]["authorization_id"] != old["plan"]["proposed_authorization_id"]
        or authority["receipt"]["actor"] != "MattyAnd"
        or authority["receipt"]["decision"] != "approved"
        or authority["receipt"]["limits"] != old["limits"]
        or authority["receipt"]["output_directory"] != old["plan"]["output_directory"]
        or outcome.get("authenticated_request_sha256") != prior["sha256"]
        or outcome.get("cleanup_verified") is not True
        or outcome.get("retry_allowed") is not False
    ):
        raise ValueError("parent consumed authority/cleanup not established")
    status_path = folder / "rollout-failure.json"
    status = bound_json(status_path, receipt["status_sha256"], "parent status")
    if (folder / "rollout-supervisor-failure.json").exists() or (
        folder / "rollout-report.json"
    ).exists():
        raise ValueError("ambiguous parent status")
    rows = receipt["pairs"]
    if (
        status.get("status") != "FAIL_OR_INCOMPLETE"
        or not resource_stop(status)
        or status.get("authenticated_request_sha256") != prior["sha256"]
        or type(status.get("completed_runs")) is not int
        or not 0 < status["completed_runs"] < len(expected)
        or not isinstance(rows, list)
        or len(rows) != status["completed_runs"]
    ):
        raise ValueError("only a stopped complete prefix is supported; never retry a failed pair")
    used = {"states": 0, "transitions": 0}
    signatures = {}
    for index, row in enumerate(rows):
        if set(row) != {"case_id", "policy_id", "sha256"}:
            raise ValueError("invalid parent pair binding")
        key = row["case_id"], row["policy_id"]
        if key != expected[index]:
            raise ValueError("parent must be the original ordered prefix")
        pair = folder / f"{key[0]}-{key[1]}"
        record = pair / "pair-result.json"
        value = bound_json(record, row["sha256"], "parent pair")
        if (
            value.get("status") != "PASS"
            or value.get("replay", {}).get("overall") != "PASS"
            or (value.get("case_id"), value.get("policy_id")) != key
            or value.get("authenticated_request_sha256") != prior["sha256"]
            or value["metric"]["code_commit"] != old["plan"]["code_commit"]
            or value["metric"]["execution_violations"] != 0
            or (pair / "pair-failure.json").exists()
        ):
            raise ValueError("parent pair not an accepted saved PASS")
        if getattr(parsed[key[0]], "scores", True) is None:
            signature = value.get("execution_signature")
            if not isinstance(signature, str) or len(signature) != 64:
                raise ValueError("missing parent control signature")
            if key[0] in signatures and signatures[key[0]] != signature:
                raise ValueError("parent control differs across policies")
            signatures[key[0]] = signature
        for k in used:
            n = value["budget"][k + "_used"]
            if type(n) is not int or n < 0:
                raise ValueError("invalid parent resource counter")
            used[k] += n
    if used != status["charged_steps_completed_pairs_only"]:
        raise ValueError("parent counters differ")
    # Reject an unacknowledged or failed/in-flight pair: continuation never retries it.
    dirs = [p for p in folder.iterdir() if p.is_dir()]
    if {p.name for p in dirs} != {f"{c}-{p}" for c, p in expected[: len(rows)]}:
        raise ValueError("parent has extra or missing pair directories")
    artifacts = receipt["artifacts"]
    if not isinstance(artifacts, dict) or len(artifacts) > 100000:
        raise ValueError("bounded parent artifact inventory required")
    if full:
        actual = {}
        for p in folder.rglob("*"):
            w.safe_path(p)
            if p.is_file():
                if len(actual) >= 100000:
                    raise ValueError("excessive parent inventory")
                actual[p.relative_to(folder).as_posix()] = w.pf.sha(w.pf.bounded_bytes(p))
        if actual != artifacts:
            raise ValueError("parent artifact bytes/inventory changed")
    return expected[len(rows) :]


def controls(request, loaded):
    """Carry control signatures across an attempt boundary, without exposing weights."""
    from scripts import prepare_rule_study_rollout as w

    if request["kind"] == w.KIND:
        return {}
    receipt = bound_json(request["parent"]["path"], request["parent"]["sha256"], "parent receipt")
    out = w.safe_path(receipt["output"])
    return {
        r["case_id"]: bound_json(
            out / f"{r['case_id']}-{r['policy_id']}" / "pair-result.json",
            r["sha256"],
            "parent control pair",
        )["execution_signature"]
        for r in receipt["pairs"]
        if loaded[2][r["case_id"]].scores is None
    }


def resource_stop(status):
    """Keep historical bytes valid; new failures distinguish time from counters."""
    reason = status.get("stop_reason")
    if reason is None:
        return status.get("message") == "combined resource budget exhausted"
    messages = {
        "wall_time_reserve": "wall-time reserve budget exhausted before next pair and cleanup",
        "state_transition_budget": "combined state/transition budget exhausted",
    }
    return reason in messages and status.get("message") == messages[reason]
