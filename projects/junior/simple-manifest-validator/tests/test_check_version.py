import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "check_version.py"


class CheckVersionTests(unittest.TestCase):
    def run_check(self, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_version_without_a_tag_passes(self):
        env = os.environ.copy()
        env.pop("GITHUB_REF_TYPE", None)
        env.pop("GITHUB_REF_NAME", None)
        result = self.run_check(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1.0.0", result.stdout)

    def test_matching_tag_passes(self):
        env = os.environ.copy()
        env["GITHUB_REF_TYPE"] = "tag"
        env["GITHUB_REF_NAME"] = "simple-manifest-v1.0.0"
        result = self.run_check(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mismatched_tag_fails(self):
        env = os.environ.copy()
        env["GITHUB_REF_TYPE"] = "tag"
        env["GITHUB_REF_NAME"] = "simple-manifest-v9.9.9"
        result = self.run_check(env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("simple-manifest-v1.0.0", result.stderr)


if __name__ == "__main__":
    unittest.main()
