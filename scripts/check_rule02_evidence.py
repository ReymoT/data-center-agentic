"""Check historical RULE02 evidence bytes and Git bindings without executing a policy.

This is artifact receiving, not current-system replay, independent scientific acceptance,
or authentication of the implementer's reported runtime. Original evidence is read-only.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/rule02"
IMPLEMENTATION = "176361ad23ba57940b1576828893ce3a7b1a1666"
SPEC = "9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return (
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def safe_path(root, rel):
    if not isinstance(rel, str) or not rel or "\\" in rel or ":" in rel:
        raise ValueError("unsafe evidence path")
    p = PurePosixPath(rel)
    if p.is_absolute() or any(x in ("", ".", "..") for x in rel.split("/")):
        raise ValueError("unsafe evidence path")
    target = root
    for part in p.parts:
        target = target / part
        if target.is_symlink() or target.is_junction():
            raise ValueError("linked evidence path")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("evidence path escaped root")
    return target


def check_inventory(root, manifest):
    entries = manifest["artifacts"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 2000:
        raise ValueError("invalid artifact count")
    listed = set()
    for entry in entries:
        rel = entry["path"]
        path = safe_path(root, rel)
        if rel in listed or rel == "MANIFEST.json":
            raise ValueError("duplicate or self-listed artifact")
        listed.add(rel)
        if not re.fullmatch("[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("invalid artifact digest")
        size = entry["bytes"]
        if type(size) is not int or not 0 <= size <= 8 * 1024 * 1024:
            raise ValueError("invalid artifact size")
        if (
            not path.is_file()
            or path.stat().st_size != size
            or digest(path.read_bytes()) != entry["sha256"]
        ):
            raise ValueError(f"artifact bytes differ: {rel}")
    actual = set()
    for path in root.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        safe_path(root, rel)
        if path.is_file() and rel != "MANIFEST.json":
            actual.add(rel)
    if actual != listed:
        raise ValueError("missing or unlisted artifacts")
    return len(listed)


def historical_bindings(repo):
    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True).stdout

    def blob(path):
        return git("show", f"{IMPLEMENTATION}:{path}")

    git("merge-base", "--is-ancestor", IMPLEMENTATION, "HEAD")
    sources = (
        git("ls-tree", "--name-only", IMPLEMENTATION, "dc_sustainability/rule_study/")
        .decode()
        .splitlines()
    )
    source_map = {
        Path(p).name: digest(blob(p).replace(b"\r\n", b"\n")) for p in sources if p.endswith(".py")
    }
    if len(source_map) != 6:
        raise ValueError("unexpected historical adapter sources")
    bindings = {
        "code_commit": IMPLEMENTATION,
        "adapter_source_sha256": digest(canonical(source_map)),
        "spec_sha256": digest(canonical(json.loads(blob("docs/rule_study/specification.json")))),
        "generator_source_sha256": digest(
            blob("dc_sustainability/evaluation/rule_study_generator.py").replace(b"\r\n", b"\n")
        ),
        "environment_lock_sha256": digest(
            blob("requirements/requirements-windows-py312.lock.txt").replace(b"\r\n", b"\n")
        ),
    }
    if bindings["spec_sha256"] != SPEC:
        raise ValueError("historical specification differs from accepted pin")
    return bindings


def check_evidence(root=EVIDENCE, repo=ROOT):
    manifest = read_json(root / "MANIFEST.json")
    count = check_inventory(root, manifest)
    if manifest["implementation_commit"] != IMPLEMENTATION:
        raise ValueError("unexpected implementation commit")
    bindings = historical_bindings(repo)
    expected = {
        (p, c) for p in ("rules-v1", "greedy_a", "greedy_b") for c in ("A", "B", "B-progress")
    }
    expected.add(("rules-v1", "B-fault"))
    seen = set()
    decisions = 0
    for item in manifest["traces"]:
        directory = safe_path(root, item["trace"])
        result = read_json(directory / "result.json")
        key = (result["policy_id"], result["case_id"])
        if (
            key in seen
            or key not in expected
            or directory != root / "traces" / key[0] / f"{key[1]}-{key[0]}"
        ):
            raise ValueError("duplicate or unexpected trace identity")
        seen.add(key)
        case_hash = digest((directory / "case.json").read_bytes())
        exact_bindings = dict(bindings, case_sha256=case_hash)
        if result["bindings"] != exact_bindings or item["code_commit"] != IMPLEMENTATION:
            raise ValueError("record bindings differ from historical Git artifacts")
        if (
            item["result_sha256"] != digest((directory / "result.json").read_bytes())
            or item["case_sha256"] != case_hash
            or item["policy_id"] != key[0]
            or item["case_id"] != key[1]
            or item["status"] != result["status"]
        ):
            raise ValueError("trace summary differs from actual files")
        paths = sorted((directory / "decisions").glob("*.json"))
        if [p.name for p in paths] != [f"decision-{n:02d}.json" for n in range(30)]:
            raise ValueError("missing or extra decision")
        if result["decision_sha256s"] != [digest(p.read_bytes()) for p in paths]:
            raise ValueError("result does not bind decision bytes")
        for n, path in enumerate(paths):
            record = read_json(path)
            if (
                record["bindings"] != exact_bindings
                or record["decision_index"] != n
                or (record["policy_id"], record["case_id"]) != key
                or record["model_call_count"] != 0
            ):
                raise ValueError("decision identity or bindings differ")
            before, execution = record["state_before"], record["execution"]
            references = [
                ("states", before["visible_state_sha256"]),
                ("snapshots", before["constraint_snapshot_sha256"]),
            ]
            if execution["state_after"] is not None:
                references.append(("states", execution["state_after"]["state_sha256"]))
            for folder, sha in references:
                if (
                    not re.fullmatch("[0-9a-f]{64}", sha)
                    or digest((directory / folder / f"{sha}.json").read_bytes()) != sha
                ):
                    raise ValueError("raw state or snapshot hash mismatch")
            ref = f"transitions/transition-{n:02d}.json"
            if (
                execution["transition_ref"] != ref
                or digest((directory / ref).read_bytes()) != execution["transition_sha256"]
            ):
                raise ValueError("raw transition hash mismatch")
            decisions += 1
    if seen != expected:
        raise ValueError("missing authored trace")
    return {
        "status": "HISTORICAL_ARTIFACTS_CHECKED",
        "artifacts": count,
        "traces": len(seen),
        "decisions": decisions,
        "implementation_commit": IMPLEMENTATION,
        "current_implementation_verified": False,
        "runtime_environment_authenticated": False,
        "independent_scientific_acceptance": False,
        "model_or_policy_executed": False,
    }


if __name__ == "__main__":
    print(json.dumps(check_evidence(), indent=2, sort_keys=True))
