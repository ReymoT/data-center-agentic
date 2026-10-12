"""Draw the final-proposal architecture; this does not execute the study."""

from pathlib import Path

from matplotlib import rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]


def main():
    with rc_context({"font.family": "DejaVu Sans", "svg.fonttype": "none", "svg.hashsalt": "dc"}):
        fig = Figure(figsize=(16, 17), facecolor="#f6f8fc")
        FigureCanvasAgg(fig)
        ax = fig.add_axes((0.025, 0.025, 0.95, 0.95))
        ax.set(xlim=(0, 100), ylim=(0, 124))
        ax.axis("off")

        def text(x, y, value, size=12, weight="normal", color="#203449"):
            ax.text(x, y, value, fontsize=size, weight=weight, color=color, va="top")

        def box(x, y, width, height, title, body, fill="#ffffff", edge="#aac0d5", size=12):
            ax.add_patch(
                FancyBboxPatch(
                    (x, y),
                    width,
                    height,
                    boxstyle="round,pad=0.35,rounding_size=0.7",
                    linewidth=1.2,
                    edgecolor=edge,
                    facecolor=fill,
                )
            )
            text(x + 1, y + height - 1, title, 13, "bold")
            text(x + 1, y + height - 3.5, body, size)

        def arrow(x, start, end):
            ax.add_patch(
                FancyArrowPatch(
                    (x, start),
                    (x, end),
                    arrowstyle="-|>",
                    mutation_scale=15,
                    linewidth=1.5,
                    color="#63829e",
                )
            )

        text(1, 123, "Data Center Sustainability Agent", 25, "bold")
        text(1, 119.5, "Final scheduling study | Planned architecture | 12 October 2026", 14)
        text(1, 116.5, "RESEARCH QUESTION", 12, "bold")
        text(
            1,
            114,
            "Does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety\n"
            "of data-center sustainability recommendations compared with a plain LLM?",
            13,
        )
        text(
            1,
            108.5,
            "Main comparison: agent versus plain_llm. Four additional policies provide scheduling references.",
            12,
        )
        text(
            1,
            105.5,
            "One simulated site; hourly slots; fixed power, cooling and battery behavior.",
            13,
        )
        text(
            1, 99, "DESIGN INSPIRATIONS — related systems, not implemented integrations", 12, "bold"
        )
        for x, title, body, fill in (
            (1, "AssetOps KG / Bench", "Typed facts and exact retrieval", "#e5f3ef"),
            (26, "LC-Opt", "Test decisions in simulation", "#eee9f8"),
            (51, "DeepMind cooling", "Checks and checked fallback", "#fff0df"),
            (76, "Resource Advisor", "Evidence-linked explanations", "#e5effb"),
        ):
            box(x, 90, 23, 7, title, body, fill, size=10.5)

        text(1, 87.5, "1  SHARED VISIBLE INPUTS", 12, "bold")
        for x, title, body in (
            (1, "Arrived jobs", "Waiting/running work\nNo future arrivals"),
            (26, "Carbon forecasts", "Up to 24 visible slots\nIssue time, units, source IDs"),
            (51, "Site constraints", "100 kW IT, 40 kW background\nPUE 1.2 is an assumption"),
            (76, "Evidence records", "Versions and checksums\nProvenance and fact IDs"),
        ):
            box(x, 77, 23, 8, title, body, size=11)
        arrow(50, 76.5, 74.3)
        box(
            1,
            65,
            98,
            9,
            "2  VISIBLE STATE AND EQUIVALENT CONTEXT",
            "Simulator exposes arrived jobs and occupancy; one authoritative constraint snapshot feeds all systems.\n"
            "RDF + SHACL + controlled SPARQL provide typed facts and IDs; flat context carries equivalent information.\n"
            "Nisha's common runner asks policies for proposals; policies cannot mutate the simulator.",
            "#e5f3ef",
            size=12,
        )
        for x in (21, 55, 85):
            arrow(x, 64.5, 62.3)
        box(
            1,
            43,
            39,
            19,
            "3A  agent — LangGraph workflow",
            "Read state → retrieve → propose\n"
            "Verify using the production checker\n"
            "At most one repair → verify again\n"
            "If needed: checked greedy-A fallback\n"
            "Then gate execution or abstain/escalate\n"
            "Evidence-based explanation cannot alter action\n"
            "Max 3 model calls, including explanation/retries",
            "#e5f3ef",
            edge="#2a9480",
            size=11.5,
        )
        box(
            42,
            43,
            26,
            19,
            "3B  plain_llm",
            "Equivalent flat facts\n"
            "Same provider and settings\n"
            "One model call\n"
            "No tools or corrective feedback\n"
            "No repair or fallback\n"
            "Original output retained for scoring\n"
            "Unsafe starts can still be blocked",
            "#e5effb",
            edge="#478ac9",
            size=11.5,
        )
        box(
            70,
            43,
            29,
            19,
            "3C  Additional references",
            "greedy_a: earliest feasible starts\n"
            "greedy_b: lower forecast emissions\n"
            "decision_tree_c: trained classifier\n"
            "random_forest_d: trained classifier\n"
            "All use the same visible inputs\n"
            "Templates; no model calls\n"
            "No online exact solver",
            "#eee9f8",
            edge="#9374bc",
            size=11.5,
        )
        for x in (21, 55, 85):
            arrow(x, 42.5, 40.3)
        box(
            1,
            31,
            98,
            9,
            "4  SHARED VERIFICATION AND EXECUTION",
            "Production checker → latest-state gate → controller-only execute_step → simulator advances once per slot.\n"
            "Check IDs, capacity, deadlines, evidence, plan hash and state version; execute eligible current starts only.\n"
            "Rejection starts no new jobs; running work continues. Future plan entries remain intentions.",
            "#fff0df",
            edge="#cc8b39",
            size=12,
        )
        arrow(50, 30.5, 28.3)
        box(
            1,
            16,
            46,
            12,
            "5  SAVED OUTPUTS AND TRACES",
            "Record original, repaired, fallback and final outputs;\n"
            "record gate verdict and actually executed actions.\n"
            "Keep source IDs, calculations, units, assumptions,\n"
            "call counts, costs and failures for audit/scoring.",
            size=12,
        )
        ax.add_patch(FancyArrowPatch((47.7, 22), (50.3, 22), arrowstyle="-|>", mutation_scale=15))
        box(
            51,
            16,
            48,
            12,
            "6  INDEPENDENT OFFLINE EVALUATION",
            "Nisha's validator uses separate implementation.\n"
            "Accuracy, faithfulness, safety; energy, carbon,\n"
            "completed work, missed deadlines and cost.\n"
            "40 development episodes; 30 held-out; 300 runs.",
            "#e5effb",
            size=12,
        )
        box(
            1,
            4,
            98,
            9,
            "OFFLINE ONLY — no policy access to private data or oracle answers",
            "Certified visible-state MILP labels train C/D on development data; inference never calls the solver.\n"
            "Private realized carbon and full-episode hindsight bounds support scoring after decisions.\n"
            "Freeze before held-out runs. Independent blinded Matty/Nisha annotation remains required.",
            "#f0f2f5",
            size=12,
        )
        text(
            1,
            2.4,
            "24 decision + 6 completion slots; no completion-slot model calls. Q01–Q13 stay open where unresolved.\n"
            "Earlier “Model D” names the agent; random_forest_d is a separate system. Components are not yet implemented.",
            10.5,
        )
        destination = ROOT / "architecture"
        destination.mkdir(exist_ok=True)
        fig.savefig(destination / "architecture.svg", metadata={"Date": None})
        svg_path = destination / "architecture.svg"
        svg = svg_path.read_text(encoding="utf-8")
        svg = svg.replace(
            " <metadata>",
            " <title>Ontology-grounded, tool-verified agent versus plain LLM: planned architecture</title>\n"
            " <desc>The main comparison tests accuracy, faithfulness and safety in workload scheduling. "
            "Four additional scheduling references share visible inputs and an execution gate; "
            "private data and offline references stay outside policy inputs.</desc>\n <metadata>",
            1,
        )
        svg_path.write_text(
            "\n".join(line.rstrip() for line in svg.splitlines()) + "\n", encoding="utf-8"
        )
        fig.savefig(destination / "architecture.png", dpi=160)
        print("Generated final-proposal architecture.svg and architecture.png")


if __name__ == "__main__":
    main()
