"""Validate bootstrap records offline; this is not a production acceptance test."""

import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
TEAM = ROOT / "docs/team"
errors = []


def require(condition, message):
    if not condition:
        errors.append(message)


def tasks(path):
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| [ ] |"):
            fields = [field.strip() for field in line.split("|")[1:-1]]
            require(fields[1] not in records, f"Duplicate task {fields[1]} in {path.name}")
            records[fields[1]] = fields
    return records


checklist = tasks(TEAM / "03_RESPONSIBILITY_CHECKLIST.md")
require(len(checklist) == 50, "Expected the package's 50 task records")
dependencies = {}
for task_id, fields in checklist.items():
    require(fields[2] != fields[3], f"Owner is also technical contact: {task_id}")
    dependencies[task_id] = set(re.findall(r"\b[A-Z]\d{2}\b", fields[5]))
    require(dependencies[task_id] <= checklist.keys(), f"Unknown prerequisite: {task_id}")


def visit(task_id, active, complete):
    require(task_id not in active, f"Dependency cycle: {task_id}")
    if task_id in active or task_id in complete:
        return
    for prerequisite in dependencies.get(task_id, ()):
        visit(prerequisite, active | {task_id}, complete)
    complete.add(task_id)


complete = set()
for task_id in checklist:
    visit(task_id, set(), complete)
for owner in ("Matty", "Reimo", "Ved", "Edison", "Nisha"):
    role = tasks(TEAM / f"MASTER_{owner.upper()}.md")
    expected = {key: value for key, value in checklist.items() if value[2] == owner}
    require(role == expected, f"Role inventory differs from checklist: {owner}")

deployment_match = re.search(
    r"^Instruction deployment: ([0-9]+\.[0-9]+)\b",
    (ROOT / "PROJECT_MASTER.md").read_text(encoding="utf-8"),
    re.MULTILINE,
)
require(deployment_match is not None, "Project master must declare instruction deployment")
version_paths = sorted(TEAM.glob("MASTER_*.md")) + sorted(TEAM.glob("0[0-4]_*.md"))
require(len(version_paths) == 10, "Expected five numbered files and five role masters")
if deployment_match:
    deployment = deployment_match.group(1)
    for path in version_paths:
        match = re.search(
            r"^Version: ([0-9]+\.[0-9]+)\b", path.read_text(encoding="utf-8"), re.MULTILINE
        )
        require(
            match is not None and match.group(1) == deployment,
            f"Instruction deployment differs or is missing: {path.relative_to(ROOT)}",
        )
    require(
        (TEAM / "CHANGELOG.md")
        .read_text(encoding="utf-8")
        .startswith(f"# Instruction deployment changelog\n\nCurrent deployment: {deployment} "),
        "Changelog current deployment differs from project master",
    )

