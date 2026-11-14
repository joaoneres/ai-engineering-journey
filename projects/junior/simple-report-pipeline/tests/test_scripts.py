import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import build_manifest  # noqa: E402
import check_version  # noqa: E402
import publish  # noqa: E402
import run_local  # noqa: E402

COMMIT = "a" * 40


class CheckVersionTests(unittest.TestCase):
    def test_valid_without_tag(self):
        self.assertIsNone(check_version.check("1.2.3", None))

    def test_tag_must_match_version(self):
        self.assertIsNone(check_version.check("1.2.3", "simple-report-v1.2.3"))
        self.assertIn("diverge", check_version.check("1.2.3", "simple-report-v1.2.4"))

    def test_rejects_wrong_prefix_and_non_semantic_version(self):
        self.assertIn("começa com", check_version.check("1.2.3", "v1.2.3"))
        self.assertIn("semântica", check_version.check("1.2", None))


class PublishTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dist = Path(tmp.name) / "dist"
        self.registry = Path(tmp.name) / "registry"
        self.dist.mkdir()
        (self.dist / "pkg-1.0.0-py3-none-any.whl").write_bytes(b"wheel")
        (self.dist / "pkg-1.0.0.tar.gz").write_bytes(b"sdist")
        manifest = build_manifest.build_manifest(self.dist, "homolog", "built", COMMIT)
        (self.dist / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def run_publish(self, environment="homolog"):
        return publish.main(
            [
                "--dist",
                str(self.dist),
                "--registry",
                str(self.registry),
                "--environment",
                environment,
            ]
        )

    def test_manifest_has_the_six_fields_and_checksums(self):
        manifest = json.loads((self.dist / "manifest.json").read_text(encoding="utf-8"))
        for field in ("project", "version", "commit", "environment", "published_at", "status"):
            self.assertIn(field, manifest)
        self.assertEqual(len(manifest["files"]), 2)

    def test_publishes_then_skips_the_repeat(self):
        self.assertEqual(self.run_publish(), 0)
        manifest = json.loads((self.dist / "manifest.json").read_text(encoding="utf-8"))
        entry = self.registry / "homolog" / publish.publication_id(manifest, "homolog")
        published = json.loads((entry / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(published["status"], "published")
        self.assertIsNotNone(published["published_at"])
        self.assertEqual(self.run_publish(), 0)
        self.assertEqual(len(list((self.registry / "homolog").iterdir())), 1)

    def test_prod_without_token_fails_without_leaking_values(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PUBLISH_TOKEN", None)
            self.assertEqual(self.run_publish("prod"), publish.EXIT_SECRET)
        self.assertFalse(self.registry.exists())

    def test_prod_with_token_publishes(self):
        with mock.patch.dict(os.environ, {"PUBLISH_TOKEN": "x"}):
            self.assertEqual(self.run_publish("prod"), 0)

    def test_tampered_file_fails_checksum(self):
        (self.dist / "pkg-1.0.0.tar.gz").write_bytes(b"tampered")
        self.assertEqual(self.run_publish(), publish.EXIT_CHECKSUM)
        self.assertFalse(self.registry.exists())


class RunLocalTests(unittest.TestCase):
    def test_stops_at_first_failure_and_skips_the_rest(self):
        stages = {
            "qualidade": [("ok", ["a"])],
            "testes": [("quebra", ["b"])],
            "build": [("x", ["c"])],
        }
        results, code = run_local.run_stages(stages, runner=lambda cmd: 1 if cmd == ["b"] else 0)
        self.assertEqual(code, 1)
        self.assertEqual([status for _, status in results], ["OK", "FALHOU", "PULADO"])


if __name__ == "__main__":
    unittest.main()
