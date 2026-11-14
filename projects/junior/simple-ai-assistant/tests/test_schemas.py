import copy
import json
import unittest

from ai_assistant.library import load_library
from ai_assistant.schemas import (
    example_errors,
    parse_json,
    respond_errors,
    understand_errors,
)

LIBRARY = load_library()
CUSTOMER = LIBRARY.profiles["customer"]
OPERATOR = LIBRARY.profiles["operator"]
DRIVER = LIBRARY.profiles["driver"]


def field(value, quote, origin):
    return {"value": value, "quote": quote, "origin": origin}


UNDERSTAND_OK = {
    "intent": "delivery",
    "fields": {
        "code": field("ABC123", "pacote ABC123", "informed"),
        "customer_name": field(None, None, "absent"),
    },
}
RESPOND_OK = {
    "speech": "Localizei o pacote ABC123. Qual é o seu nome?",
    "facts": [{"field": "status", "value": "in_transit", "origin": "base"}],
    "asking": ["customer_name"],
    "next_action": "ask_missing_information",
    "internal_note": {
        "priority": "medium",
        "priority_origin": "inferred",
        "text": "ABC123 em rota.",
    },
}


class ParseJsonTests(unittest.TestCase):
    def test_valid_object(self):
        data, errors = parse_json('{"a": 1}')
        self.assertEqual((data, errors), ({"a": 1}, []))

    def test_blank_answer_is_an_error(self):
        for blank in ("", "   \n", None):
            data, errors = parse_json(blank)
            self.assertIsNone(data)
            self.assertIn("empty", errors[0])

    def test_invalid_json_and_non_object(self):
        self.assertIn("not valid json", parse_json("{oops")[1][0])
        self.assertIn("must be a json object", parse_json("[1, 2]")[1][0])


class UnderstandSchemaTests(unittest.TestCase):
    def test_valid_answer_passes(self):
        self.assertEqual(understand_errors(UNDERSTAND_OK, LIBRARY, CUSTOMER), [])

    def test_unclear_is_always_allowed(self):
        answer = {**UNDERSTAND_OK, "intent": "unclear"}
        self.assertEqual(understand_errors(answer, LIBRARY, CUSTOMER), [])

    def test_intent_outside_the_profile_is_refused(self):
        answer = {**UNDERSTAND_OK, "intent": "occurrence"}
        errors = understand_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("output.intent" in error for error in errors))

    def test_missing_and_unexpected_keys(self):
        answer = copy.deepcopy(UNDERSTAND_OK)
        del answer["intent"]
        answer["extra"] = 1
        errors = understand_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("missing key 'intent'" in error for error in errors))
        self.assertTrue(any("unexpected key 'extra'" in error for error in errors))

    def test_fields_must_match_the_required_fields(self):
        answer = copy.deepcopy(UNDERSTAND_OK)
        del answer["fields"]["customer_name"]
        answer["fields"]["colour"] = field("red", "red", "informed")
        errors = understand_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("missing key 'customer_name'" in error for error in errors))
        self.assertTrue(any("unexpected key 'colour'" in error for error in errors))

    def test_unknown_is_an_origin_for_extracted_fields_but_not_for_facts_or_priority(self):
        answer = copy.deepcopy(UNDERSTAND_OK)
        answer["fields"]["code"] = field(None, "não sei meu código", "unknown")
        self.assertEqual(understand_errors(answer, LIBRARY, CUSTOMER), [])
        respond = copy.deepcopy(RESPOND_OK)
        respond["facts"][0]["origin"] = "unknown"
        respond["internal_note"]["priority_origin"] = "unknown"
        errors = respond_errors(respond, LIBRARY, CUSTOMER)
        self.assertTrue(any("facts[0].origin" in error for error in errors))
        self.assertTrue(any("priority_origin" in error for error in errors))

    def test_base_is_not_an_origin_for_extracted_fields(self):
        answer = copy.deepcopy(UNDERSTAND_OK)
        answer["fields"]["code"]["origin"] = "base"
        errors = understand_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("fields.code.origin" in error for error in errors))

    def test_null_is_only_allowed_where_declared(self):
        answer = copy.deepcopy(UNDERSTAND_OK)
        answer["fields"]["code"]["origin"] = None
        answer["intent"] = None
        errors = understand_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("must not be null" in error for error in errors))

    def test_not_an_object(self):
        self.assertTrue(understand_errors([], LIBRARY, CUSTOMER))