interface_path = ROOT / "docs/INTERFACES.md"
schema_path = ROOT / "dc_sustainability/schemas.py"
require(interface_path.is_file(), "Missing canonical F02 interface document")
require(schema_path.is_file(), "Missing implemented F02 schemas")
if interface_path.is_file() and schema_path.is_file():
    document_version = re.search(
        r"Contract version:\*\* ([0-9]+\.[0-9]+\.[0-9]+)",
        interface_path.read_text(encoding="utf-8"),
    )
    schema_version = re.search(
        r'^SCHEMA_VERSION = "([0-9]+\.[0-9]+\.[0-9]+)"',
        schema_path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    require(
        document_version is not None
        and schema_version is not None
        and document_version.group(1) == schema_version.group(1),
        "Canonical interface contract version differs from implemented schemas",
    )
legacy_interface = ROOT / "docs/Interfaces F02"
require(
    legacy_interface.is_file()
    and legacy_interface.stat().st_size < 1000
    and "[INTERFACES.md](INTERFACES.md)" in legacy_interface.read_text(encoding="utf-8"),
    "Alternate F02 path must remain a short compatibility pointer",
)

for path in ROOT.rglob("*.md"):
    if any(part in {".git", ".venv", "tmp"} for part in path.relative_to(ROOT).parts):
        continue
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            continue
        relative = unquote(target.split("#", 1)[0])
        require(
            (path.parent / relative).exists(), f"Broken link: {path.relative_to(ROOT)} -> {target}"
        )

config = json.loads((ROOT / "configs/project.example.json").read_text(encoding="utf-8"))
require(config["status"] == "template_only_not_runnable", "Configuration must be marked template")
require(
    config["systems"]
    == ["agent", "plain_llm", "greedy_a", "greedy_b", "decision_tree_c", "random_forest_d"],
    "Six-system registry differs from final scope",
)
require(
    config["unresolved_decisions"] == {f"Q{i:02}": None for i in range(1, 14)},
    "Bootstrap must not select unresolved Q01-Q13 decisions",
)
for name in ("requirements-core.in", "requirements-windows-py312.lock.txt"):
    require((ROOT / "requirements" / name).is_file(), f"Missing dependency input: {name}")
for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
    if line and not line.startswith("#"):
        require(line.endswith("="), "Environment example must contain blank placeholders only")
tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
readme = (ROOT / "README.md").read_text(encoding="utf-8")
require(readme.startswith("Teammates and roles\n"), "README must start with teammates and roles")
require("https://github.com/MattyAnd" in readme, "Matty's confirmed GitHub ID is missing")
for name in ("AssetOps", "LC-Opt", "DeepMind", "Resource Advisor"):
    require(name in readme, f"Reviewed system disclosure missing: {name}")
require(
    (TEAM / "02_INTERFACE_CONTRACTS.md").stat().st_size < 1000,
    "Package contract must remain a pointer, not a duplicate specification",
)
merge_rule = (
    "A pull request can be merged once its checks pass. "
    "A teammate review is welcome but not required. "
    "Changes to shared data formats or settings still need the affected teammates to agree first."
)
policy_paths = [ROOT / "AGENTS.md", ROOT / "PROJECT_MASTER.md"] + [
    TEAM / f"MASTER_{owner}.md" for owner in ("MATTY", "NISHA", "REIMO", "VED", "EDISON")
]
instruction_authority = (
    "The masters and shared instructions published on GitHub's main branch "
    "are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. "
    "Other teammates and their AI assistants must not edit, overwrite, replace, delete "
    "or publish new versions without Matty's explicit authorization."
)
for path in policy_paths:
    require(path.is_file(), f"Missing shared-policy file: {path.relative_to(ROOT)}")
    if path.is_file():
        require(
            merge_rule in path.read_text(encoding="utf-8"),
            f"Fixed merge rule differs or is missing: {path.relative_to(ROOT)}",
        )
        require(
            instruction_authority in path.read_text(encoding="utf-8"),
            f"Instruction authority differs or is missing: {path.relative_to(ROOT)}",
        )
coding_decision_rule = "The coder responsible for a component owns its internal implementation decisions within the agreed scope and contracts. Routine internal choices do not require prior approval from the technical contact, another teammate or Matty.\n\nFor changes to shared interfaces, settings or scientific rules, the coding owner leads the exact proposal and obtains agreement from only the directly affected owners before implementation.\n\nRecord the coding decision owner, exact change, directly affected consumers, required tests, request time and response deadline in the Issue or decision record. An unanswered or unresolved shared decision must be escalated by the coding owner to Matty within 24 elapsed hours for a short resolution meeting. Silence is not approval.\n\nImplement, test and publish the agreed independent portions immediately while a disputed portion is pending. Block only the specific affected behavior or acceptance step; do not hold the whole task when other work is ready.\n\nExisting task ownership, main-instruction authority, merge rules, independent scientific evaluation and model-call authorization remain unchanged."
coding_policy_paths = policy_paths + [
    TEAM / "01_SHARED_RULES.md",
    ROOT / "docs/decisions/Q11_CODER_OWNED_DECISIONS.md",
]
for path in coding_policy_paths:
    require(path.is_file(), f"Missing coding-decision policy: {path.relative_to(ROOT)}")
    if path.is_file():
        require(
            coding_decision_rule in path.read_text(encoding="utf-8"),
            f"Coder-owned decision rule differs or is missing: {path.relative_to(ROOT)}",
        )

if errors:
    print("Bootstrap validation failed:\n" + "\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print("PASS: 50 task records, role inventories, acyclic dependencies, local Markdown links,")
print("      deployment/contract versions, canonical interface pointer, config placeholders,")
print("      dependency inputs, README preferences and seven-file policy rules.")
