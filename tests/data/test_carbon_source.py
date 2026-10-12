"""Offline D01 tests use generated synthetic CSVs, never redistributed source data."""

import csv
import hashlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from dc_sustainability.data.carbon_source import (
    COLUMNS,
    HOUR,
    SOURCE_URL,
    START,
    episode_indices,
    inspect_csv,
    load_source,
    main,
    provenance,
    retrieve_source,
)


def synthetic_csv(change=None, header=COLUMNS):
    rows = [[(START + i * HOUR).isoformat(), *(["1"] * 8), "500"] for i in range(8760)]
    if change:
        change(rows)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode()


class CarbonSourceTests(unittest.TestCase):
    def inspect(self, payload):
        return inspect_csv(payload, require_pinned=False)

    def test_complete_year_and_repeatable_checksum(self):
        payload = synthetic_csv()
        report = self.inspect(payload)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["row_count"], 8760)
        self.assertEqual(report["avg_CI_mean"], 500)
        self.assertEqual(report["first_timestamp_utc"], "2022-01-01T00:00:00+00:00")
        self.assertEqual(report["last_timestamp_utc"], "2022-12-31T23:00:00+00:00")
        self.assertEqual(report, self.inspect(payload))

    def test_pinned_check_rejects_synthetic_and_local_loader(self):
        payload = synthetic_csv()
        self.assertIn("checksum", inspect_csv(payload)["errors"][0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            path.write_bytes(payload)
            with self.assertRaises(ValueError):
                load_source(path)
            with self.assertRaises(FileNotFoundError):
                load_source(path.with_name("missing.csv"))

    def test_valid_loader_preserves_utc_and_values(self):
        payload = synthetic_csv()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            path.write_bytes(payload)
            with patch(
                "dc_sustainability.data.carbon_source.SHA256", hashlib.sha256(payload).hexdigest()
            ):
                observations, report = load_source(path)
            self.assertEqual(observations[0], (START, 500.0))
            self.assertEqual(len(observations), 8760)
            self.assertEqual(report["errors"], [])

    def test_cli_reports_failed_validation_and_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            report = Path(directory) / "report.json"
            source.write_bytes(b"bad")
            with patch("sys.argv", ["carbon_source", str(source), "--report", str(report)]):
                self.assertEqual(main(), 1)
                before = report.read_bytes()
                with self.assertRaises(FileExistsError):
                    main()
            self.assertEqual(report.read_bytes(), before)

    def test_missing_and_extra_records(self):
        for change in (lambda r: r.pop(), lambda r: r.append(r[-1])):
            with self.subTest(change=change):
                self.assertTrue(
                    any("8760" in e for e in self.inspect(synthetic_csv(change))["errors"])
                )

    def test_missing_or_duplicate_columns_and_bad_csv(self):
        for header in (COLUMNS[:-1], (*COLUMNS[:-1], "timestamp")):
            self.assertTrue(self.inspect(synthetic_csv(header=header))["errors"])
        for payload in (b"", b"\xff", b'"unclosed'):
            self.assertTrue(self.inspect(payload)["errors"])

    def test_missing_nonfinite_negative_and_outlier_numbers(self):
        for column in (1, 9):
            for value in ("", "nan", "inf", "-1", "nonsense"):
                with self.subTest(column=column, value=value):
                    payload = synthetic_csv(lambda r: r[4].__setitem__(column, value))
                    self.assertTrue(self.inspect(payload)["errors"])
        payload = synthetic_csv(lambda r: r[4].__setitem__(9, "2001"))
        self.assertTrue(any("screening" in e for e in self.inspect(payload)["errors"]))

    def test_timestamp_duplicate_gap_disorder_and_timezone(self):
        for value in (
            "2022-01-01T03:00:00+00:00",
            "2022-01-01T06:00:00+00:00",
            "2022-01-01T04:30:00+00:00",
            "2022-01-01T04:00:00",
            "2022-01-01T04:00:00-07:00",
            "invalid",
            "2023-01-01T04:00:00+00:00",
        ):
            with self.subTest(value=value):
                payload = synthetic_csv(lambda r: r[4].__setitem__(0, value))
                self.assertTrue(self.inspect(payload)["errors"])
        payload = synthetic_csv(lambda r: r[4].__setitem__(0, r[3][0]))
        self.assertTrue(any("duplicate" in e for e in self.inspect(payload)["errors"]))

    def test_bad_row_width(self):
        for change in (lambda r: r[4].pop(), lambda r: r[4].append("extra")):
            self.assertTrue(
                any("field count" in e for e in self.inspect(synthetic_csv(change))["errors"])
            )

    def test_episode_mapping_requires_explicit_convention_and_never_wraps(self):
        indices = episode_indices(date(2022, 1, 1), interval_convention="start")
        self.assertEqual(indices, tuple(range(7, 37)))
        for day in (date(2021, 12, 31), date(2022, 12, 31), date(2023, 1, 1)):
            with self.assertRaises(ValueError):
                episode_indices(day, interval_convention="start")
        with self.assertRaises(ValueError):
            episode_indices(date(2022, 1, 1), interval_convention="end")

    def test_provenance_does_not_claim_acceptance_or_known_acquisition(self):
        report = provenance(self.inspect(synthetic_csv()), acquisition_time_utc=None)
        self.assertIsNone(report["acquisition_time_utc"])
        self.assertIsNone(report["pollutant_basis"])
        self.assertIsNone(report["source_interval_convention"])
        self.assertFalse(report["acceptance_complete"])
        self.assertTrue(report["blockers"])

    def test_download_is_pinned_validates_before_write_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            with patch("urllib.request.urlopen") as request:
                request.return_value.__enter__.return_value.read.return_value = synthetic_csv()
                with self.assertRaises(ValueError):
                    retrieve_source(path)
                request.assert_called_once_with(SOURCE_URL, timeout=60)
                self.assertFalse(path.exists())
            path.write_bytes(b"preserve")
            with (
                patch("urllib.request.urlopen") as request,
                patch(
                    "dc_sustainability.data.carbon_source.inspect_csv", return_value={"errors": []}
                ),
            ):
                request.return_value.__enter__.return_value.read.return_value = b"new"
                with self.assertRaises(FileExistsError):
                    retrieve_source(path)
            self.assertEqual(path.read_bytes(), b"preserve")


if __name__ == "__main__":
    unittest.main()
