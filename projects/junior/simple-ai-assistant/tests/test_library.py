import shutil
import tempfile
import unittest
from pathlib import Path

from ai_assistant.library import (
    EXAMPLE_TYPES,
    PROFILE_IDS,
    PROJECT_ROOT,
    TASK_IDS,
    LibraryError,
    load_library,
)


class LibraryLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load_library()

    def test_loads_the_five_task_prompts_and_four_profiles(self):
        self.assertEqual(tuple(self.library.prompts), TASK_IDS)
        self.assertEqual(tuple(self.library.profiles), PROFILE_IDS)

    def test_every_prompt_covers_the_four_example_types(self):
        for prompt in self.library.prompts.values():
            kinds = {example.type for example in prompt.examples}
            self.assertEqual(kinds, set(EXAMPLE_TYPES), prompt.id)

    def test_example_outputs_match_the_declared_output_fields(self):
        for prompt in self.library.prompts.values():
            for example in prompt.examples:
                self.assertEqual(set(example.output), set(prompt.output_fields), prompt.id)

    def test_every_task_loads_on_its_own(self):
        for task_id in TASK_IDS:
            prompt = self.library.prompts[task_id]
            self.assertEqual(prompt.id, task_id)
            self.assertTrue(prompt.constraints and prompt.criteria)

    def test_every_profile_can_escalate_and_uses_the_core_tasks(self):
        for profile in self.library.profiles.values():
            self.assertIn("human_escalation", profile.intents)
            self.assertIn("classification", profile.tasks)
            self.assertIn("extraction", profile.tasks)

    def test_only_the_customer_hides_source_fields(self):
        self.assertEqual(self.library.profiles["customer"].hidden_fields, ("customer", "address"))
        for profile_id in ("operator", "partner", "driver"):
            self.assertEqual(self.library.profiles[profile_id].hidden_fields, ())

    def test_only_the_driver_must_always_conclude_by_escalating(self):
        self.assertEqual(self.library.profiles["driver"].conclude_with, "escalate_to_human")
        for profile_id in ("customer", "operator", "partner"):
            self.assertIsNone(self.library.profiles[profile_id].conclude_with)

    def test_tasks_for_splits_the_profile_tasks_by_stage(self):
        understand = self.library.tasks_for("operator", "understand")
        respond = self.library.tasks_for("operator", "respond")
        self.assertEqual([p.id for p in understand], ["classification", "extraction"])
        self.assertEqual([p.id for p in respond], ["summarization", "internal_response"])

    def test_global_rules_and_vocabulary_are_present(self):
        self.assertGreaterEqual(len(self.library.rules), 5)
        self.assertIn("unclear", self.library.vocabulary.intents)
        self.assertIn("absent", self.library.vocabulary.origins)
        self.assertIn("escalate_to_human", self.library.vocabulary.next_actions)


class LibraryValidationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for folder in ("prompts", "profiles"):
            shutil.copytree(PROJECT_ROOT / folder, self.root / folder)

    def edit(self, relative: str, old: str, new: str) -> None:
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, "test setup: text to replace not found")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assertRefused(self, *fragments: str) -> None:
        with self.assertRaises(LibraryError) as context:
            load_library(self.root)
        for fragment in fragments:
            self.assertIn(fragment, str(context.exception))

    def test_valid_copy_loads(self):
        self.assertEqual(tuple(load_library(self.root).prompts), TASK_IDS)

    def test_refuses_a_prompt_without_objective(self):
        self.edit("prompts/classification.toml", 'objective = "', 'objective_ = "')
        self.assertRefused("classification.toml", "objective")

    def test_refuses_a_prompt_missing_an_example_type(self):
        self.edit("prompts/classification.toml", 'type = "escalation"', 'type = "positive"')
        self.assertRefused("classification.toml", "escalation")

    def test_refuses_an_example_with_invalid_json(self):
        self.edit(
            "prompts/classification.toml", """'''{"intent": "delivery"}'''""", "'''{\"intent\": '''"
        )
        self.assertRefused("classification.toml", "not valid JSON")

    def test_refuses_example_keys_that_differ_from_output_fields(self):
        self.edit("prompts/classification.toml", '{"intent": "delivery"}', '{"kind": "delivery"}')
        self.assertRefused("classification.toml", "output keys")

    def test_refuses_an_unknown_stage(self):
        self.edit("prompts/extraction.toml", 'stage = "understand"', 'stage = "later"')
        self.assertRefused("extraction.toml", "stage")

    def test_refuses_an_id_that_does_not_match_the_file_name(self):
        self.edit("prompts/extraction.toml", 'id = "extraction"', 'id = "extract"')
        self.assertRefused("extraction.toml", "does not match")

    def test_refuses_invalid_toml(self):
        self.edit("prompts/summarization.toml", "version = 1", "version = = 1")
        self.assertRefused("summarization.toml", "invalid TOML")

    def test_refuses_a_missing_prompt_file(self):
        (self.root / "prompts" / "summarization.toml").unlink()
        self.assertRefused("summarization.toml", "not found")

    def test_refuses_a_profile_with_an_unknown_intent(self):
        self.edit("profiles/customer.toml", '"proof"', '"refund"')
        self.assertRefused("customer.toml", "unknown intents")

    def test_refuses_a_profile_that_cannot_escalate(self):
        self.edit("profiles/customer.toml", ', "human_escalation"', "")
        self.assertRefused("customer.toml", "human_escalation")

    def test_refuses_a_profile_that_concludes_with_an_unknown_action(self):
        self.edit("profiles/driver.toml", '"escalate_to_human"\n', '"fly_away"\n')
        self.assertRefused("driver.toml", "conclude_with")

    def test_refuses_a_profile_with_an_unknown_task(self):
        self.edit("profiles/driver.toml", '"text_transformation"', '"magic"')
        self.assertRefused("driver.toml", "unknown tasks")

    def test_refuses_a_profile_without_the_core_tasks(self):
        self.edit("profiles/partner.toml", '"classification", "extraction"', '"classification"')
        self.assertRefused("partner.toml", "extraction")


if __name__ == "__main__":
    unittest.main()
