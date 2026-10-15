# Publication audit

Instruction deployment: 1.10 - 2026-10-15. Current maintenance is recorded in [the D03 consumer handoff](../handoffs/A03_D03_F04_F05.md). The dated evidence below describes prior publications.

Previous deployment: 1.9 - 2026-10-12. Current scope is Matty's A01/A03 agreed core and supplied hardware. [The implementation handoff](../handoffs/A01_A03_AGREED_CORE.md) links issues #6/#7, code, tests and limits. [The previous maintenance handoff](../handoffs/F03_F04_F05_MAINTENANCE.md) retains its historical evidence. This is a publication audit, not a formal reviewer-approval gate.

Deployment 1.10 verification: 742 tests and 19 subtests passed locally, including
29 actual D03-to-checker consumer cases. Lint/format (41 Python files), compilation,
setup, pip, dependency smoke and whitespace passed. Architecture SVG/PNG were
visually checked; README's new catalog command ran successfully. The handoff records
the observed Windows CRLF/Git LF hash difference with equal JSON content. All task
allocations, seven-file policies, schemas/interface bytes, teammate code/manifests
and locks remain unchanged. Q01-Q06 remain pending where documented; partial
consumer evidence does not establish full A03, simulator or scientific acceptance.

Affected files were checked for scope, unresolved decisions, identity, exclusions and honest implementation status. README retains equally formatted roles, Matty/Nisha together, and the reviewed systems/rationale. Architecture text and visually inspected SVG/PNG identify F02/D01 and A01/A03 core as implemented, with the complete pipeline still planned. Hardware publication excludes raw screenshot and device/product IDs.

The canonical interface, schema code/examples, carbon code/manifests, dependency locks and all teammate commits are preserved. Source attachments are untouched. Setup validation confirms 50 unique tasks, matching role tables, acyclic dependencies, links, blank configuration, deployment 1.9 alignment and identical seven-file merge/authority rules. No shared data format, generation setting, scientific choice or ownership changed.

Local verification passed 258 tests and 19 subtests, lint, formatting, compilation, pip consistency, dependency smoke, setup and whitespace checks. The 65 new tests exercise actual fixed-checker logic and actual local HTTP transport with labeled synthetic server responses. The server is test-only; no model inference, execution approval, independent scientific evaluation or live integration is claimed. Q01-Q04 and remaining Q09 deployment/context/projection/resource inputs still block full A01/A03 acceptance. F03's final provider-inclusive/platform acceptance remains pending.

Matty authorizes direct publication to main. No formal review request, independent approval or successful scientific experiment is claimed. The original package archive remains unchanged outside Git.

## Subsequent A01/F03 model setup

On 2026-10-12, Matty authorized the independent installation and identity-recording
step. [The model setup handoff](../handoffs/A01_F03_MODEL_SETUP.md) records successful
Qwen3 8B Q4_K_M installation, complete digest/license metadata, six independently
verified stored blobs and a fresh matching metadata comparison. Weights and private
machine identifiers stay outside Git. No model inference or GPU measurement ran.

The repository now passes 264 tests and 19 subtests, lint, formatting (36 Python
files), compilation, pip consistency, setup validation and whitespace checks.
Six new inventory tests use labeled synthetic metadata and cover actual validation
failures; they are not evidence of inference. Shared schemas, dependencies, model
generation settings, scientific decisions and the seven-file policies are preserved.
Instruction deployment remains 1.9. Full A01/F03 integration and acceptance still
need the documented run inputs and consumer evidence.
