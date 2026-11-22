"""RULE-03: independent receiving of the current RULE-02 implementation (#241).

The RULE-02 system (rules-v1 + unchanged production checker + Greedy A fallback + the
real simulator) is deterministic for a closed case: every arrival is known, so its
policy-induced graph is a single path. Verifying it on a case domain therefore means
running the actual common runner once per case and independently replaying the records.
This module does that mapping and adds what the trace reader cannot do alone:

- **Pin**: independently reconstruct every binding of the current code from the repository
  (specification, ``rule_study/*.py`` adapter map, generator, environment lock, git HEAD and
  clean-tree status). It does not call the runner's ``make_bindings``.
- **Domain mapping**: convert verifier cases (primary 64, extended 1,024, authored A/B) into
  the runner's ``CaseSpec`` shape, so the same inputs drive both sides.
- **Binding and artifact check**: every decision/result record carries exactly the pinned
  bindings; ``case.json`` hashes to its binding; every referenced raw state, snapshot and
  transition file exists and hashes to its reference; every decision has its completion
  commitment.
- **Replay**: the merged trace reader replays the records against the verifier's own
  reconstruction (S1-S5, P1, P2, R04 arithmetic).

``plan_receiving`` only describes a run. ``run_receiving`` executes the runner and is meant
for an approved bounded run (or unit tests with a test-only commit). It never writes into an
existing directory. Scores are artificial weights; nothing here concerns emissions.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from dc_sustainability.evaluation import rule_study_trace as tr
from dc_sustainability.evaluation import rule_study_verifier as v

RECORD_KIND = "rule_study_receiving_v1"
POLICIES = ("rules-v1", "greedy_a", "greedy_b")
DOMAINS = ("primary", "extended", "authored")
BINDING_FIELDS = (
    "spec_sha256",
    "adapter_source_sha256",
    "generator_source_sha256",
    "case_sha256",
    "environment_lock_sha256",
    "code_commit",
)
SPEC_REL = Path("docs/rule_study/specification.json")
ADAPTER_DIR = Path("dc_sustainability/rule_study")
GENERATOR_REL = Path("dc_sustainability/evaluation/rule_study_generator.py")
LOCK_REL = Path("requirements/requirements-windows-py312.lock.txt")
FINDINGS_PER_TRACE = 20


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True, check=True
    ).stdout.strip()


def reconstruct_pin(repo_root: Path, *, code_commit: str | None = None) -> dict:
    """Independently rebuild the code-level bindings (everything except the per-case hash).

    ``code_commit`` overrides git for unit tests only; the result then says so.
    """
    root = Path(repo_root)
    spec = json.loads((root / SPEC_REL).read_text(encoding="utf-8"))
    sources = sorted((root / ADAPTER_DIR).glob("*.py"))
    if not sources:
        raise ValueError("no rule_study adapter sources found")
    adapter_map = {p.name: _lf_sha256(p) for p in sources}
    pin = {
        "spec_sha256": v.canonical_sha256(spec),
        "adapter_source_sha256": v.canonical_sha256(adapter_map),
        "adapter_files": adapter_map,
        "generator_source_sha256": _lf_sha256(root / GENERATOR_REL),
        "environment_lock_sha256": _lf_sha256(root / LOCK_REL),
    }
    if code_commit is not None:
        pin.update(code_commit=code_commit, clean_tree=None, commit_source="test_only_override")
    else:
        pin.update(
            code_commit=_git(root, "rev-parse", "HEAD"),
            clean_tree=_git(root, "status", "--porcelain") == "",
            commit_source="git",
        )
    return pin


def case_spec_for(case: v.Case):
    """The runner's CaseSpec for a verifier case (PUE 1, perfect forecast when scores exist)."""
    from dc_sustainability import schemas as s
    from dc_sustainability.rule_study import cases as rc

    body = re.sub(r"[^A-Za-z0-9]", "", case.case_id)[:28]
    if not body:
        raise ValueError(f"case_id {case.case_id!r} has no usable characters")
    forecast = case.scores is not None
    return rc.CaseSpec(
        case_id=case.case_id,
        episode_id=f"EP-RCV{body}",
        capacity_kw=case.capacity_kw,
        background_kw=case.background_kw,
        pue=1.0,
        jobs=tuple(
            s.Job(
                job_id=j.job_id,
                arrival_slot=j.arrival_slot,
                duration_slots=j.duration_slots,
                power_kw=j.power_kw,
                deadline_slot=j.deadline_slot,
                flexible=j.flexible,
            )
            for j in case.jobs
        ),
        first_scores=tuple(case.scores) if forecast else (v.DEFAULT_SCORE,) * v.HORIZON,
        remaining_score=v.DEFAULT_SCORE,
        forecast_present=forecast,
        fault_starts=tuple(case.fault_starts),
    )


def domain_cases(name: str, spec: Mapping) -> list[v.Case]:
    if name == "primary":
        return v.primary_domain()
    if name == "extended":
        return v.extended_domain()
    if name == "authored":
        return v.authored_cases(spec)
    raise ValueError(f"unknown domain {name!r}; use one of {DOMAINS}")


