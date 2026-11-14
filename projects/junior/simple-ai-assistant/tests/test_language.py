"""The project is in English; only what a person reads on screen is Portuguese."""

import re
import unittest
from pathlib import Path

from ai_assistant.library import PROJECT_ROOT

ACCENTED = re.compile("[áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]")
# The company name is a proper noun, not Portuguese prose.
BRAND = re.compile("FilaFácil|Logística|logística")
# A Portuguese sample quoted inside an English instruction is an example, not an instruction.
QUOTED_SAMPLE = re.compile(r'\\"[^"]*\\"')
SOURCE = PROJECT_ROOT / "src" / "ai_assistant"


class LanguageTests(unittest.TestCase):
    def test_portuguese_text_in_code_lives_only_in_ui_text(self):
        offenders = []
        for path in sorted(SOURCE.glob("*.py")):
            if path.name == "ui_text.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if ACCENTED.search(BRAND.sub("", line)):
                    offenders.append(f"{path.name}:{number}: {line.strip()}")
        self.assertEqual(offenders, [])

    def test_prompt_instructions_are_in_english_and_only_examples_use_portuguese(self):
        offenders = []
        for path in sorted((PROJECT_ROOT / "prompts").glob("*.toml")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                key = line.split("=", 1)[0].strip()
                if key in ("input", "output", "note"):
                    continue
                prose = QUOTED_SAMPLE.sub("", BRAND.sub("", line))
                if ACCENTED.search(prose):
                    offenders.append(f"{path.name}:{number}: {line.strip()}")
        self.assertEqual(offenders, [])

    def test_profiles_and_the_deliveries_base_are_in_english(self):
        proper_names = re.compile("João|FilaFácil|Logística|Souza")
        for path in sorted(Path(PROJECT_ROOT, "profiles").glob("*.toml")):
            text = proper_names.sub("", path.read_text(encoding="utf-8"))
            self.assertIsNone(ACCENTED.search(text), path.name)


if __name__ == "__main__":
    unittest.main()
