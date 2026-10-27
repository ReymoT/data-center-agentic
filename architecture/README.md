# Final scheduling architecture

Current update, October 27: greedy A/B, the C/D probability constructor, Q07 feature/collection code, provisional D04 splits and the agreed primary Q10 sampler are merged; trained C/D artifacts, the common runner and experiments remain unfinished. Nisha and Ved accept the accepted-runtime Arc 140V/Vulkan setting for both systems, but model offload and performance are not yet validated and a fresh bounded run authorization is still required. Current main passes 1,468 tests and 19 subtests. [Current intake](../docs/handoffs/OCT27_A01_Q07_F04_F05.md).

The current diagram replaces the obsolete engineering image. Its flow describes the planned final-proposal scheduling study. The footer records implemented components: F02 records, D01-D04/D06 tooling, S01/S02, K02, P01, P02 A/B, P03 constructor/features/collection, L01 preparation, E01/E04/E05 preparation, primary Q10 sampling and A01-A04 cores. Trained C/D, the common runner, completed independent evaluation and the full pipeline remain planned; component boxes and synthetic receiving cases are not research-result evidence.

The diagram starts with the exact research question. The main comparison is the ontology-grounded, tool-verified agent versus the plain LLM. Four additional policies provide scheduling reference results. Workload scheduling is the experimental setting, and conclusions remain limited to the evaluated scenarios.

Read the [plain-language architecture](../docs/ARCHITECTURE.md) for workflow, visibility boundaries, policy differences, offline learning/evaluation and unresolved decisions. [Source review](../docs/SOURCE_REVIEW.md) explains the four related systems and design rationale. The supplied broad Model D image remains a reference outside Git and does not expand the final scope.

Files: [SVG](architecture.svg) for scalable viewing and [PNG](architecture.png) for README display. Both are generated from [render_architecture.py](../scripts/render_architecture.py), with Matplotlib from the candidate environment:

```powershell
.venv\Scripts\python.exe scripts/render_architecture.py
```

Regenerate both files together after architecture changes and inspect readability. Scientific open decisions remain in the register; the drawing does not select defaults.
