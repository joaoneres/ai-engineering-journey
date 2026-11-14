import json
import tempfile
import unittest
from pathlib import Path

from simple_manifest_validator.manifest import (
    ManifestError,
    build_report,
    load_manifest,
    validate,
)

VALID = {
    "package": "PKG-1",
    "route": "North",
    "vehicle": "Van 02",
    "responsible": "Ana Souza",
    "status": "pending",
}


class ManifestTests(unittest.TestCase):
    def write(self, name: str, content: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [f.unlink() for f in directory.iterdir()] or directory.rmdir())
        path = directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_reads_json_and_csv(self):
        raw = json.dumps([VALID])
        self.assertEqual(load_manifest(self.write("manifest.json", raw)), [VALID])
        csv_text = (
            "package,route,vehicle,responsible,status\nPKG-1,North,Van 02,Ana Souza,pending\n"
        )
        self.assertEqual(load_manifest(self.write("manifest.csv", csv_text)), [VALID])

    def test_load_strips_csv_header_and_cells(self):
        csv_text = (
            " package , route , vehicle , responsible , status \n"
            " PKG-1 , North , Van 02 , Ana Souza , pending \n"
        )
        self.assertEqual(load_manifest(self.write("manifest.csv", csv_text)), [VALID])

    def test_load_rejects_unusable_files(self):
        with self.assertRaises(ManifestError):
            load_manifest(Path("does-not-exist.json"))
        with self.assertRaises(ManifestError):
            load_manifest(self.write("manifest.json", "{ not json"))
        with self.assertRaises(ManifestError):
            load_manifest(self.write("manifest.json", json.dumps({"package": "PKG-1"})))
        with self.assertRaises(ManifestError):
            load_manifest(self.write("manifest.json", json.dumps(["PKG-1"])))
        with self.assertRaises(ManifestError):
            load_manifest(self.write("manifest.csv", "package,route\nPKG-1,North\n"))
        with self.assertRaises(ManifestError):
            load_manifest(self.write("manifest.csv", ""))
        with self.assertRaises(ManifestError):
            load_manifest(self.write("manifest.txt", "hello"))

    def test_empty_manifest_is_approved(self):
        report = build_report([])
        self.assertEqual(report["total_records"], 0)
        self.assertEqual(report["total_errors"], 0)
        self.assertEqual(report["status"], "approved")

    def test_valid_records_are_approved(self):
        other = {**VALID, "package": "PKG-2"}
        report = build_report([VALID, other])
        self.assertEqual(report["status"], "approved")
        self.assertEqual(report["problems"], [])

    def test_each_broken_field_is_one_problem(self):
        broken = {"package": "  ", "route": "", "vehicle": None, "responsible": 1, "status": "ok"}
        problems = validate([broken])
        self.assertEqual(
            [item["message"] for item in problems],
            [
                "missing package",
                "empty route",
                "missing vehicle",
                "missing responsible",
            ],
        )
        self.assertTrue(all(item["record"] == 1 for item in problems))

    def test_duplicate_package_keeps_the_first_record(self):
        copy = {**VALID, "route": "South"}
        problems = validate([VALID, copy])
        self.assertEqual(problems, [{"record": 2, "message": "duplicate package PKG-1"}])

    def test_blank_packages_are_not_treated_as_duplicates(self):
        blank = {**VALID, "package": ""}
        messages = [item["message"] for item in validate([blank, blank])]
        self.assertEqual(messages, ["missing package", "missing package"])

    def test_rejected_report_counts_every_problem(self):
        report = build_report([{**VALID, "route": "", "vehicle": ""}])
        self.assertEqual(report["total_records"], 1)
        self.assertEqual(report["total_errors"], 2)
        self.assertEqual(report["status"], "rejected")

    def test_non_dict_record_is_invalid(self):
        self.assertEqual(validate(["nope"]), [{"record": 1, "message": "invalid record"}])


if __name__ == "__main__":
    unittest.main()
