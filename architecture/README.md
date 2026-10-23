# Final scheduling architecture

The current diagram replaces the obsolete engineering image. Its flow describes the planned final-proposal scheduling study. The footer records implemented components: F02 records, D01-D03/D06 tooling, S01 transitions, K02 controlled retrieval with the existing F02 Context, P01 arithmetic pending S02 adoption, L01 no-op preparation, E01 replay/E04 draft review preparation and A01/A03 core. K02 has bounded Matty consumer evidence, while policies beyond P01, execution gate, agent and full pipeline remain planned; component boxes and synthetic review cases are not integrated execution or research-result evidence.

The diagram starts with the exact research question. The main comparison is the ontology-grounded, tool-verified agent versus the plain LLM. Four additional policies provide scheduling reference results. Workload scheduling is the experimental setting, and conclusions remain limited to the evaluated scenarios.

Read the [plain-language architecture](../docs/ARCHITECTURE.md) for workflow, visibility boundaries, policy differences, offline learning/evaluation and unresolved decisions. [Source review](../docs/SOURCE_REVIEW.md) explains the four related systems and design rationale. The supplied broad Model D image remains a reference outside Git and does not expand the final scope.

Files: [SVG](architecture.svg) for scalable viewing and [PNG](architecture.png) for README display. Both are generated from [render_architecture.py](../scripts/render_architecture.py), with Matplotlib from the candidate environment:

```powershell
.venv\Scripts\python.exe scripts/render_architecture.py
```

Regenerate both files together after architecture changes and inspect readability. Scientific open decisions remain in the register; the drawing does not select defaults.
