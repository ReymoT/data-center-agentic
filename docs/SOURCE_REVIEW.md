# Source review and architecture rationale

Reviewed on 2026-10-10 for this bootstrap. The final October proposal is the scope authority. The supplied Model D review and image explain prior design exploration, not broader implementation requirements.

## Supplied material

- `Team_Master_Instructions.zip`: package 1.0, all five masters, numbered files 00-04, review record and dependency references. Extracted Markdown matched the existing workspace package byte for byte. Repository adaptations are recorded in [the changelog](team/CHANGELOG.md).
- `Data_Center_Sustainability_Proposal.doc`: final proposal, SHA256 `0518ad96355083269dbd342d3adab10fcd8b867d7730015315cfe41f0c095f0a`. Read the legacy Word text including scope, E1-E6, evaluation, timeline, team division and references.
- `Model_D_Review_with_LangGraph.pdf`: two-page earlier review of related systems and workflow, including the broad diagram. Reviewed text and the supplied diagram; no external system was reproduced.
- `Model_D_LangGraph_Architecture.jpg`: earlier broad Model D architecture. The narrower final proposal supersedes its digital twin, enterprise telemetry and water/cooling scope.
- The obsolete repository engineering image was replaced with an original diagram of the final scheduling study. [SVG](../architecture/architecture.svg) and [PNG](../architecture/architecture.png) share one maintained [drawing script](../scripts/render_architecture.py).

Original attachments remain outside Git. This record stores provenance without redistributing them or assuming a license.

## Comparison method and sources

The supplied review asked about data, linked assets/measurements, LLM versus deterministic work, testing, uncertainty, unsafe actions and human approval. The final proposal uses the same systems as motivation:

- [AssetOpsBench](https://arxiv.org/abs/2506.03828) and [industrial knowledge graph research](https://arxiv.org/abs/2605.26874): typed relationships and exact retrieval motivate our evidence graph.
- [LC-Opt](https://arxiv.org/abs/2511.00116): simulation motivates testing decisions before applying them; our simulator is workload scheduling, not a Modelica cooling twin.
- [DeepMind cooling](https://deepmind.google/blog/safety-first-ai-for-autonomous-data-centre-cooling-and-industrial-control/): checks, fallback and oversight motivate bounded verified execution.
- [Resource Advisor Copilot](https://www.se.com/ww/en/about-us/newsroom/news/press-releases/building-sustainability%E2%80%99s-digital-future-with-ecostruxure%E2%84%A2-resource-advisor-copilot-schneider-electric%E2%80%99s-latest-ai-advancement-64eca1cf6053e3d1d90ab96e/): sustainability decision support motivates evidence-linked explanations.
- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview): the proposal's workflow framework, distinct from the domain RDF graph.

The public reference pages were checked on 2026-10-10. The comparison is a synthesis of the supplied review and final proposal; it is not an audit of deployed systems, a copied proprietary design or an empirical superiority claim. We select connected evidence, exact calculations, bounded routing and independent evaluation because they address our research question within course scope. Future results must establish actual accuracy, faithfulness and safety.