class RespondSchemaTests(unittest.TestCase):
    def test_valid_answer_passes_for_a_profile_with_internal_response(self):
        self.assertEqual(respond_errors(RESPOND_OK, LIBRARY, CUSTOMER), [])

    def test_extra_task_keys_are_required_by_profile(self):
        # the operator also uses summarization, so "summary" is mandatory there
        errors = respond_errors(RESPOND_OK, LIBRARY, OPERATOR)
        self.assertTrue(any("missing key 'summary'" in error for error in errors))

    def test_driver_needs_a_record_not_an_internal_note(self):
        errors = respond_errors(RESPOND_OK, LIBRARY, DRIVER)
        self.assertTrue(any("missing key 'record'" in error for error in errors))
        self.assertTrue(any("unexpected key 'internal_note'" in error for error in errors))

    def test_invalid_next_action_and_fact_origin(self):
        answer = copy.deepcopy(RESPOND_OK)
        answer["next_action"] = "do_magic"
        answer["facts"][0]["origin"] = "memory"
        errors = respond_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("next_action" in error for error in errors))
        self.assertTrue(any("facts[0].origin" in error for error in errors))

    def test_internal_note_priority_must_be_in_the_vocabulary(self):
        answer = copy.deepcopy(RESPOND_OK)
        answer["internal_note"]["priority"] = "urgent"
        errors = respond_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("internal_note.priority" in error for error in errors))

    def test_asking_must_name_required_fields(self):
        answer = copy.deepcopy(RESPOND_OK)
        answer["asking"] = ["colour"]
        errors = respond_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("output.asking[0]" in error for error in errors))

    def test_asking_is_a_required_key(self):
        answer = copy.deepcopy(RESPOND_OK)
        del answer["asking"]
        errors = respond_errors(answer, LIBRARY, CUSTOMER)
        self.assertTrue(any("missing key 'asking'" in error for error in errors))

    def test_an_absent_fact_may_have_a_null_value_at_schema_level(self):
        answer = copy.deepcopy(RESPOND_OK)
        answer["facts"].append({"field": "code", "value": None, "origin": "absent"})
        self.assertEqual(respond_errors(answer, LIBRARY, CUSTOMER), [])

    def test_priority_may_be_null(self):
        answer = copy.deepcopy(RESPOND_OK)
        answer["internal_note"].update(priority=None, priority_origin="absent")
        self.assertEqual(respond_errors(answer, LIBRARY, CUSTOMER), [])

    def test_empty_speech_is_refused(self):
        answer = {**RESPOND_OK, "speech": "  "}
        self.assertTrue(
            any("speech" in error for error in respond_errors(answer, LIBRARY, CUSTOMER))
        )


class ExamplesFollowTheSchemaTests(unittest.TestCase):
    def test_every_few_shot_example_obeys_the_output_schema(self):
        for prompt in LIBRARY.prompts.values():
            for example in prompt.examples:
                errors = example_errors(prompt.output_fields, example.output, LIBRARY)
                self.assertEqual(errors, [], f"{prompt.id}/{example.type}: {errors}")

    def test_a_broken_example_is_detected(self):
        prompt = LIBRARY.prompts["classification"]
        self.assertTrue(example_errors(prompt.output_fields, {"intent": "refund"}, LIBRARY))
        self.assertEqual(json.loads('{"intent": "delivery"}'), {"intent": "delivery"})


if __name__ == "__main__":
    unittest.main()
