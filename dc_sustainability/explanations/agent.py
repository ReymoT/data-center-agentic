"""L02 production renderer for the A02 Agent explanation stage.

The harness calls ``render_explanation(context, selected)`` after a stage has passed
its independent check. The explanation describes that approved plan only: it cannot
return or replace a Plan, it is provisional until the controller's final recheck, and
the prompt forbids claiming execution, savings, or any check, tool, repair or source
that did not happen. The renderer calls no model, checker, simulator or runtime.
"""

import hashlib
from pathlib import Path
from string import Template

from dc_sustainability import schemas as s

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
EXPLANATION_PROMPT_FILES = (
    "shared/task_rules.md",
    "shared/explanation_rules.md",
    "agent/explanation_system.md",
    "agent/explanation.md",
)


def _read_prompt(name: str) -> str:
    # Normalize line endings so Git checkout settings cannot change prompt hashes.
    return (PROMPT_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def explanation_template_sha256() -> str:
    """Hash every file used by the Agent explanation renderer, for the freeze manifest."""
    digest = hashlib.sha256()
    for name in EXPLANATION_PROMPT_FILES:
        digest.update(name.encode("utf-8") + b"\0" + _read_prompt(name).encode("utf-8") + b"\0")
    return digest.hexdigest()


def render_explanation(context: s.Context, selected: s.StageRecord) -> list[dict[str, str]]:
    """Render the Agent explanation request for one checked, passing stage."""
    context = s.Context.model_validate(
        context.model_dump(mode="python", warnings="none"), strict=True
    )
    if context.representation != "graph":
        raise ValueError("the Agent explanation receives the graph context representation")
    selected = s.StageRecord.model_validate(
        selected.model_dump(mode="python", warnings="none"), strict=True
    )
    plan, c = selected.plan, context.content
    if (plan.episode_id, plan.slot, plan.state_version) != (
        c.episode_id,
        c.current_slot,
        c.state_version,
    ):
        raise ValueError("the selected stage does not match the explanation context")
    if selected.check is None or selected.check.status != "pass":
        raise ValueError("only a checked, passing plan is explained")
    system = Template(_read_prompt("agent/explanation_system.md")).substitute(
        task_rules=_read_prompt("shared/task_rules.md"),
        explanation_rules=_read_prompt("shared/explanation_rules.md"),
    )
    user = Template(_read_prompt("agent/explanation.md")).substitute(
        episode_id=c.episode_id,
        slot=c.current_slot,
        state_version=c.state_version,
        plan_json=plan.to_json(),
        check_json=selected.check.to_json(),
        context_json=c.to_json(),
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
