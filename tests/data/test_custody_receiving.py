"""Independent rank/window check on synthetic receipt only; no actual cohort."""

import hashlib
import json
from datetime import datetime, timedelta, timezone

from dc_sustainability.data import held_out_custody as custody
from dc_sustainability.data import materialize_development as development
from dc_sustainability.data import splits
from tests.data.test_held_out_custody import authorization  # noqa: F401


def test_independent_synthetic_selection_and_physical_isolation(authorization):  # noqa: F811
    parameters = authorization["parameters"]
    dev, _ = development.allocation()

    def hours(day):
        start = datetime.fromisoformat(day).replace(hour=7, tzinfo=timezone.utc)
        return {start + timedelta(hours=i) for i in range(30)}

    occupied = set().union(*(hours(r["window"]["date"]) for r in dev["records"]))

    def rank(day):
        payload = json.dumps(
            [custody.VERSION, parameters["selection_seed"], day],
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        return hashlib.sha256(payload).hexdigest(), day

    chosen = []
    for day in sorted(parameters["candidate_dates"], key=rank):
        if day[5:7] in {d[5:7] for d in chosen} or occupied & hours(day):
            continue
        chosen.append(day)
        occupied |= hours(day)
        if len(chosen) == 6:
            break
    result = custody.build_metadata(
        authorization, authorization_sha256=splits.digest(authorization), revision="a" * 40
    )
    held = [r for r in result["records"] if r["partition"] == "held_out"]
    assert sorted(chosen) == sorted({r["window"]["date"] for r in held})
    assert len(held) == 30
    assert result["scientific_acceptance"] is False
    assert result["held_out_contents_generated"] is False
