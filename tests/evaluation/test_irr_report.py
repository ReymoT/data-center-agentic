"""The rendered reliability numbers reproduce the hand-written development report."""

import copy
import json
import subprocess
import sys
from pathlib import Path

from dc_sustainability.evaluation import agreement as g
from dc_sustainability.evaluation import irr_report
from tests.evaluation.test_calibration import CAL, cases

ROOT = Path(__file__).resolve().parents[2]
AGREEMENT = ROOT / "docs/e04/ratings/agreement"
ORIGINALS = ("../originals/E05_Nisha_2026-10-26.json", "../originals/E05_Matty_2026-10-22.json")


def development():
    report = json.loads((AGREEMENT / "agreement_report.json").read_text(encoding="utf-8"))
    return irr_report.render(
        report,
        title="Development",
        scope="the 11 synthetic E04 development cases",
        originals=ORIGINALS,
        artifact_dir=AGREEMENT,
    )


def test_development_numbers_match_the_published_report():
    text = development()
    published = (AGREEMENT / "E05_DEVELOPMENT_IRR.md").read_text(encoding="utf-8")
    # Rows rendered in the same format as the hand-written report must be identical.
    identical = [
        line
        for line in text.splitlines()
        if line.startswith(("| a:", "| b:", "| supported", "| contradicted", "| unsupported"))
        or line.startswith(("| Output units", "| Reviewed", "| Missing", "| Assertions"))
    ]
    assert len(identical) == 12  # inputs 2, denominators 4, marginals 3, confusion 3
    for line in identical:
        assert line in published, line
    for fragment in (
        "0 matched, 0 only a, 64 only b, **agreement 0.00**",
        "**raw agreement 75.0%**, **Cohen's kappa 0.00**",
        "| decision | 20/20 | 100.0% | 1.00 |",
        "| reason | 18/20 | 90.0% | 0.44 |",
        "| evidence | 18/20 | 90.0% | 0.46 |",
        "| limitations | 19/20 | 95.0% | 0.90 |",
        "Rater a (Nisha) used only `supported` for all 32 pairs",
    ):
        assert fragment in text
    # Artifact hashes recomputed from the files equal the published ones.
    for name in irr_report.ARTIFACTS:
        digest = irr_report.sha256_lf(AGREEMENT / name)
        assert f"`{name}` | `{digest}`" in text
        assert digest in published
    # Claims-only block is identical here, so it is not repeated.
    assert "claim records only" not in text


def _block(n, agreed, kappa, a, b):
    return {
        "n": n,
        "agreed": agreed,
        "percent": 100 * agreed / n if n else None,
        "kappa": kappa,
        "marginals": {"a": a, "b": b},
    }


def test_kappa_notes_explain_undefined_and_one_label_cases():
    zero = dict.fromkeys(irr_report.LABELS, 0)
    raters = ("A", "B")
    assert irr_report.kappa_notes(_block(0, 0, None, zero, zero), raters) == [
        "Kappa is undefined: there are no matched pairs."
    ]
    same = {**zero, "supported": 5}
    (note,) = irr_report.kappa_notes(_block(5, 5, None, same, same), raters)
    assert note.startswith("Kappa is undefined") and "chance-expected agreement is 1" in note
    mixed = {**zero, "supported": 3, "unsupported": 2}
    (note,) = irr_report.kappa_notes(_block(5, 3, 0.0, mixed, same), raters)
    assert note.startswith("Rater b (B) used only `supported` for all 5 pairs")
    assert irr_report.kappa_notes(_block(5, 4, 0.5, mixed, mixed), raters) == []


def test_draft1_sections_render_only_when_present():
    a = g.load_original((CAL / "ratings/E04_Nisha_original_2026-10-31.json").read_bytes(), cases())
    b = g.load_original(
        (CAL / "ratings/E04_Matty_normalized_2026-10-31.json").read_bytes(), cases()
    )
    report = g.summary(g.compare(a, b, {}))
    text = irr_report.render(report, title="T", scope="S", originals=("a.json", "b.json"))
    assert "### Raw-text assertions" in text and "### Reference kind" in text
    assert "Both recorded a kind on 0 matched assertions" in text
    assert "rule §11.9" not in text and "## Artifacts" not in text
    capped = copy.deepcopy(report)
    capped["cap_review"] = {
        "cap_hits": 4,
        "unfinished": {"a": 1, "b": 2},
        "agreement": {"n": 4, "agreed": 3, "percent": 75.0, "kappa": 0.5},
    }
    text = irr_report.render(capped, title="T", scope="S", originals=("a.json", "b.json"))
    assert "Computed cap hits: 4. Marked unfinished: a 1, b 2." in text
    assert "| unfinished | 3/4 | 75.0% | 0.50 |" in text


def test_cli_writes_the_report(tmp_path):
    out = tmp_path / "irr.md"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/render_irr_report.py"),
            "--report",
            str(AGREEMENT / "agreement_report.json"),
            "--a-original",
            ORIGINALS[0],
            "--b-original",
            ORIGINALS[1],
            "--scope",
            "the 11 synthetic E04 development cases",
            "--title",
            "Development",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    assert out.read_text(encoding="utf-8") == development()
