import contextlib
import io
import json
import unittest
from pathlib import Path

from simple_report_pipeline.cli import main

SAMPLE = Path(__file__).parent.parent / "samples" / "pickups.json"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_text_report(self):
        code, out, _ = run([str(SAMPLE)])
        self.assertEqual(code, 0)
        self.assertIn("Total de coletas: 4 | Total de pacotes: 20", out)

    def test_json_report(self):
        code, out, _ = run([str(SAMPLE), "--format", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["by_status"]["pending"], 2)

    def test_missing_file_returns_error_code_without_traceback(self):
        code, out, err = run(["nope.json"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Erro:", err)


if __name__ == "__main__":
    unittest.main()
