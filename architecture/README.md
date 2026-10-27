# Final scheduling architecture

Current update, October 25: greedy A/B and the injected-probability C/D constructor are merged with bounded receiving evidence; trained C/D artifacts, the common runner and experiments remain unfinished. The accepted-runtime CPU request retains its 120-second timeout. A zero-request metadata check identifies Matty's Arc 140V through Vulkan as the concrete host candidate, but model offload and performance are not yet validated. Current main CI passes 1,310 tests and 19 subtests. [Current receiving and host evidence](../docs/handoffs/A01_IGPU_HOST_CANDIDATE_2026-10-25.md).

The current diagram replaces the obsolete engineering image. Its flow describes the planned final-proposal scheduling study. The footer records implemented components: F02 records, D01-D03/D06 tooling, S01/S02, K02, P01, P02 A/B, the P03 probability constructor, L01 no-op preparation, E01/E04 preparation and A01-A04 cores. Trained C/D, the common runner, independent evaluation and the full pipeline remain planned; component boxes and synthetic receiving cases are not research-result evidence.

The diagram starts with the exact research question. The main comparison is the ontology-grounded, tool-verified agent versus the plain LLM. Four additional policies provide scheduling reference results. Workload scheduling is the experimental setting, and conclusions remain limited to the evaluated scenarios.

Read the [plain-language architecture](../docs/ARCHITECTURE.md) for workflow, visibility boundaries, policy differences, offline learning/evaluation and unresolved decisions. [Source review](../docs/SOURCE_REVIEW.md) explains the four related systems and design rationale. The supplied broad Model D image remains a reference outside Git and does not expand the final scope.

Files: [SVG](architecture.svg) for scalable viewing and [PNG](architecture.png) for README display. Both are generated from [render_architecture.py](../scripts/render_architecture.py), with Matplotlib from the candidate environment:

```powershell
.venv\Scripts\python.exe scripts/render_architecture.py
```

Regenerate both files together after architecture changes and inspect readability. Scientific open decisions remain in the register; the drawing does not select defaults.
