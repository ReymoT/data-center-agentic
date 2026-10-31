"""Reviewed production prompt rendering for the A02 Agent proposal stage.

This module renders visible K02 context only. It calls no model, checker, tool,
fallback, simulator or runtime. Repair and explanation renderers remain unavailable
until their separate inputs are reviewed.
"""

import hashlib
from collections.abc import Sequence
from pathlib import Path
from string import Template

from dc_sustainability import schemas as s

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROPOSAL_PROMPT_FILES = (
    "shared/task_rules.md",
    "agent/system.md",
    "agent/proposal.md",
)


def _read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def proposal_template_sha256() -> str:
    """Hash every file used by the Agent proposal renderer."""
    digest = hashlib.sha256()
    for name in PROPOSAL_PROMPT_FILES:
        digest.update(name.encode("utf-8") + b"\0" + _read_prompt(name).encode("utf-8") + b"\0")
    return digest.hexdigest()


def render_proposal(context: s.Context) -> list[dict[str, str]]:
    """Render one Agent Plan request from a validated graph context."""
    context = s.Context.model_validate(
        context.model_dump(mode="python", warnings="none"), strict=True
    )
    if context.representation != "graph":
        raise ValueError("the Agent proposal receives the graph context representation")
    system = Template(_read_prompt("agent/system.md")).substitute(
        task_rules=_read_prompt("shared/task_rules.md")
    )
    user = Template(_read_prompt("agent/proposal.md")).substitute(
        schema_version=s.SCHEMA_VERSION,
        episode_id=context.content.episode_id,
        slot=context.content.current_slot,
        state_version=context.content.state_version,
        context_json=context.content.to_json(),
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def messages_sha256(messages: Sequence[dict[str, str]]) -> str:
    """Canonical hash recorded by a later run manifest."""
    return s.sha256_hex([dict(message) for message in messages])
