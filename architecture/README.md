# Final scheduling architecture

The current diagram replaces the obsolete engineering image. It describes the planned final-proposal scheduling study; it does not claim that components have been implemented.

Read the [plain-language architecture](../docs/ARCHITECTURE.md) for workflow, visibility boundaries, policy differences, offline learning/evaluation and unresolved decisions. [Source review](../docs/SOURCE_REVIEW.md) explains the four related systems and design rationale. The supplied broad Model D image remains a reference outside Git and does not expand the final scope.

Files: [SVG](architecture.svg) for scalable viewing and [PNG](architecture.png) for README display. Both are generated from [render_architecture.py](../scripts/render_architecture.py), with Matplotlib from the candidate environment:

```powershell
.venv\Scripts\python.exe scripts/render_architecture.py
```

Regenerate both files together after architecture changes and inspect readability. Scientific open decisions remain in the register; the drawing does not select defaults.
