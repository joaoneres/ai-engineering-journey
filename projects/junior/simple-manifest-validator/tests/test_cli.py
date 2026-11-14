import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from simple_manifest_validator.cli import main

SAMPLE = Path(__file__).parent.parent / "samples" / "manifest.json"
CSV_SAMPLE = Path(__file__).parent.parent / "samples" / "manifest.csv"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_json_sample_is_approved(self):
        code, out, err = run([str(SAMPLE)])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Records: 2", out)
        self.assertIn("Final status: approved", out)

    def test_csv_sample_is_approved(self):
        code, out, _ = run([str(CSV_SAMPLE)])
        self.assertEqual(code, 0)
        self.assertIn("Final status: approved", out)

    def test_rejected_manifest_still_exits_zero(self):
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [f.unlink() for f in directory.iterdir()] or directory.rmdir())
        path = directory / "manifest.json"
        path.write_text(
            "["
            '{"package": "PKG-1", "route": "", "vehicle": "Van 02", '
            '"responsible": "Ana", "status": "pending"}'
            "]",
            encoding="utf-8",
        )
        code, out, err = run([str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("empty route", out)
        self.assertIn("Final status: rejected", out)

    def test_output_file_matches_stdout(self):
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [f.unlink() for f in directory.iterdir()] or directory.rmdir())
        output = directory / "report.txt"
        code, out, _ = run([str(SAMPLE), "--output", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(output.read_text(encoding="utf-8"), out)

    def test_missing_file_returns_error_code_without_traceback(self):
        code, out, err = run(["nope.json"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Error:", err)
        self.assertNotIn("Traceback", err)

    def test_output_directory_missing_returns_error_code(self):
        code, out, err = run([str(SAMPLE), "--output", "missing-dir/report.txt"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("could not write", err)


if __name__ == "__main__":
    unittest.main()
