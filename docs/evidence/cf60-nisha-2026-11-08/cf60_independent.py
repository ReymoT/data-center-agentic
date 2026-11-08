"""Independent CF60 broker receiving checks. Synthetic values and public development
metadata only; no source CSV, held-out data, selection or model call.

Usage (from the pinned checkout): python cf60_independent.py <harness output json> <report json>
"""

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.data import cf60_broker as b
from dc_sustainability.data import cf60_receiving as rcv
from dc_sustainability.data.materialize_development import allocation

harness_path, report_path = map(Path, sys.argv[1:3])
H = timedelta(hours=1)
O = datetime(2022, 1, 1, tzinfo=timezone.utc)
SRC = s.SourceRef(
    source_id="SRC-SYNTHETIC",
    path="synthetic://nisha-receiving",
    sha256="b" * 64,
    redistribution_status="permitted",
)
results, problems = {}, []


def check(name, condition, detail=""):
    results[name] = bool(condition)
    if not condition:
        problems.append(f"{name}: {detail}")
        print("PROBLEM", name, detail)


def expect_error(name, error, fn):
    try:
        fn()
    except error:
        results[name] = True
        return
    except Exception as other:  # wrong error type is still a finding
        problems.append(f"{name}: raised {type(other).__name__}")
        results[name] = False
        return
    problems.append(f"{name}: no error")
    results[name] = False


# 1. Eligibility: brute force every hourly label against my own reading of the rule.
#    Physical interval [start, start+1h); completion E; availability E+1h strictly
#    before issue; completion age at most four hours.
mismatch = 0
for interp in ("start", "end"):
    for issue_h in range(0, 8760, 7):
        issue = O + issue_h * H
        mine = []
        for back in range(1, 12):
            label = issue - back * H
            start = label if interp == "start" else label - H
            completion = start + H
            if completion + H < issue and issue - completion <= 4 * H:
                mine.append(label)
        if tuple(sorted(mine, reverse=True)) != b.candidates(issue, interp):
            mismatch += 1
check("eligibility_matches_brute_force", mismatch == 0, f"{mismatch} issues differ")


def cap(rows, issue, interp="start", **extra):
    return b.RestrictedHistory(
        rows, issue=issue, interpretation=interp, source=SRC, authorization="synthetic-only", **extra
    )


anchor = O + 2000 * H
issue = anchor + 5 * H
allowed = b.candidates(issue, "start")
rows = [(label, 300.0 + i) for i, label in enumerate(allowed)]

# 2. Public surface: nothing that enumerates or reaches a store.
probe = cap(rows, issue)
public = sorted(n for n in dir(probe) if not n.startswith("_"))
check(
    "public_surface_minimal",
    public == ["authorization", "footprint", "interpretation", "issue", "read", "source"],
    str(public),
)
check("no_instance_dict", not hasattr(probe, "__dict__"))
expect_error("issue_immutable", AttributeError, lambda: setattr(probe, "issue", issue + H))
expect_error("issue_undeletable", AttributeError, lambda: delattr(probe, "source"))

# 3. Construction refuses rows outside the allowlist, duplicates and bad values.
expect_error("extra_row_refused", PermissionError, lambda: cap([*rows, (issue, 1.0)], issue))
expect_error("duplicate_row_refused", ValueError, lambda: cap([rows[0], rows[0]], issue))
for bad in (float("nan"), float("inf"), -1.0, True, "300"):
    expect_error(f"bad_value_{bad!r}", ValueError, lambda bad=bad: cap([(allowed[0], bad)], issue))
expect_error(
    "naive_time_refused", ValueError, lambda: cap([(allowed[0].replace(tzinfo=None), 1.0)], issue)
)
expect_error(
    "subclass_source_refused",
    TypeError,
    lambda: b.RestrictedHistory(
        rows,
        issue=issue,
        interpretation="start",
        source=type("Sub", (s.SourceRef,), {})(**SRC.model_dump()),
        authorization="x",
    ),
)
expect_error("empty_authorization_refused", ValueError, lambda: cap(rows, issue, authorization=" ") if False else b.RestrictedHistory(rows, issue=issue, interpretation="start", source=SRC, authorization=" "))

# 4. Reads: every allowed row returns its value; every other key is denied and logged.
probe = cap(rows, issue)
values = [probe.read(label) for label in allowed]
check("allowed_values_returned", values == [v for _, v in rows])
denied = 0
for h in range(-48, 48):
    label = issue + h * H
    if label in allowed:
        continue
    try:
        probe.read(label)
    except PermissionError:
        denied += 1
check("other_keys_denied", denied == 96 - 3, str(denied))
log = probe.footprint()
check("every_attempt_logged", len(log) == 3 + denied, str(len(log)))
check("denials_logged_as_rejected", sum(e["status"] == "rejected" for e in log) == denied)

# 5. Forecast behavior: latest present candidate wins regardless of value.
for interp in ("start", "end"):
    labels = b.candidates(issue, interp)
    for present in ((0, 1, 2), (1, 2), (2,), ()):
        r = [(labels[i], [900.0, 5.0, 50.0][i]) for i in present]
        out = b.issue_forecast(cap(r, issue, interp), anchor=anchor, slot=5, trusted_issue=issue)
        want = None if not present else dict(r)[labels[min(present)]]
        got = {f.value for f in out.forecasts}
        ok = (got == set()) if want is None else (got == {want})
        check(f"latest_wins_{interp}_{present}", ok, str(got))
        if want is None:
            check(f"missing_slots_{interp}", out.missing_slots == tuple(range(5, 29)))
        else:
            check(
                f"visible_horizon_{interp}_{present}",
                [f.valid_slot for f in out.forecasts] == list(range(5, 29)),
            )
        receipt = json.loads(out.receipt_json)
        check(
            f"receipt_has_no_values_{interp}_{present}",
            "900.0" not in out.receipt_json and "5.0," not in out.receipt_json,
        )
        check(f"receipt_not_adoption_{interp}_{present}", receipt["scientific_adoption"] is False)

