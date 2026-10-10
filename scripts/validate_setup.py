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
if errors:
    print("Bootstrap validation failed:\n" + "\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print("PASS: 50 task records, role inventories, acyclic dependencies, local Markdown links,")
print("      config placeholders, dependency inputs, environment example and README preferences.")
