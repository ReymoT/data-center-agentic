# Prompt preparation

Owner: Nisha, with Matty reviewing agent prompts. Q09 fixes the shared provider settings in Matty's adapter; prompts never set model options. F02/L02 settle structured output and evidence requirements. The plain system has one call without feedback/repair/fallback. Agent explanations cannot modify approved actions. Freeze prompt hashes before held-out evaluation.

| File | Used by | Purpose |
|---|---|---|
| `shared/task_rules.md` | plain LLM; offered to the agent | Scheduling, impact and evidence rules both LLM systems should see identically |
| `shared/explanation_rules.md` | plain LLM; offered to the agent | What an explanation must state and must not claim |
| `plain_llm/system.md` | plain LLM (L01) | One-response instructions; includes both shared files |
| `plain_llm/user.md` | plain LLM (L01) | Exact output identifiers plus the flat context JSON |

Status: development drafts, not frozen. They state no Q01 rule for starts in completion slots and no Q02/Q03 coverage or abstention rule; update them when those decisions are accepted. The flat context is the F02 `ContextContent` JSON until K02 publishes the agreed projection. `dc_sustainability.llm.plain.prompt_template_sha256()` hashes these files with normalized line endings for the freeze manifest.
