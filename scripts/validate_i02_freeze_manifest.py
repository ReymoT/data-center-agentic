"""Validate the I02 freeze manifest offline.

No network, process or model-call path. The checked-in manifest is a pre-freeze
checklist: it should be internally valid, and ``--require-ready`` should fail until
every item is frozen with its evidence and the freeze commit is recorded. The run
matrix arithmetic is checked so a silent reduction cannot pass as the planned study.
"""

import argparse
import json
import re
from pathlib import Path

CATEGORIES = (
    "code",
    "locks",
    "fixtures",
    "ontology",
    "models/features",
    "prompts/provider",
    "seeds",
    "references",
    "scoring/rubric",
)
STATUSES = ("pending", "blocked", "frozen")
OWNERS = ("Nisha", "Matty", "Reimo", "Ved", "Edison")
ITEM_FIELDS = {"id", "category", "description", "owner", "task", "status", "path", "sha256"}
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_SHA = re.compile(r"[0-9a-f]{40}")


def _matrix_blockers(matrix: dict) -> list[str]:
    blockers = []
    episodes = matrix.get("episodes", {})
    design = matrix.get("core_design", {})
    trials = matrix.get("trials_per_system", {})
    caps = matrix.get("call_cap_per_decision", {})
    slots = matrix.get("decision_slots")
    if episodes.get("core") != design.get("dates", 0) * design.get("scenarios", 0):
        blockers.append("run_matrix: core episodes must be dates x scenarios")
    if episodes.get("total") != episodes.get("core", 0) + episodes.get("missing_forecast", 0):
        blockers.append("run_matrix: total episodes must be core + missing_forecast")
    if sorted(trials) != sorted(
        ("greedy_a", "greedy_b", "decision_tree_c", "random_forest_d", "plain_llm", "agent")
    ):
        blockers.append("run_matrix: all six systems are required")
    total = episodes.get("total", 0)
    if matrix.get("total_runs") != total * sum(trials.values()):
        blockers.append("run_matrix: total_runs must be episodes x summed trials")
    for system, cap in caps.items():
        expected = total * trials.get(system, 0) * (slots or 0) * cap
        if matrix.get("maximum_model_calls", {}).get(system) != expected:
            blockers.append(f"run_matrix: maximum {system} calls must be {expected}")
    if set(caps) != {"plain_llm", "agent"}:
        blockers.append("run_matrix: call caps are needed for plain_llm and agent")
    return blockers


def validate_manifest(manifest: dict, *, require_ready: bool = False) -> list[str]:
    """Return every integrity or readiness blocker without changing the manifest."""
    blockers: list[str] = []
    if manifest.get("schema_version") != "i02-freeze-manifest-v1":
        blockers.append("unexpected manifest schema_version")
    blockers += _matrix_blockers(manifest.get("run_matrix", {}))

    freeze = manifest.get("freeze", {})
    commit = freeze.get("commit")
    if commit is not None and not (isinstance(commit, str) and GIT_SHA.fullmatch(commit)):
        blockers.append("freeze.commit must be a full 40-character git SHA")

    ids = set()
    covered = set()
    for item in manifest.get("items", []):
        name = item.get("id", "?")
        if not ITEM_FIELDS <= set(item):
            blockers.append(f"{name}: missing fields {sorted(ITEM_FIELDS - set(item))}")
            continue
        if name in ids:
            blockers.append(f"{name}: repeated item id")
        ids.add(name)
        covered.add(item["category"])
        if item["category"] not in CATEGORIES:
            blockers.append(f"{name}: unknown category {item['category']!r}")
        if item["owner"] not in OWNERS:
            blockers.append(f"{name}: owner must be a team member")
        status = item["status"]
        if status not in STATUSES:
            blockers.append(f"{name}: status must be one of {', '.join(STATUSES)}")
        sha = item["sha256"]
        if sha is not None and not (isinstance(sha, str) and SHA256.fullmatch(sha)):
            blockers.append(f"{name}: sha256 must be 64 lowercase hex characters")
        if status == "blocked" and not str(item.get("blocker") or "").strip():
            blockers.append(f"{name}: a blocked item names its blocker")
        if status == "frozen":
            # A file is pinned by its own hash, or by the freeze commit when it is in the repo.
            if sha is None and not (item["path"] and commit):
                blockers.append(f"{name}: frozen without a sha256 or an in-repo path and commit")
        elif require_ready:
            blockers.append(
                f"{name}: {status}" + (f" ({item['blocker']})" if item.get("blocker") else "")
            )
    missing = [c for c in CATEGORIES if c not in covered]
    if missing:
        blockers.append(f"no item covers {', '.join(missing)}")

    if require_ready:
        if commit is None:
            blockers.append("freeze.commit is not recorded")
        if not freeze.get("frozen_at") or not freeze.get("frozen_by"):
            blockers.append("freeze.frozen_at and freeze.frozen_by are not recorded")
    return blockers


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    blockers = validate_manifest(manifest, require_ready=args.require_ready)
    items = manifest.get("items", [])
    counts = {s: sum(i.get("status") == s for i in items) for s in STATUSES}
    print(", ".join(f"{n} {s}" for s, n in counts.items()))
    for blocker in blockers:
        print(f"BLOCKED: {blocker}")
    if not blockers:
        print(
            "READY: every item is frozen" if args.require_ready else "VALID: not a readiness claim"
        )
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
