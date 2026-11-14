import tempfile
import unittest
from pathlib import Path

from ai_assistant.config import (
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
    ConfigError,
    load_settings,
    read_env_file,
)


class EnvFileTests(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(text, encoding="utf-8")
            return read_env_file(path)

    def test_parses_plain_pairs_comments_blanks_and_quotes(self):
        values = self.read(
            "# comment\n\nA=1\nB = two \nC=\"quoted value\"\nD='single'\nexport E=exported\nF=a=b\n"
        )
        self.assertEqual(
            values,
            {"A": "1", "B": "two", "C": "quoted value", "D": "single", "E": "exported", "F": "a=b"},
        )

    def test_ignores_malformed_lines(self):
        self.assertEqual(self.read("no equals sign\n=novalue\nOK=1\n"), {"OK": "1"})

    def test_a_missing_file_is_just_empty(self):
        self.assertEqual(read_env_file(Path("/nonexistent/.env")), {})


class SettingsTests(unittest.TestCase):
    def settings(self, file_text="", environ=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(file_text, encoding="utf-8")
            return load_settings(environ or {}, path)

    def test_defaults_when_nothing_is_configured(self):
        settings = self.settings()
        self.assertIsNone(settings.api_key)
        self.assertEqual(settings.model, DEFAULT_MODEL)
        self.assertEqual(settings.timeout, DEFAULT_TIMEOUT)

    def test_values_come_from_the_env_file(self):
        settings = self.settings(
            "DEEPSEEK_API_KEY=file-key\nDEEPSEEK_MODEL=other\nDEEPSEEK_TIMEOUT=12\n"
        )
        self.assertEqual(
            (settings.api_key, settings.model, settings.timeout), ("file-key", "other", 12.0)
        )

    def test_the_environment_wins_over_the_file(self):
        settings = self.settings("DEEPSEEK_API_KEY=file-key\n", {"DEEPSEEK_API_KEY": "env-key"})
        self.assertEqual(settings.api_key, "env-key")

    def test_thinking_is_off_by_default_and_parsed_from_the_setting(self):
        self.assertFalse(self.settings().thinking)
        for raw in ("on", "TRUE", "1", "enabled"):
            self.assertTrue(self.settings(f"DEEPSEEK_THINKING={raw}\n").thinking, raw)
        for raw in ("off", "false", "0", "disabled"):
            self.assertFalse(self.settings(f"DEEPSEEK_THINKING={raw}\n").thinking, raw)

    def test_an_invalid_thinking_value_is_refused(self):
        with self.assertRaises(ConfigError):
            self.settings("DEEPSEEK_THINKING=maybe\n")

    def test_an_invalid_timeout_is_refused(self):
        for bad in ("abc", "0", "-3"):
            with self.assertRaises(ConfigError):
                self.settings(f"DEEPSEEK_TIMEOUT={bad}\n")

    def test_the_key_is_not_shown_by_repr_or_str(self):
        settings = self.settings("DEEPSEEK_API_KEY=sk-test-secret-value\n")
        self.assertNotIn("sk-test-secret-value", repr(settings))
        self.assertNotIn("sk-test-secret-value", str(settings))


if __name__ == "__main__":
    unittest.main()
