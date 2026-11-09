"""Check request-local Claim schemas against the pinned runtime's grammar converter.

Offline only: builds the Agent and Plain request schemas, converts them with a
compiled ``a01_claim_grammar_probe`` (llama.cpp b11669, the converter bundled by
Ollama 0.40.5) and records which synthetic strings the grammar accepts.  It makes no
model request, starts no runtime and reads no saved output.  Converter acceptance is
not evidence of model behaviour, timing or token counts.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.llm.response_bounds import bounded_response_schema  # noqa: E402
from tests.contracts import fixtures as f  # noqa: E402

OLLAMA_TAG = ("v0.40.5", "d919272e53593d1d55d40e1180eaa06dfbede3ac")
LLAMA_CPP_TAG = ("b11669", "620d2225cc436ab0b001e3200e590e3b286ef9ab")
CONVERTER_FILES = (
    "common/json-schema.cpp",
    "common/json-schema-to-grammar.cpp",
    "tools/server/server-schema.cpp",
)
EXPECTED_CONVERTER_SHA256 = {
    "common/json-schema.cpp": "68ba2adbb6e0578c0d89e99cc9a9a7aa9c0b554b555bcd3908da71789045509d",
    "common/json-schema-to-grammar.cpp": "d5a82fff5d611abd1198ff27c328b20376ffe9f110b4771d579c8bd20c70541f",
    "tools/server/server-schema.cpp": "1f9d7b73b4363b90b08de0360b0a5ce0b3d152750bfb8d587a367e90c7904050",
}
MISSING = object()
EVIDENCE = ["FACT-CI-s03"]


def _claim(cid="C1", evidence=EVIDENCE, value=MISSING, unit=MISSING, **extra):
    record = {"claim_id": cid, "text": "Slot 3 is forecast at 250 g/kWh."}
    for key, item in (("evidence_ids", evidence), ("value", value), ("unit", unit)):
        if item is not MISSING:
            record[key] = item
    record.update(extra)
    return record


# name, claims, expected grammar verdict for the paired request schema
CASES = (
    ("observed_null_value_with_g_per_kwh", [_claim(value=None, unit="g/kWh")], False),
    ("observed_null_value_with_slot", [_claim(value=None, unit="slot")], False),
    ("omitted_value_with_unit", [_claim(unit="slot")], False),
    ("number_with_null_unit", [_claim(value=250.0, unit=None)], False),
    ("number_with_omitted_unit", [_claim(value=250.0)], False),
    ("number_and_unit", [_claim(value=250.0, unit="g/kWh")], True),
    ("zero_and_unit", [_claim(evidence=[], value=0, unit="kg")], True),
    ("negative_and_unit", [_claim(evidence=[], value=-8.5, unit="kg")], True),
    ("both_null", [_claim(evidence=[], value=None, unit=None)], True),
    ("both_null_with_evidence", [_claim(value=None, unit=None)], True),
    ("both_omitted_explicit_keys_required", [_claim(evidence=[])], False),
    ("numeric_without_evidence_key", [_claim(evidence=MISSING, value=1.0, unit="kg")], False),
    ("boolean_value", [_claim(evidence=[], value=True, unit="kg")], False),
    ("string_value", [_claim(evidence=[], value="250", unit="g/kWh")], False),
    ("unsupported_unit", [_claim(evidence=[], value=250.0, unit="MWh")], False),
    ("no_claims", [], True),
    (
        "four_mixed_claims",
        [
            _claim("C1", value=22.0, unit="kg"),
            _claim("C2", evidence=[], value=None, unit=None),
            _claim("C3", value=None, unit=None),
            _claim("C4", evidence=[], value=4, unit="slot"),
        ],
        True,
    ),
    (
        "five_claims_over_limit",
        [_claim(f"C{i}", evidence=[], value=None, unit=None) for i in range(1, 6)],
        False,
    ),
    ("unknown_evidence_id", [_claim(evidence=["FACT-CI-s99"], value=1.0, unit="kg")], False),
    (
        "three_evidence_ids",
        [_claim(evidence=["FACT-CI-s01", "FACT-CI-s02", "FACT-CI-s03"], value=1.0, unit="kg")],
        False,
    ),
    ("text_at_limit", [_claim(evidence=[], value=None, unit=None, text="x" * 256)], True),
    ("text_over_limit", [_claim(evidence=[], value=None, unit=None, text="x" * 257)], False),
    ("extra_key", [_claim(evidence=[], value=None, unit=None, note="x")], False),
)

# Keywords the converter does not read: a coupled rule written with them is ignored.
CONTROL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "unit": {"anyOf": [{"enum": ["kg", "slot"], "type": "string"}, {"type": "null"}]},
    },
    "required": ["value", "unit"],
    "if": {"properties": {"value": {"type": "null"}}},
    "then": {"properties": {"unit": {"type": "null"}}},
    "dependentRequired": {"unit": ["value"]},
    "not": {"properties": {"value": {"type": "null"}, "unit": {"type": "string"}}},
}
CONTROL_CASES = (
    ("null_value_with_unit", {"value": None, "unit": "kg"}),
    ("number_with_null_unit", {"value": 1, "unit": None}),
)


def _resolve(node, root):
    while "$ref" in node:
        node = root["$defs"][node["$ref"].rsplit("/", 1)[-1]]
    branches = [b for b in node.get("anyOf", ()) if "properties" in b or "$ref" in b]
    return _resolve(branches[0], root) if branches else node


def _ordered(value, node, root):
    """Serialize in the converter's order: required keys, then optional keys."""
    node = _resolve(node, root)
    if isinstance(value, dict) and "properties" in node:
        props, required = node["properties"], node.get("required", [])
        keys = [k for k in props if k in required] + [k for k in props if k not in required]
        keys = [k for k in keys if k in value] + [k for k in value if k not in props]
        return {k: _ordered(value[k], props.get(k, {}), root) for k in keys}
    if isinstance(value, list) and "items" in node:
        return [_ordered(item, node["items"], root) for item in value]
    return value


