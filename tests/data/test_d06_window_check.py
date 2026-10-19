"""Offline tests for the D06 checker, using tiny synthetic CSVs, not source data."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

CHECKER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "d06_check_window.py"
_SPEC = importlib.util.spec_from_file_location("d06_check_window", CHECKER_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"could not load checker from {CHECKER_PATH}")
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)


def _csv(hours: int, *, skip: int | None = None, negative: bool = False) -> str:
    start = datetime(2022, 1, 1, tzinfo=timezone.utc)
    lines = [",".join(checker.HEADER)]
    for hour in range(hours):
        if hour == skip:
            continue
        avg_ci = -1.0 if negative and hour == 3 else 500.0 + hour
        row = [
            (start + timedelta(hours=hour)).isoformat(),
            *["1.0"] * 8,
            repr(avg_ci),
        ]
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


def _passing_result() -> dict:
    """A minimal successful result used to test the pass/fail gate independently."""
    return {
        "problems": [],
        "sha256_matches_reference": True,
        "blob_matches_reference": True,
        "year": {
            "rows": 8760,
            "valid_timestamp_rows": 8760,
            "first": "2022-01-01T00:00:00+00:00",
            "last": "2022-12-31T23:00:00+00:00",
            "duplicates": 0,
            "non_hourly_steps": 0,
        },
        "window": {
            "rows": 24,
            "contiguous_hourly": True,
            "expected_hours_present": True,
        },
        "reference_comparison": {
            "year_exact_equal": {key: True for key in checker.REF_YEAR},
            "jan1_exact_equal": {key: True for key in checker.REF_JAN1},
        },
    }


class WindowCheckTests(unittest.TestCase):
    def run_check(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.csv"
            path.write_text(text, encoding="utf-8")
            return checker.check(path, "2022-01-01")

    def run_cli(self, text: str) -> tuple[int, str, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "synthetic.csv"
            report_path = root / "report.json"
            csv_path.write_text(text, encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "d06_check_window.py",
                str(csv_path),
                "--day",
                "2022-01-01",
                "--report",
                str(report_path),
            ]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
                exit_code = checker.main()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            return exit_code, stdout.getvalue(), report

    def test_clean_window(self):
        result = self.run_check(_csv(30))
        self.assertEqual(result["window"]["rows"], 24)
        self.assertTrue(result["window"]["expected_hours_present"])
        self.assertEqual(
            (result["window"]["first"], result["window"]["last"]),
            (500.0, 523.0),
        )
        self.assertEqual(result["year"]["non_hourly_steps"], 0)
        self.assertFalse(result["sha256_matches_reference"])  # synthetic != pinned source

    def test_gap_is_reported_not_filled(self):
        result = self.run_check(_csv(30, skip=5))
        self.assertEqual(result["window"]["rows"], 23)
        self.assertFalse(result["window"]["expected_hours_present"])
        self.assertEqual(result["year"]["non_hourly_steps"], 1)

    def test_negative_value_is_reported(self):
        result = self.run_check(_csv(30, negative=True))
        self.assertTrue(
            any("not finite and nonnegative" in problem for problem in result["problems"])
        )

    def test_requested_adapter_mismatch_makes_result_fail(self):
        result = _passing_result()
        result["adapter_comparison"] = {
            "adapter_rows": 8760,
            "window_values_identical": False,
        }
        self.assertFalse(
            checker.result_passes(result, compare_adapter_requested=True)
        )

    def test_requested_adapter_comparison_missing_makes_result_fail(self):
        result = _passing_result()
        self.assertFalse(
            checker.result_passes(result, compare_adapter_requested=True)
        )

    def test_adapter_mismatch_does_not_fail_when_comparison_not_requested(self):
        result = _passing_result()
        result["adapter_comparison"] = {
            "adapter_rows": 8760,
            "window_values_identical": False,
        }
        self.assertTrue(checker.result_passes(result, compare_adapter_requested=False))

    def test_malformed_timestamp_produces_clean_cli_failure(self):
        lines = _csv(30).splitlines()
        cells = lines[1].split(",")
        cells[0] = "not-a-timestamp"
        lines[1] = ",".join(cells)
        exit_code, output, report = self.run_cli("\n".join(lines) + "\n")
        self.assertEqual(exit_code, 1)
        self.assertIn("RESULT: FAIL", output)
        self.assertTrue(any("malformed timestamp" in problem for problem in report["problems"]))

    def test_nonnumeric_cell_produces_clean_cli_failure(self):
        lines = _csv(30).splitlines()
        cells = lines[1].split(",")
        cells[1] = "not-a-number"
        lines[1] = ",".join(cells)
        exit_code, output, report = self.run_cli("\n".join(lines) + "\n")
        self.assertEqual(exit_code, 1)
        self.assertIn("RESULT: FAIL", output)
        self.assertTrue(any("is not numeric" in problem for problem in report["problems"]))

    def test_invalid_day_produces_clean_cli_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "synthetic.csv"
            report_path = root / "report.json"
            csv_path.write_text(_csv(30), encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "d06_check_window.py",
                str(csv_path),
                "--day",
                "not-a-date",
                "--report",
                str(report_path),
            ]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
                exit_code = checker.main()
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 1)
        self.assertIn("RESULT: FAIL", stdout.getvalue())
        self.assertTrue(any("invalid --day value" in problem for problem in report["problems"]))


if __name__ == "__main__":
    unittest.main()