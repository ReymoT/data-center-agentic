"""Rule §11.8 calibration packet: generated files, separation and a compare run.

The extraction here is synthetic test data, not an answer key for the packet.
"""

import json

from dc_sustainability.evaluation import agreement as g
from dc_sustainability.evaluation import review as rv
from scripts import build_e04_calibration as build
from scripts import build_e04_cases as dev

CAL = build.OUT


def committed(name):
    return (CAL / name).read_text(encoding="utf-8")


def cases():
    return rv.load_cases(json.loads(committed("calibration_cases.json")))


def test_committed_files_match_the_generator():
    for name, text in build.build().items():
        assert committed(name) == text, f"{name} is stale; run scripts/build_e04_calibration.py"


def test_two_practice_outputs_apart_from_the_development_cases():
    [case] = cases()
    assert case.case_id == "CAL01" and len(case.outputs) == 2
    development = json.loads(dev.build()["development_cases.json"])["cases"]
    assert case.case_id not in {c["case_id"] for c in development}
    dev_outputs = [o for c in development for o in c["outputs"].values()]
    for output in json.loads(committed("calibration_cases.json"))["cases"][0]["outputs"].values():
        assert output not in dev_outputs


def test_packet_covers_summary_limitation_and_raw_text_extraction():
    [case] = cases()
    kinds = {
        k: (o.explanation is not None, o.raw_response is not None) for k, o in case.outputs.items()
    }
    assert sorted(kinds.values()) == [(False, True), (True, False)]
    structured = next(o for o in case.outputs.values() if o.explanation)
    assert len(structured.explanation.summary.split(". ")) >= 4  # several sentences to split
    assert len(structured.explanation.limitations) == 2


def test_rater_material_does_not_reveal_the_design():
    text = committed("CALIBRATION_PACKET.md").lower()
    for word in ("design", "agent", "plain", "intended", "false", "correct"):
        assert word not in text, word
    assert "extracts independently" in committed("CALIBRATION_PACKET.md")


def test_template_starts_empty_and_calibration_ratings_compare(tmp_path):
    [case] = cases()
    template = json.loads(committed("annotation_template.json"))
    assert all(a["label"] is None for o in template["outputs"] for a in o["assertions"])

    def rated(rater, raw_ids, summary_ids):
        data = json.loads(committed("annotation_template.json"))
        data["rater"] = rater
        for entry in data["outputs"]:
            output = case.outputs[entry["output"]]
            entry["completeness"] = dict.fromkeys(rv.COMPLETENESS, 1 if output.explanation else 0)
            for a in entry["assertions"]:
                a.update(label="supported", supporting_cited_ids=[], restated_in_summary=False)
            source, ids = ("summary", summary_ids) if output.explanation else ("raw", raw_ids)
            entry["assertions"] += [
                {
                    "assertion_id": i,
                    "source": source,
                    "text": "synthetic test text",
                    "label": "supported",
                    "cited_ids": [],
                    "supporting_cited_ids": [],
                    "reference_kind": "power_load_capacity",
                }
                for i in ids
            ]
        return g.load_original(json.dumps(data).encode("utf-8"), cases())

    raw_key = next(k for k, o in case.outputs.items() if o.raw_response)
    text_key = next(k for k, o in case.outputs.items() if o.explanation)
    a, b = rated("A", ["R1", "R2"], ["S1"]), rated("B", ["R1"], ["S1", "S2"])
    matches = {("CAL01", raw_key): [("R1", "R1")], ("CAL01", text_key): [("S1", "S1")]}
    report = g.summary(g.compare(a, b, matches))
    assert report["raw_text"]["extraction"] == {
        "both": 1,
        "only_a": 1,
        "only_b": 0,
        "agreement": 0.5,
    }
    assert report["extraction"]["agreement"] == 0.5
    assert report["reference_kind"]["n"] == 2
