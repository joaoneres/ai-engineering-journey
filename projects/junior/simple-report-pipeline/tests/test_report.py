import json
import tempfile
import unittest
from pathlib import Path

from simple_report_pipeline.report import ReportError, build_summary, is_valid_pickup, load_pickups

VALID = {
    "id": 1,
    "customer_name": "Ana",
    "address": "Rua A",
    "package_count": 3,
    "priority": "high",
    "status": "pending",
}


class ReportTests(unittest.TestCase):
    def write(self, content: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [f.unlink() for f in directory.iterdir()] or directory.rmdir())
        path = directory / "pickups.json"
        path.write_text(content, encoding="utf-8")
        return path

    def test_summary_counts_and_includes_empty_categories(self):
        other = {**VALID, "id": 2, "package_count": 4, "priority": "low", "status": "completed"}
        summary = build_summary([VALID, other])
        self.assertEqual(summary["total_pickups"], 2)
        self.assertEqual(summary["total_packages"], 7)
        self.assertEqual(summary["by_priority"], {"high": 1, "medium": 0, "low": 1})
        self.assertEqual(summary["by_status"], {"pending": 1, "in_transit": 0, "completed": 1})

    def test_empty_list_gives_zeroes(self):
        self.assertEqual(build_summary([])["total_packages"], 0)

    def test_invalid_records_are_rejected(self):
        self.assertFalse(is_valid_pickup({**VALID, "package_count": 0}))
        self.assertFalse(is_valid_pickup({**VALID, "package_count": True}))
        self.assertFalse(is_valid_pickup({**VALID, "status": "lost"}))
        self.assertFalse(is_valid_pickup("nope"))

    def test_load_reads_valid_file(self):
        self.assertEqual(load_pickups(self.write(json.dumps([VALID]))), [VALID])

    def test_load_rejects_missing_file_bad_json_and_bad_records(self):
        with self.assertRaises(ReportError):
            load_pickups(Path("does-not-exist.json"))
        with self.assertRaises(ReportError):
            load_pickups(self.write("{ not json"))
        with self.assertRaises(ReportError):
            load_pickups(self.write(json.dumps([{"id": 1}])))


if __name__ == "__main__":
    unittest.main()
