import unittest

from ai_assistant.library import load_library
from ai_assistant.rubrics import (
    Evidence,
    check_disclosure,
    check_entities,
    check_facts,
    check_false_actions,
    check_internal_note,
    check_next_action,
    check_record,
    check_respond,
    check_understand,
)

LIBRARY = load_library()
SOURCE = {
    "code": "ABC123",
    "customer": "Maria Souza",
    "address": "Rua das Flores, 123",
    "deadline": "2026-11-20",
    "status": "in_transit",
}
MESSAGE = "meu pacote ABC123 não chegou, sou a Maria Souza"


def field(value, quote, origin):
    return {"value": value, "quote": quote, "origin": origin}


def evidence(message=MESSAGE, memory=(), source=None):
    return Evidence(message=message, memory_texts=tuple(memory), source=source)


class UnderstandRubricTests(unittest.TestCase):
    def check(self, item, ev=None):
        return check_understand({"fields": {"code": item}}, ev or evidence())

    def test_grounded_field_passes(self):
        self.assertEqual(self.check(field("ABC123", "pacote ABC123", "informed")), [])

    def test_quote_must_exist_in_the_message(self):
        errors = self.check(field("ABC123", "pacote ZZZ999", "informed"))
        self.assertTrue(any("quote" in error for error in errors))

    def test_informed_value_must_be_user_text(self):
        errors = self.check(field("XYZ789", "pacote ABC123", "informed"))
        self.assertTrue(any("informed value 'XYZ789'" in error for error in errors))

    def test_quote_may_come_from_the_memory(self):
        ev = evidence(message="e o prazo?", memory=["pacote ABC123"])
        self.assertEqual(self.check(field("ABC123", "pacote ABC123", "informed"), ev), [])

    def test_absent_must_be_null(self):
        errors = self.check(field("ABC123", None, "absent"))
        self.assertTrue(any("absent field" in error for error in errors))

    def test_present_value_needs_a_quote_and_a_value(self):
        self.assertTrue(self.check(field("ABC123", None, "informed")))
        self.assertTrue(self.check(field(None, "pacote ABC123", "informed")))

    def test_inferred_value_still_needs_a_real_quote(self):
        self.assertEqual(self.check(field("high", "não chegou", "inferred")), [])
        self.assertTrue(self.check(field("high", "urgentíssimo", "inferred")))

    def test_comparison_ignores_case_spacing_and_edge_punctuation(self):
        ev = evidence(message="Pacote   ABC123 não chegou.")
        self.assertEqual(
            self.check(field("abc123", "pacote abc123 não chegou", "informed"), ev), []
        )


class FactRubricTests(unittest.TestCase):
    def test_base_fact_must_equal_the_source(self):
        facts = [{"field": "deadline", "value": "2026-11-20", "origin": "base"}]
        self.assertEqual(check_facts(facts, evidence(source=SOURCE)), [])
        facts[0]["value"] = "2026-11-21"
        errors = check_facts(facts, evidence(source=SOURCE))
        self.assertTrue(any("source says '2026-11-20'" in error for error in errors))

    def test_base_fact_without_a_source_is_refused(self):
        facts = [{"field": "status", "value": "in_transit", "origin": "base"}]
        self.assertTrue(any("no source record" in e for e in check_facts(facts, evidence())))

    def test_base_fact_for_an_unknown_field_is_refused(self):
        facts = [{"field": "driver", "value": "Pedro", "origin": "base"}]
        self.assertTrue(
            any("no field 'driver'" in e for e in check_facts(facts, evidence(source=SOURCE)))
        )

    def test_informed_fact_must_be_user_text_and_inferred_is_free(self):
        informed = [{"field": "code", "value": "ABC123", "origin": "informed"}]
        self.assertEqual(check_facts(informed, evidence()), [])
        invented = [{"field": "code", "value": "QQQ111", "origin": "informed"}]
        self.assertTrue(check_facts(invented, evidence()))
        inferred = [{"field": "priority", "value": "high", "origin": "inferred"}]
        self.assertEqual(check_facts(inferred, evidence()), [])


