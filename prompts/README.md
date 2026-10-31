# Prompt preparation

Owner: Nisha, with Matty reviewing agent prompts. Q09 fixes the shared provider settings in Matty's adapter; prompts never set model options. F02/L02 settle structured output and evidence requirements. The plain system has one call without feedback/repair/fallback. Agent explanations cannot modify approved actions. Freeze prompt hashes before held-out evaluation.

| File | Used by | Purpose |
|---|---|---|
| `shared/task_rules.md` | plain LLM; offered to the agent | Scheduling, impact and evidence rules both LLM systems should see identically |
| `shared/explanation_rules.md` | plain LLM; offered to the agent | What an explanation must state and must not claim |
| `plain_llm/system.md` | plain LLM (L01) | One-response instructions; includes both shared files |
| `plain_llm/user.md` | plain LLM (L01) | Exact output identifiers plus the flat context JSON |
| `agent/system.md` | Agent proposal (A02) | Shared scheduling rules plus explicit no-claim boundaries |
| `agent/proposal.md` | Agent proposal (A02) | Exact Plan identifiers plus graph-equivalent visible context JSON |

Status: development drafts, not frozen. The shared rules include the accepted scheduling
boundaries, and the proposal renderer requires one disposition for every visible waiting
job. The flat and graph representations carry the same F02 `ContextContent` facts.
`dc_sustainability.llm.plain.prompt_template_sha256()` hashes the plain prompt files with
normalized line endings for the freeze manifest.

The reviewed Agent proposal renderer is `dc_sustainability.agent.renderers.render_proposal`.
It returns a Plan only and provides no tool, repair, fallback, explanation or execution
path. Its prompt-file hash is recorded by `proposal_template_sha256()`.
