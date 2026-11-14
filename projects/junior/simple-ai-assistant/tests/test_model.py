import unittest

from ai_assistant.model import ModelError, ScriptedModel


class ScriptedModelTests(unittest.TestCase):
    def test_returns_responses_in_order_and_serialises_dicts(self):
        model = ScriptedModel(["first", {"a": "ç"}])
        self.assertEqual(model.complete("s", "u"), "first")
        self.assertEqual(model.complete("s", "u"), '{"a": "ç"}')
        self.assertEqual(model.remaining, 0)

    def test_records_every_call(self):
        model = ScriptedModel(["x"])
        model.complete("system text", "user text")
        self.assertEqual(model.calls, [("system text", "user text")])

    def test_raises_scripted_exceptions(self):
        model = ScriptedModel([ModelError("boom")])
        with self.assertRaises(ModelError):
            model.complete("s", "u")

    def test_running_out_of_responses_is_an_error(self):
        with self.assertRaises(ModelError):
            ScriptedModel([]).complete("s", "u")


if __name__ == "__main__":
    unittest.main()
