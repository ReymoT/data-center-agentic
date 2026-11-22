"""Build or check the RULE-02 evidence manifest (reviewer tool).

Build (writes a new MANIFEST.json, refuses to overwrite):
    python docs/evidence/rule02/tools/build_manifest.py build

Check (re-hashes every listed file and reports missing, changed or unlisted files; exit 0 only if exact):
    python docs/evidence/rule02/tools/build_manifest.py check

Standard library only. The manifest lists every file under docs/evidence/rule02 except MANIFEST.json itself,
so it cannot contain its own hash. The commit that adds this directory is recorded by Git, not in the manifest.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

EVIDENCE_DIR = Path(__file__).resolve().parents[1]
MANIFEST = EVIDENCE_DIR / "MANIFEST.json"

IMPLEMENTATION_COMMIT = "176361ad23ba57940b1576828893ce3a7b1a1666"
DOCUMENTATION_COMMIT = "ee1de66aec897d481308e3ce35a583c026c1b3ee"
BASE_COMMIT = "75d6ada1785816c2e9b0ab1c08b18da23c9facd8"
SUPERSEDED_BINDING = "c42376e94e7558cdd980c45a57150ab24c0b09ab"

GENERATION_COMMANDS = [
    "git clone <repo> rule02-clean && cd rule02-clean && git checkout --detach "
    + IMPLEMENTATION_COMMIT,
    'test -z "$(git status --porcelain)"   # the runner refuses to bind code_commit from a dirty tree',
    "PYTHONPATH=. python -m dc_sustainability.rule_study.demo --output-dir <new empty dir outside the clone>",
    "PYTHONPATH=. python scripts/verify_rule_study.py --traces docs/evidence/rule02/traces/rules-v1"
    " --system-id rules-v1 --rules-v1 --out docs/evidence/rule02/compat/verify-rules-v1.json",
    "PYTHONPATH=. python scripts/verify_rule_study.py --traces docs/evidence/rule02/traces/greedy_a"
    " --system-id greedy_a --out docs/evidence/rule02/compat/verify-greedy_a.json",
    "PYTHONPATH=. python scripts/verify_rule_study.py --traces docs/evidence/rule02/traces/greedy_b"
    " --system-id greedy_b --out docs/evidence/rule02/compat/verify-greedy_b.json",
    "PYTHONPATH=. python docs/evidence/rule02/tools/replay_from_saved.py --traces docs/evidence/rule02/traces"
    " --out docs/evidence/rule02/compat/replay-from-saved.json",
    "python docs/evidence/rule02/tools/build_manifest.py build",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def role(rel: str) -> str:
    parts = rel.split("/")
    if parts[0] == "traces":
        if parts[-1] == "case.json":
            return "trace:case"
        if parts[-1] == "result.json":
            return "trace:result"
        return "trace:" + (parts[3] if len(parts) > 4 else "file")
    if parts[0] == "compat":
        return "compatibility"
    if parts[0] == "meta":
        return "environment-or-log"
    if parts[0] == "tools":
        return "reviewer-tool"
    return "documentation"


def listed_files() -> list[str]:
    return sorted(
        p.relative_to(EVIDENCE_DIR).as_posix()
        for p in EVIDENCE_DIR.rglob("*")
        if p.is_file() and p != MANIFEST and "__pycache__" not in p.parts
    )


def build() -> dict:
    artifacts = [
        {
            "path": rel,
            "role": role(rel),
            "sha256": sha256_file(EVIDENCE_DIR / rel),
            "bytes": (EVIDENCE_DIR / rel).stat().st_size,
        }
        for rel in listed_files()
    ]
    traces = []
    for result in sorted(EVIDENCE_DIR.glob("traces/*/*/result.json")):
        data = json.loads(result.read_text(encoding="utf-8"))
        traces.append(
            {
                "trace": result.parent.relative_to(EVIDENCE_DIR).as_posix(),
                "case_id": data["case_id"],
                "policy_id": data["policy_id"],
                "status": data["status"],
                "result_sha256": sha256_file(result),
                "case_sha256": sha256_file(result.parent / "case.json"),
                "code_commit": data["bindings"]["code_commit"],
            }
        )
    return {
        "record_kind": "rule02_evidence_manifest_v1",
        "issue": "https://github.com/ReymoT/data-center-agentic/issues/240",
        "pull_request": "https://github.com/ReymoT/data-center-agentic/pull/257",
        "study_id": "rule-study-20261119-v1",
        "adapter_version": "proposal-1",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "documentation_commit": DOCUMENTATION_COMMIT,
        "base_commit": BASE_COMMIT,
        "evidence_commit": "the commit that adds this directory; Git records it, so it is not listed here",
        "superseded_binding_commit": SUPERSEDED_BINDING,
        "superseded_binding_note": (
            "Earlier sandbox traces were bound to this SHA, which is not in the published history. Its tree is"
            " identical to the implementation commit (same Git tree hash), but those traces were not reviewer"
            " accessible and are replaced by the regenerated traces here."
        ),
        "generation_commands": GENERATION_COMMANDS,
        "claims_not_made": [
            "not independent RULE-03 verification (issue #241)",
            "binding_validation is INCOMPLETE in the compatibility reports",
            "scores are artificial score-kWh weights, not measured carbon intensity or CO2e",
            "not Matty's implementation acceptance",
        ],
        "traces": traces,
        "artifacts": artifacts,
    }


def check() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = []
    listed = {a["path"]: a for a in manifest["artifacts"]}
    for rel, entry in listed.items():
        path = EVIDENCE_DIR / rel
        if not path.is_file():
            problems.append(f"missing: {rel}")
        elif sha256_file(path) != entry["sha256"]:
            problems.append(f"changed: {rel}")
    for rel in listed_files():
        if rel not in listed:
            problems.append(f"unlisted: {rel}")
    for item in manifest["traces"]:
        if item["code_commit"] != manifest["implementation_commit"]:
            problems.append(f"binding mismatch: {item['trace']}")
    for problem in problems:
        print(problem)
    print(f"{len(listed)} artifacts listed; {len(problems)} problems")
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("build", "check"))
    args = parser.parse_args(argv)
    if args.mode == "check":
        return check()
    if MANIFEST.exists():
        raise SystemExit(f"refusing to overwrite {MANIFEST}")
    MANIFEST.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