def _probe(binary, schema, cases):
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        (folder / "schema.json").write_text(json.dumps(schema), encoding="utf-8")
        lines = [name + "\t" + json.dumps(doc, separators=(",", ":")) for name, doc in cases]
        (folder / "cases.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                str(binary),
                str(folder / "schema.json"),
                str(folder / "cases.tsv"),
                str(folder / "g"),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        grammar = (folder / "g").read_bytes()
    verdicts = dict(line.split("\t") for line in result.stdout.strip().splitlines())
    return {name: verdicts[name] == "ACCEPT" for name, _ in cases}, grammar


def _documents(model, state, schema):
    plan = {
        "schema_version": s.SCHEMA_VERSION,
        "record_type": "Plan",
        "episode_id": state.episode_id,
        "slot": state.current_slot,
        "state_version": state.state_version,
        "starts": [],
        "deferrals": [],
        "abstentions": [],
        "status": "proposed",
    }
    for name, claims, _ in CASES:
        explanation = {"source": "llm", "summary": "Start J1 at slot 2.", "claims": claims}
        doc = explanation
        if model is s.PolicyOutput:
            doc = {
                "schema_version": s.SCHEMA_VERSION,
                "record_type": "PolicyOutput",
                "system": "plain_llm",
                "output_status": "ok",
                "plan": plan,
                "explanation": explanation,
            }
        yield name, _ordered(doc, schema, schema)


def assess(binary, llama_cpp):
    source = {
        name: hashlib.sha256((llama_cpp / name).read_bytes()).hexdigest()
        for name in CONVERTER_FILES
    }
    if source != EXPECTED_CONVERTER_SHA256:
        raise ValueError("converter source differs from the pinned b11669 files")
    binary_sha256 = hashlib.sha256(binary.read_bytes()).hexdigest()
    state = f.visible_state()
    expected = {name: verdict for name, _, verdict in CASES}
    runs = []
    for profile in (96, 256):
        for model, system in ((s.Explanation, "agent"), (s.PolicyOutput, "plain_llm")):
            schema, _ = bounded_response_schema(
                model, state, system=system, explanation_characters=profile
            )
            cases = list(_documents(model, state, schema))
            if profile == 96:
                cases = [(n, d) for n, d in cases if not n.startswith("text_")]
            verdicts, grammar = _probe(binary, schema, cases)
            mismatches = sorted(n for n, ok in verdicts.items() if ok is not expected[n])
            runs.append(
                {
                    "system": system,
                    "response_model": model.__name__,
                    "explanation_characters": profile,
                    "request_schema_sha256": s.sha256_hex(schema),
                    "grammar_sha256": hashlib.sha256(grammar).hexdigest(),
                    "accepted": verdicts,
                    "mismatches_with_expected": mismatches,
                }
            )
    control, _ = _probe(binary, CONTROL_SCHEMA, CONTROL_CASES)
    return {
        "scope": "offline converter check of request-local Claim schemas; synthetic strings",
        "runtime_converter": {
            "ollama_tag": OLLAMA_TAG[0],
            "ollama_commit": OLLAMA_TAG[1],
            "llama_cpp_tag": LLAMA_CPP_TAG[0],
            "llama_cpp_commit": LLAMA_CPP_TAG[1],
            "converter_source_sha256": source,
            "probe_source_sha256": hashlib.sha256(
                (ROOT / "scripts/a01_claim_grammar_probe.cpp").read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest(),
            "probe_source_hash_convention": "LF-normalized",
        },
        "expected_accepted": expected,
        "runs": runs,
        "ignored_keyword_control": {
            "keywords": ["if", "then", "dependentRequired", "not"],
            "accepted": control,
            "meaning": "accepted one-sided pairs show these keywords add no grammar constraint",
        },
        "probe_binary_sha256": binary_sha256,
        "source_verification": "three converter files match pinned upstream bytes",
        "binary_build_binding": "caller-supplied binary; build/source binding not independently attested",
        "model_calls": 0,
        "runtime_started": False,
        "limitations": [
            "Synthetic strings only; no model output or sampling behaviour is observed.",
            "The probe uses the converter source, not the installed Windows binary.",
            "Native grammar, prompt counts, timing and cleanup need an authorized run.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True, help="compiled probe binary")
    parser.add_argument("--llama-cpp", type=Path, required=True, help="b11669 source tree")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = assess(args.probe, args.llama_cpp)
    failed = [run for run in result["runs"] if run["mismatches_with_expected"]]
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print("runs:", len(result["runs"]), "with mismatches:", len(failed))
    print("ignored-keyword control:", result["ignored_keyword_control"]["accepted"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