def _runs(cases: Sequence[v.Case], policies: Sequence[str]) -> list[tuple[v.Case, str]]:
    # Fault injection is a rules-v1 demonstration only; baselines skip faulted cases.
    return [
        (case, policy)
        for policy in policies
        for case in cases
        if policy == "rules-v1" or not case.fault_injected
    ]


def plan_receiving(
    domains: Sequence[str], policies: Sequence[str], repo_root: Path, spec: Mapping
) -> dict:
    """Describe an exact bounded receiving run without running anything."""
    _check_policies(policies)
    pin = reconstruct_pin(repo_root)
    rows = {}
    for name in domains:
        cases = domain_cases(name, spec)
        rows[name] = {
            "cases": len(cases),
            "runs": len(_runs(cases, policies)),
            "case_sha256s_sha256": v.canonical_sha256(
                [v.canonical_sha256(case_spec_for(c).case_json()) for c in cases]
            ),
        }
    return {
        "record_kind": RECORD_KIND + "_plan",
        "status": "NOT_RUN",
        "pin": pin,
        "policies": list(policies),
        "domains": rows,
        "decisions_per_run_max": v.HORIZON,
        "replay_budget": v.Budget().summary(),
        "note": "plan only; executing it needs an approved bounded run on a clean pinned tree",
    }


def _check_policies(policies: Sequence[str]) -> None:
    if not policies or set(policies) - set(POLICIES) or len(set(policies)) != len(policies):
        raise ValueError(f"policies must be distinct values from {POLICIES}")


# --------------------------------------------------------------------------- artifact check


def _read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _hash_ref(folder: Path, sub: str, digest, where: str, out: list) -> None:
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        out.append(f"{where}: missing or malformed {sub} hash")
        return
    path = folder / sub / f"{digest}.json"
    if not path.is_file():
        out.append(f"{where}: {sub}/{digest[:12]}... missing")
    elif _text_sha256(_read_text(path)) != digest:
        out.append(f"{where}: {sub}/{digest[:12]}... content does not match its name")


def check_trace_artifacts(folder: Path, pin: Mapping) -> list[str]:
    """Binding and raw-artifact findings for one runner output folder; empty means clean."""
    folder = Path(folder)
    out: list[str] = []
    case_path = folder / "case.json"
    if not case_path.is_file() or not (folder / "result.json").is_file():
        return ["case.json or result.json missing"]
    case_sha = _text_sha256(_read_text(case_path))
    expected = {k: pin[k] for k in BINDING_FIELDS if k != "case_sha256"}
    expected["case_sha256"] = case_sha
    if case_sha != v.canonical_sha256(json.loads(_read_text(case_path))):
        out.append("case.json is not in canonical form")

    def compare(bindings, where):
        if not isinstance(bindings, Mapping) or set(bindings) != set(BINDING_FIELDS):
            out.append(f"{where}: bindings fields differ")
            return
        for key in BINDING_FIELDS:
            if bindings[key] != expected[key]:
                out.append(f"{where}: {key} differs from the independent pin")

    result = json.loads(_read_text(folder / "result.json"))
    compare(result.get("bindings"), "result")
    decision_paths = sorted((folder / "decisions").glob("*.json"))
    if not decision_paths:
        out.append("no decision records")
    for path in decision_paths:
        text = _read_text(path)
        rec = json.loads(text)
        where = path.stem
        compare(rec.get("bindings"), where)
        commitment = folder / ".completed" / path.name
        if not commitment.is_file() or _read_text(commitment) != _text_sha256(text) + "\n":
            out.append(f"{where}: completion commitment missing or different")
        before = rec.get("state_before") or {}
        _hash_ref(folder, "states", before.get("visible_state_sha256"), where, out)
        _hash_ref(folder, "snapshots", before.get("constraint_snapshot_sha256"), where, out)
        execution = rec.get("execution") or {}
        after = execution.get("state_after")
        if after is not None:
            _hash_ref(folder, "states", after.get("state_sha256"), f"{where}/after", out)
        ref = execution.get("transition_ref")
        if ref is not None:
            if ref != f"transitions/transition-{rec.get('decision_index', -1):02d}.json":
                out.append(f"{where}: unexpected transition_ref")
            elif not (folder / ref).is_file():
                out.append(f"{where}: transition file missing")
            elif _text_sha256(_read_text(folder / ref)) != execution.get("transition_sha256"):
                out.append(f"{where}: transition content differs from its hash")
        if len(out) >= FINDINGS_PER_TRACE:
            out.append("further findings for this trace not listed")
            break
    return out


# --------------------------------------------------------------------------- execution