# 6. Clock and reuse rules.
fresh = cap(rows, issue)
b.issue_forecast(fresh, anchor=anchor, slot=5, trusted_issue=issue)
expect_error(
    "used_capability_refused",
    ValueError,
    lambda: b.issue_forecast(fresh, anchor=anchor, slot=5, trusted_issue=issue),
)
expect_error(
    "clock_mismatch_refused",
    ValueError,
    lambda: b.issue_forecast(cap(rows, issue), anchor=anchor, slot=4, trusted_issue=issue),
)
expect_error(
    "plain_mapping_refused",
    TypeError,
    lambda: b.issue_forecast(dict(rows), anchor=anchor, slot=5, trusted_issue=issue),
)
expect_error(
    "subclass_capability_refused",
    TypeError,
    lambda: b.issue_forecast(
        type("Sub", (b.RestrictedHistory,), {"__slots__": ()})(
            rows, issue=issue, interpretation="start", source=SRC, authorization="x"
        ),
        anchor=anchor,
        slot=5,
        trusted_issue=issue,
    ),
)

# 7. Fault injection: a reader that leaks denied keys must make the harness fail.
original = b.RestrictedHistory.read


def leaky(self, label):
    try:
        return original(self, label)
    except PermissionError:
        return 1.0


b.RestrictedHistory.read = leaky
try:
    rcv.receive()
    check("harness_catches_leak", False, "harness passed with a leaking reader")
except ValueError as error:
    check("harness_catches_leak", "unauthorized" in str(error), str(error))
finally:
    b.RestrictedHistory.read = original

# 8. Producer harness output versus my run.
harness = json.loads(harness_path.read_text(encoding="utf-8"))
producer = json.loads(Path("docs/evidence/cf60-synthetic-receiving.json").read_text(encoding="utf-8"))
for key in ("broker_code_sha256", "checks_sha256", "development_metadata_sha256"):
    check(f"harness_{key}_matches_producer", harness[key] == producer[key])
check("harness_60_checks", len(harness["checks"]) == 60)
check(
    "harness_rows_and_denials",
    all(c["accessible_rows"] == 3 and c["denied_reads"] == 8757 for c in harness["checks"]),
)

# 9. Development footprints recomputed from the pinned allocation with my own rules.
manifest, _ = allocation()
records = manifest["records"]
check("forty_records", len(records) == 40 and len({r["episode_id"] for r in records}) == 40)
mine = {}
for r in records:
    day = date.fromisoformat(r["window"]["date"])
    a = int((datetime(day.year, day.month, day.day, 7, tzinfo=timezone.utc) - O) / H)
    rec = r["window"]["proposed_physical_indices"]
    reads = {}
    for interp in ("start", "end"):
        labels = set()
        for t in range(30):
            labels |= {int((x - O) / H) for x in b.candidates(O + (a + t) * H, interp)}
        reads[interp] = sorted(labels)
    mine[r["episode_id"]] = {
        "recorded": rec,
        "start_scoring": list(range(a, a + 30)),
        "end_scoring": list(range(a + 1, a + 31)),
        "legacy": [i - 1 for i in rec],
        "start_reads": reads["start"],
        "end_reads": reads["end"],
    }
by_id = {e["episode_id"]: e for e in harness["development_metadata"]}
agree = all(
    by_id[k]["recorded_scoring"] == v["recorded"]
    and by_id[k]["start_scoring"] == v["start_scoring"]
    and by_id[k]["end_scoring"] == v["end_scoring"]
    and by_id[k]["legacy_reads"] == v["legacy"]
    and by_id[k]["start_cf60_reads"] == v["start_reads"]
    and by_id[k]["end_cf60_reads"] == v["end_reads"]
    and by_id[k]["reserved_union"] == sorted(set().union(*map(set, v.values())))
    for k, v in mine.items()
)
check("footprints_match_independent_recompute", agree)
check("recorded_equals_start_hypothesis", all(v["recorded"] == v["start_scoring"] for v in mine.values()))
check("cf60_union_32_rows", all(len(v["start_reads"]) == len(v["end_reads"]) == 32 for v in mine.values()))

# Overlap of reserved development footprints across folds (history/history included).
fold = {r["episode_id"]: r["fold"] for r in records}
union = {k: set().union(*map(set, v.values())) for k, v in mine.items()}
ids = sorted(union)
cross = [
    (x, y)
    for i, x in enumerate(ids)
    for y in ids[i + 1 :]
    if union[x] & union[y] and fold[x] != fold[y]
]
check("no_cross_fold_footprint_overlap", not cross, str(cross[:4]))

report = {
    "commit": "c09167451d66cf51018f8eb30278abd700286f57",
    "checks": results,
    "problems": problems,
    "passed": sum(results.values()),
    "total": len(results),
}
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(report["passed"], "of", report["total"], "checks passed;", len(problems), "problems")
