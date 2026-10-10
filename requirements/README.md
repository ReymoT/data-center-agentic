# Candidate environment

The files here are byte-identical copies of package 1.0's proposed core input and Windows x64 CPython 3.12 lock. The lock was dependency-resolved before this task; runtime validation in this branch must be reported separately in [the handoff](../docs/handoffs/F01.md). Provider SDK/settings remain unresolved Q09. Supported platforms and Python adoption remain Q13. Do not claim this is the final environment.

Create an isolated Python 3.12 environment, install using `--require-hashes`, run `pip check`, `scripts/smoke_dependencies.py`, Ruff check/format, then the offline bootstrap validator as shown in [README](../README.md). Package installation requires network access; smoke execution itself is offline and uses no model.

The smoke script verifies all direct imports, a SHACL validation and SPARQL query, a certified tiny integer program, both classifier save/load predictions, and a bounded LangGraph route. These verify dependencies, not the project algorithms or safety.

Ordinary PR/main CI validates bootstrap records, installs the hashed Windows candidate, checks dependencies, runs offline smoke operations and checks lint/format/compilation. Installation contacts the package index; execution uses no external data or model service. Production unit/contract tests should be added as implementations arrive. The workflow is prepared, not yet observed on GitHub. A Windows dependency-lock check must not be silently copied to Linux/macOS. Regenerate each accepted lock from the reviewed input after provider/stack changes; retain resolved hashes and validate imports and consumer behavior.

Troubleshooting: confirm 64-bit CPython 3.12 and matching wheel target. On hash failure stop and verify the input/lock; do not disable hashes. On unavailable pinned versions, record evidence and review a replacement rather than substituting versions. On missing pip/venv support use an actual full Python installation or a packaged pip installer that targets the isolated environment. Do not edit global Python packages. Missing provider settings block live calls, not foundation checks.