class EntityRubricTests(unittest.TestCase):
    def test_codes_from_the_sources_pass(self):
        ev = evidence(source=SOURCE)
        self.assertEqual(check_entities("Localizei o pacote ABC123.", ev, "speech"), [])

    def test_an_invented_code_is_refused(self):
        errors = check_entities("O pacote ZZZ999 está em rota.", evidence(), "speech")
        self.assertTrue(any("'ZZZ999'" in error for error in errors))

    def test_a_date_in_br_format_matches_the_iso_source(self):
        ev = evidence(source=SOURCE)
        self.assertEqual(check_entities("Previsão para 20/11/2026.", ev, "speech"), [])
        self.assertEqual(check_entities("Previsão para 20/11.", ev, "speech"), [])

    def test_a_wrong_or_invented_date_is_refused(self):
        ev = evidence(source=SOURCE)
        self.assertTrue(check_entities("Previsão para 21/11/2026.", ev, "speech"))
        self.assertTrue(check_entities("Previsão para 20/11/2027.", ev, "speech"))

    def test_an_invented_name_is_refused_but_a_known_one_passes(self):
        ev = evidence()
        self.assertEqual(check_entities("Obrigada, Maria.", ev, "speech"), [])
        errors = check_entities("Obrigada, Carlos.", ev, "speech")
        self.assertTrue(any("'Carlos'" in error for error in errors))

    def test_the_first_word_of_a_sentence_is_not_a_name(self):
        self.assertEqual(
            check_entities("Entendi. Localizei tudo. Obrigada.", evidence(), "speech"), []
        )

    def test_brand_words_are_allowed(self):
        self.assertEqual(check_entities("Aqui é a FilaFácil Logística.", evidence(), "speech"), [])

    def test_another_customers_data_cannot_leak(self):
        ev = evidence(source=SOURCE)
        errors = check_entities("O pacote DEF456 é de Carla Dias.", ev, "speech")
        self.assertTrue(any("'DEF456'" in error for error in errors))
        self.assertTrue(any("'Carla'" in error for error in errors))


class DisclosureTests(unittest.TestCase):
    HIDDEN = ("customer", "address")

    def test_a_hidden_source_value_cannot_be_revealed_to_an_unidentified_user(self):
        speech = "A entrega está em nome de Maria Souza, na Rua das Flores, 123."
        errors = check_disclosure(
            speech, evidence(message="cadê o ABC123?", source=SOURCE), self.HIDDEN
        )
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("'customer'" in error for error in errors))
        self.assertTrue(any("'address'" in error for error in errors))

    def test_the_value_can_be_repeated_once_the_user_said_it_first(self):
        speech = "Obrigada, Maria Souza. Localizei o pacote."
        ev = evidence(message="sou a Maria Souza", source=SOURCE)
        self.assertEqual(check_disclosure(speech, ev, self.HIDDEN), [])

    def test_nothing_is_hidden_when_the_profile_hides_no_field(self):
        speech = "Endereço cadastrado: Rua das Flores, 123."
        self.assertEqual(check_disclosure(speech, evidence(source=SOURCE), ()), [])

    def test_check_respond_applies_the_disclosure_rule(self):
        output = {
            "speech": "Localizei o pacote ABC123, em nome de Maria Souza.",
            "facts": [],
            "next_action": "provide_information",
        }
        ev = evidence(message="cadê o ABC123?", source=SOURCE)
        errors = check_respond(
            output, ev, intent="delivery", missing=(), hidden_fields=("customer",)
        )
        self.assertTrue(any("reveals the source field 'customer'" in error for error in errors))
        self.assertEqual(check_respond(output, ev, intent="delivery", missing=()), [])


class FalseActionTests(unittest.TestCase):
    def test_claiming_to_register_is_refused(self):
        self.assertTrue(check_false_actions("Registrei o aviso de atraso.", "speech"))
        self.assertTrue(check_false_actions("Cancelei a entrega.", "speech"))

    def test_preparing_a_record_is_fine(self):
        self.assertEqual(check_false_actions("Preparei um registro para a equipe.", "speech"), [])