def run_receiving(
    domains: Sequence[str],
    policies: Sequence[str],
    out_dir: Path,
    repo_root: Path,
    spec: Mapping,
    *,
    code_commit: str | None = None,
    cases_by_domain: Mapping[str, Iterable[v.Case]] | None = None,
) -> dict:
    """Run the actual RULE-02 runner on each case, then check artifacts and replay records.

    ``code_commit`` and ``cases_by_domain`` exist for unit tests; a real receiving run uses
    the clean git HEAD and the named domains in full.
    """
    from dc_sustainability.rule_study import runner as rr
    from dc_sustainability.rule_study.scheduler import ScoreKwhConvention

    _check_policies(policies)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    pin = reconstruct_pin(repo_root, code_commit=code_commit)
    convention = ScoreKwhConvention()
    sections = {}
    for name in domains:
        cases = list(
            cases_by_domain[name] if cases_by_domain is not None else domain_cases(name, spec)
        )
        domain_dir = out_dir / name
        run_errors, folders = [], []
        for case, policy in _runs(cases, policies):
            try:
                case_spec = case_spec_for(case)
                bindings = rr.make_bindings(case_spec, repo_root, code_commit=code_commit)
                run, _, runner = rr.run_case(
                    domain_dir,
                    case_spec,
                    policy,
                    bindings=bindings,
                    score_convention=convention,
                    fault_injection=case_spec.fault_injection if case_spec.fault_starts else None,
                )
                folders.append((case.case_id, policy, runner.root))
            except Exception as exc:  # recorded, never retried or hidden
                run_errors.append(
                    {
                        "case_id": case.case_id,
                        "policy": policy,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        sections[name] = _receive_folders(name, len(cases), folders, run_errors, pin, spec)
    return _report(pin, policies, sections)


def receive_existing(folders: Sequence[Path], repo_root: Path, spec: Mapping, **pin_kw) -> dict:
    """Check and replay already written runner folders against an independent pin."""
    pin = reconstruct_pin(repo_root, **pin_kw)
    items = []
    for folder in folders:
        case = json.loads(_read_text(Path(folder) / "case.json"))
        result = json.loads(_read_text(Path(folder) / "result.json"))
        items.append((case.get("case_id"), result.get("policy_id"), Path(folder)))
    policies = sorted({p for _, p, _ in items if isinstance(p, str)})
    section = _receive_folders("supplied", len(items), items, [], pin, spec)
    return _report(pin, policies, {"supplied": section})


def _receive_folders(name, n_cases, folders, run_errors, pin, spec) -> dict:
    artifact_findings = {}
    triples = []
    for case_id, policy, folder in folders:
        findings = check_trace_artifacts(folder, pin)
        if findings:
            artifact_findings[f"{case_id}/{policy}"] = findings
        triples.append(tr.load_trace_dir(folder))
    replay = tr.verify_traces(
        triples, expected_spec_sha256=v.canonical_sha256(spec), is_rules_v1_run=True
    )
    property_statuses = {
        policy: {p: x["status"] for p, x in res["properties"].items()}
        for policy, res in replay["results"].items()
    }
    arithmetic = {
        policy: res["arithmetic_consistency"]["status"] for policy, res in replay["results"].items()
    }
    if pin.get("commit_source") != "git":
        binding_status = "INCOMPLETE"
    elif artifact_findings:
        binding_status = "FAIL"
    elif not pin.get("clean_tree"):
        binding_status = "INCOMPLETE"
    else:
        binding_status = "PASS" if folders else "NOT_RUN"
    statuses = [s for row in property_statuses.values() for s in row.values()]
    statuses += list(arithmetic.values())
    if run_errors or replay["refused_traces"] or "FAIL" in statuses or artifact_findings:
        overall = "FAIL"
    elif (
        folders
        and binding_status == "PASS"
        and all(s in ("PASS", "NOT_RUN") for s in statuses)
        and "PASS" in statuses
    ):
        overall = "PASS"
    else:
        overall = "INCOMPLETE"
    return {
        "domain": name,
        "cases": n_cases,
        "runs_completed": len(folders),
        "run_errors": run_errors,
        "binding_check": {
            "status": binding_status,
            "traces_checked": len(folders),
            "findings": artifact_findings,
            "note": "independent pin vs every decision/result binding, case.json and raw "
            "state/snapshot/transition/commitment files; local hashes, not signatures",
        },
        "property_statuses": property_statuses,
        "arithmetic": arithmetic,
        "replay": replay,
        "overall": overall,
    }


def _report(pin, policies, sections) -> dict:
    statuses = [s["overall"] for s in sections.values()]
    return {
        "record_kind": RECORD_KIND,
        "receiver_source_sha256": _own_sha256(),
        "verifier_source_sha256": v.source_sha256(),
        "pin": pin,
        "policies": list(policies),
        "domains": sections,
        "overall": "FAIL"
        if "FAIL" in statuses
        else ("PASS" if statuses and all(s == "PASS" for s in statuses) else "INCOMPLETE"),
        "scope": "the pinned implementation on the listed closed synthetic domains only; "
        "not generalization, final-set evaluation, metric acceptance or a scientific freeze",
    }


def _own_sha256() -> str:
    return _lf_sha256(Path(__file__))
