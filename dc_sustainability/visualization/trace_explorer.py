"""Build a standalone read-only HTML explorer; no runner/provider imports or calls."""

import hashlib
import json
from pathlib import Path

from dc_sustainability import schemas as s

TEMPLATE = Path(__file__).resolve().parents[2] / "ui/trace_explorer.html"


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_unit(directory: Path) -> dict:
    """Validate complete saved EP-HAND1 units and project an explicit field allowlist."""
    directory = Path(directory)
    result = s.EpisodeResult.from_json((directory / "result.json").read_text(encoding="utf-8"))
    if result.episode_id != "EP-HAND1":
        raise ValueError("only the public EP-HAND1 development fixture is allowed")
    records = []
    for path in sorted((directory / "traces").glob("*.json")):
        record = s.DecisionRecord.from_json(path.read_text(encoding="utf-8"))
        if (record.run_id, record.episode_id, record.system, record.trial) != (
            result.run_id,
            result.episode_id,
            result.system,
            result.trial,
        ):
            raise ValueError("trace identity differs from result")
        if path.stem != s.sha256_hex(record.decision_id):
            raise ValueError("trace filename differs from decision identity")
        stages = []
        for name in ("initial", "repaired", "fallback"):
            stage = getattr(record, name)
            stages.append(
                {
                    "name": name,
                    "presence": "recorded"
                    if stage
                    else "not applicable"
                    if name in record.not_applicable_stages
                    else "not performed",
                    "plan_hash": stage.plan.plan_hash if stage else None,
                    "starts": [p.to_jsonable() for p in stage.plan.starts] if stage else [],
                    "check": stage.check.status if stage and stage.check else "not checked",
                    "violation_count": len(stage.check.violations)
                    if stage and stage.check
                    else None,
                }
            )
        records.append(
            {
                "decision_id": record.decision_id,
                "slot": record.slot,
                "final_status": record.final_status,
                "model_call_count": record.model_call_count,
                "execution_check": record.execution_check.status
                if record.execution_check
                else "not checked",
                "executed_starts": [p.to_jsonable() for p in record.executed_starts],
                "stages": stages,
                "error_count": len(record.errors),
                "sha256": _digest(path),
                "explanation_present": record.explanation is not None,
            }
        )
    records.sort(key=lambda record: record["slot"])
    if [record["slot"] for record in records] != list(range(30)):
        raise ValueError("exactly one trace for every slot 0-29 is required")
    return {
        "system": result.system,
        "run_id": result.run_id,
        "episode_id": result.episode_id,
        "trial": result.trial,
        "result_sha256": _digest(directory / "result.json"),
        "completed": len(result.completed_job_ids),
        "missed": len(result.deadline_missed_job_ids),
        "unfinished": len(result.unfinished_job_ids),
        "records": records,
    }


def build(unit_directories, output: Path) -> dict:
    units = [project_unit(Path(directory)) for directory in unit_directories]
    keys = [(u["system"], u["run_id"], u["trial"]) for u in units]
    if not units or len(set(keys)) != len(keys):
        raise ValueError("distinct saved units are required")
    payload = {"scope": "public-development-replay-not-study-results", "units": units}
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("{{DATA}}") != 1:
        raise ValueError("explorer template needs exactly one data marker")
    with Path(output).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(template.replace("{{DATA}}", encoded))
    return {
        "units": len(units),
        "traces": sum(len(u["records"]) for u in units),
        "html_sha256": _digest(Path(output)),
        "model_calls": 0,
    }