class NextActionTests(unittest.TestCase):
    def test_escalation_intent_requires_escalating(self):
        self.assertTrue(check_next_action("provide_information", "human_escalation", ()))
        self.assertEqual(check_next_action("escalate_to_human", "human_escalation", ()), [])

    def test_with_missing_fields_the_only_allowed_actions_are_asking_or_escalating(self):
        for action in ("hand_off_to_team", "close", "provide_information"):
            errors = check_next_action(action, "delivery", ("customer_name",))
            self.assertTrue(any("required fields are missing" in e for e in errors), action)
        self.assertEqual(check_next_action("escalate_to_human", "delivery", ("customer_name",)), [])
        self.assertEqual(
            check_next_action("ask_missing_information", "delivery", ("customer_name",)), []
        )

    def test_does_not_ask_when_nothing_is_missing(self):
        self.assertTrue(check_next_action("ask_missing_information", "delivery", ()))
        self.assertEqual(check_next_action("ask_missing_information", "unclear", ()), [])

    def test_asking_for_what_is_missing_is_fine(self):
        self.assertEqual(check_next_action("ask_missing_information", "delivery", ("code",)), [])


class RecordAndNoteTests(unittest.TestCase):
    def test_record_absent_means_null(self):
        record = {"code": {"value": "ABC123", "origin": "absent"}}
        self.assertTrue(check_record(record, evidence()))
        record = {"code": {"value": None, "origin": "absent"}}
        self.assertEqual(check_record(record, evidence()), [])

    def test_record_informed_value_must_be_user_text(self):
        good = {"problem": {"value": "não chegou", "origin": "informed"}}
        bad = {"problem": {"value": "caminhão quebrou", "origin": "informed"}}
        self.assertEqual(check_record(good, evidence()), [])
        self.assertTrue(check_record(bad, evidence()))

    def test_internal_note_priority_and_origin_go_together(self):
        bad = {"priority": "high", "priority_origin": "absent", "text": "ok"}
        good = {"priority": None, "priority_origin": "absent", "text": "Faltam dados."}
        self.assertTrue(check_internal_note(bad, evidence()))
        self.assertEqual(check_internal_note(good, evidence()), [])


class RespondRubricTests(unittest.TestCase):
    def output(self, **overrides):
        base = {
            "speech": "Localizei o pacote ABC123: está em rota, com previsão para 20/11/2026.",
            "facts": [
                {"field": "status", "value": "in_transit", "origin": "base"},
                {"field": "deadline", "value": "2026-11-20", "origin": "base"},
            ],
            "next_action": "provide_information",
        }
        return {**base, **overrides}

    def test_a_grounded_answer_passes(self):
        errors = check_respond(
            self.output(), evidence(source=SOURCE), intent="delivery", missing=()
        )
        self.assertEqual(errors, [])

    def test_the_invented_deadline_scenario_is_caught(self):
        wrong = self.output(speech="Seu pacote ABC123 chega em 22/11/2026.")
        errors = check_respond(wrong, evidence(source=SOURCE), intent="delivery", missing=())
        self.assertTrue(any("22/11/2026" in error for error in errors))

    def test_collects_several_violations_at_once(self):
        wrong = self.output(
            speech="Registrei o pacote ZZZ999.",
            facts=[{"field": "status", "value": "completed", "origin": "base"}],
            next_action="hand_off_to_team",
        )
        errors = check_respond(
            wrong, evidence(source=SOURCE), intent="delivery", missing=("customer_name",)
        )
        self.assertGreaterEqual(len(errors), 4)


class FewShotExamplesPassTheRubricsTests(unittest.TestCase):
    """The examples shown to the model must themselves be grounded in their own input."""

    def test_extraction_examples(self):
        for example in LIBRARY.prompts["extraction"].examples:
            errors = check_understand(example.output, evidence(message=example.input))
            self.assertEqual(errors, [], f"{example.type}: {errors}")

    def test_text_transformation_examples(self):
        for example in LIBRARY.prompts["text_transformation"].examples:
            errors = check_record(example.output["record"], evidence(message=example.input))
            self.assertEqual(errors, [], f"{example.type}: {errors}")

    def test_summarization_examples(self):
        for example in LIBRARY.prompts["summarization"].examples:
            ev = evidence(message=example.input)
            summary = example.output["summary"]
            errors = check_entities(summary, ev, "summary") + check_false_actions(
                summary, "summary"
            )
            self.assertEqual(errors, [], f"{example.type}: {errors}")

    def test_internal_response_examples(self):
        for example in LIBRARY.prompts["internal_response"].examples:
            errors = check_internal_note(
                example.output["internal_note"], evidence(message=example.input)
            )
            self.assertEqual(errors, [], f"{example.type}: {errors}")


if __name__ == "__main__":
    unittest.main()
