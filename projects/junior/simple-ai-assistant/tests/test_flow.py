import unittest

from ai_assistant.deliveries import load_deliveries
from ai_assistant.flow import Flow
from ai_assistant.library import PROFILE_IDS, load_library
from ai_assistant.model import ModelError, ScriptedModel
from ai_assistant.scenarios import load_scenario

LIBRARY = load_library()
DELIVERIES = load_deliveries()


def item(value, quote, origin="informed"):
    return {"value": value, "quote": quote, "origin": origin}


ABSENT = item(None, None, "absent")


def customer_understand(code="ABC123", name=ABSENT):
    code_item = item(code, f"pacote {code}") if code else ABSENT
    return {"intent": "delivery", "fields": {"code": code_item, "customer_name": name}}


def customer_respond(**overrides):
    answer = {
        "speech": (
            "Localizei o pacote ABC123: está em rota, com previsão de entrega para 20/11/2026. "
            "Qual é o seu nome?"
        ),
        "facts": [{"field": "deadline", "value": "2026-11-20", "origin": "base"}],
        "asking": ["customer_name"],
        "next_action": "ask_missing_information",
        "internal_note": {
            "priority": None,
            "priority_origin": "absent",
            "text": "Entrega ABC123 consultada.",
        },
    }
    return {**answer, **overrides}


def run(profile, message, responses, state=None):
    model = ScriptedModel(responses)
    flow = Flow(LIBRARY, model, DELIVERIES)
    return flow, model, flow.turn(state or flow.start(profile), message)


class ScenarioTests(unittest.TestCase):
    EXPECTED_FINAL = {
        "customer": "hand_off_to_team",
        "operator": "hand_off_to_team",
        "partner": "hand_off_to_team",
        "driver": "escalate_to_human",
    }

    def test_every_recorded_scenario_passes_the_real_validators_without_retries(self):
        for profile in PROFILE_IDS:
            scenario = load_scenario(profile)
            model = scenario.scripted_model()
            flow = Flow(LIBRARY, model, DELIVERIES)
            state = flow.start(profile)
            for turn in scenario.turns:
                result = flow.turn(state, turn.user)
                state = result.state
                self.assertIsNone(result.failure, f"{profile}: {result.errors}")
                self.assertEqual(result.model_calls, 2, profile)  # understand + respond, no retry
            self.assertEqual(model.remaining, 0, profile)
            self.assertEqual(result.next_action, self.EXPECTED_FINAL[profile], profile)

    def test_the_driver_scenario_ends_escalated_with_a_standard_record(self):
        scenario = load_scenario("driver")
        flow = Flow(LIBRARY, scenario.scripted_model(), DELIVERIES)
        result = flow.turn(flow.start("driver"), scenario.turns[0].user)
        self.assertTrue(result.escalated)
        record = dict(result.state.extras)["record"]
        self.assertEqual(record["code"]["value"], "ABC123")

    def test_the_customer_scenario_collects_the_name_over_two_turns(self):
        scenario = load_scenario("customer")
        flow = Flow(LIBRARY, scenario.scripted_model(), DELIVERIES)
        first = flow.turn(flow.start("customer"), scenario.turns[0].user)
        self.assertEqual(first.next_action, "ask_missing_information")
        self.assertEqual(first.state.asked, ("customer_name",))
        second = flow.turn(first.state, scenario.turns[1].user)
        self.assertEqual(second.state.field("customer_name").value, "Maria Souza")
        self.assertEqual(second.state.field("code").value, "ABC123")  # remembered, not re-asked

    def test_a_partner_conversation_asks_only_for_the_missing_field(self):
        scenario = load_scenario("partner")
        flow = Flow(LIBRARY, scenario.scripted_model(), DELIVERIES)
        first = flow.turn(flow.start("partner"), scenario.turns[0].user)
        self.assertEqual(first.state.asked, ("moment",))


class LookupTests(unittest.TestCase):
    def test_the_source_is_only_sent_in_the_respond_step_and_comes_from_the_base(self):
        _, model, _ = run(
            "customer", "meu pacote ABC123 não chegou", [customer_understand(), customer_respond()]
        )
        understand_user, respond_user = model.calls[0][1], model.calls[1][1]
        self.assertNotIn("<source>", understand_user)
        self.assertIn('"found": true', respond_user)
        self.assertIn(
            "Maria Souza", respond_user
        )  # the base record, looked up by code in plain code

    def test_a_code_that_is_not_in_the_base_is_reported_as_not_found(self):
        understand = customer_understand(code="ZZZ999")
        respond = customer_respond(
            speech="Não encontrei nenhuma entrega com o código ZZZ999. Pode conferir o código?",
            facts=[],
            internal_note={
                "priority": None,
                "priority_origin": "absent",
                "text": "Entrega ZZZ999 não localizada.",
            },
        )
        _, model, result = run("customer", "meu pacote ZZZ999 não chegou", [understand, respond])
        self.assertIsNone(result.failure)
        self.assertIn('"found": false', model.calls[1][1])

    def test_base_facts_are_refused_when_nothing_was_found(self):
        understand = customer_understand(code="ZZZ999")
        invented = customer_respond(
            speech="O pacote ZZZ999 chega em 20/11/2026. Qual é o seu nome?"
        )
        fixed = customer_respond(
            speech="Não encontrei nenhuma entrega com o código ZZZ999. Qual é o seu nome?",
            facts=[],
            internal_note={
                "priority": None,
                "priority_origin": "absent",
                "text": "Entrega ZZZ999 não localizada.",
            },
        )
        _, model, result = run(
            "customer", "meu pacote ZZZ999 não chegou", [understand, invented, fixed]
        )
        self.assertIsNone(result.failure)
        self.assertEqual(result.model_calls, 3)
        self.assertIn("no source record", model.calls[2][1])


class GuidedRetryTests(unittest.TestCase):
    def test_a_rejected_answer_is_retried_with_the_exact_errors(self):
        wrong = customer_respond(speech="Seu pacote ABC123 chega em 22/11/2026. Qual é o seu nome?")
        _, model, result = run(
            "customer",
            "meu pacote ABC123 não chegou",
            [customer_understand(), wrong, customer_respond()],
        )
        self.assertIsNone(result.failure)
        self.assertEqual(result.model_calls, 3)
        retry_prompt = model.calls[2][1]
        self.assertIn("<validation_errors>", retry_prompt)
        self.assertIn("22/11/2026", retry_prompt)
        self.assertIn("<rejected_answer>", retry_prompt)

    def test_a_blank_answer_counts_as_an_attempt(self):
        _, model, result = run(
            "customer",
            "meu pacote ABC123 não chegou",
            ["", customer_understand(), customer_respond()],
        )
        self.assertIsNone(result.failure)
        self.assertEqual(result.model_calls, 3)
        self.assertIn("empty", model.calls[1][1])

    def test_an_intent_outside_the_profile_is_rejected_then_fixed(self):
        wrong = {**customer_understand(), "intent": "occurrence"}
        _, model, result = run(
            "customer",
            "meu pacote ABC123 não chegou",
            [wrong, customer_understand(), customer_respond()],
        )
        self.assertIsNone(result.failure)
        self.assertIn("output.intent", model.calls[1][1])

    def test_an_invented_quote_is_rejected(self):
        wrong = customer_understand()
        wrong["fields"]["code"] = item("ABC123", "o código é ABC123 mesmo")
        _, model, result = run(
            "customer",
            "meu pacote ABC123 não chegou",
            [wrong, customer_understand(), customer_respond()],
        )
        self.assertIsNone(result.failure)
        self.assertIn("does not appear in the message", model.calls[1][1])

    def test_the_model_cannot_claim_to_have_registered_something(self):
        wrong = customer_respond(speech="Registrei o aviso de atraso do ABC123. Qual é o seu nome?")
        _, model, result = run(
            "customer",
            "meu pacote ABC123 não chegou",
            [customer_understand(), wrong, customer_respond()],
        )
        self.assertIsNone(result.failure)
        self.assertIn("cannot perform", model.calls[2][1])


class DisclosureFlowTests(unittest.TestCase):
    def test_the_customer_profile_cannot_reveal_the_name_or_address_from_the_base(self):
        leaking = customer_respond(
            speech=(
                "O pacote ABC123 está em nome de Maria Souza, na Rua das Flores, 123. "
                "Qual é o seu nome?"
            )
        )
        _, model, result = run(
            "customer",
            "meu pacote ABC123 não chegou",
            [customer_understand(), leaking, customer_respond()],
        )
        self.assertIsNone(result.failure)
        self.assertEqual(result.model_calls, 3)
        self.assertIn("reveals the source field", model.calls[2][1])

    def test_the_driver_profile_may_show_the_registered_address(self):
        scenario = load_scenario("driver")
        flow = Flow(LIBRARY, scenario.scripted_model(), DELIVERIES)
        result = flow.turn(flow.start("driver"), scenario.turns[0].user)
        self.assertIsNone(result.failure)
        self.assertIn("Rua das Flores, 123", result.speech)


class DriverConclusionTests(unittest.TestCase):
    def test_a_driver_case_cannot_end_with_a_plain_hand_off(self):
        scenario = load_scenario("driver")
        understand, respond = scenario.turns[0].model
        handing_off = {**respond, "next_action": "hand_off_to_team"}
        _, model, result = run("driver", scenario.turns[0].user, [understand, handing_off, respond])
        self.assertIsNone(result.failure)
        self.assertEqual(result.next_action, "escalate_to_human")
        self.assertIn("must conclude with 'escalate_to_human'", model.calls[2][1])


class AskedFieldsTests(unittest.TestCase):
    """Regression: only the fields the assistant really asked about count as asked."""

    OPERATOR_VAGUE = {
        "intent": "unclear",
        "fields": {"code": ABSENT, "description": ABSENT, "location": ABSENT, "time": ABSENT},
    }

    def operator_respond(self, asking, speech):
        return {
            "speech": speech,
            "facts": [],
            "asking": asking,
            "next_action": "ask_missing_information",
            "summary": "Mensagem sem detalhes da ocorrência.",
            "internal_note": {
                "priority": None,
                "priority_origin": "absent",
                "text": "Faltam dados.",
            },
        }

    def test_asking_only_for_the_code_does_not_mark_the_other_fields_as_asked(self):
        respond = self.operator_respond(["code"], "Qual é o código da entrega?")
        _, _, result = run("operator", "olá", [self.OPERATOR_VAGUE, respond])
        self.assertIsNone(result.failure)
        self.assertEqual(result.state.asked, ("code",))

    def test_asking_for_everything_in_one_question_marks_everything_as_asked(self):
        fields = ["code", "description", "location", "time"]
        respond = self.operator_respond(fields, "Qual o código, a descrição, o local e o horário?")
        _, _, result = run("operator", "olá", [self.OPERATOR_VAGUE, respond])
        self.assertEqual(result.state.asked, tuple(fields))

    def test_a_declaration_that_does_not_match_what_is_missing_is_rejected(self):
        wrong = self.operator_respond(["colour"], "Qual a cor?")
        right = self.operator_respond(["code"], "Qual é o código da entrega?")
        _, model, result = run("operator", "olá", [self.OPERATOR_VAGUE, wrong, right])
        self.assertIsNone(result.failure)
        self.assertEqual(result.model_calls, 3)
        self.assertIn("output.asking", model.calls[2][1])

    def test_a_reply_without_a_question_is_rejected_when_asking(self):
        no_question = self.operator_respond(["code"], "Preciso do código da entrega.")
        right = self.operator_respond(["code"], "Qual é o código da entrega?")
        _, model, result = run("operator", "olá", [self.OPERATOR_VAGUE, no_question, right])
        self.assertIsNone(result.failure)
        self.assertIn("must contain a question", model.calls[2][1])


class UnknownAnswerTests(unittest.TestCase):
    """'I do not know my code' is an explicit unknown, not an escalation."""

    CUSTOMER_UNKNOWN = {
        "intent": "delivery",
        "fields": {
            "code": item(None, "não sei meu código", "unknown"),
            "customer_name": item("Maria Souza", "Maria Souza"),
        },
    }

    def after_first_question(self):
        first = {"intent": "unclear", "fields": {"code": ABSENT, "customer_name": ABSENT}}
        asking = {
            "speech": "Qual é o código da entrega e o seu nome?",
            "facts": [],
            "asking": ["code", "customer_name"],
            "next_action": "ask_missing_information",
            "internal_note": {
                "priority": None,
                "priority_origin": "absent",
                "text": "Faltam dados.",
            },
        }
        flow = Flow(LIBRARY, ScriptedModel([first, asking]), DELIVERIES)
        return flow.turn(flow.start("customer"), "olá").state

    def respond(self, value):
        return {
            "speech": "Sem o código não consigo consultar. Vou encaminhar o caso para a equipe.",
            "facts": [{"field": "code", "value": value, "origin": "absent"}],
            "asking": [],
            "next_action": "hand_off_to_team",
            "internal_note": {
                "priority": None,
                "priority_origin": "absent",
                "text": "Cliente sem código.",
            },
        }

    def test_an_explicit_unknown_resolves_the_field_and_the_case_can_conclude(self):
        state = self.after_first_question()
        message = "eu não sei meu código, mas sou Maria Souza"
        _, _, result = run("customer", message, [self.CUSTOMER_UNKNOWN, self.respond(None)], state)
        self.assertIsNone(result.failure)
        self.assertEqual(result.next_action, "hand_off_to_team")
        self.assertTrue(result.state.field("code").unknown)

    def test_an_unknown_needs_a_real_quote(self):
        state = self.after_first_question()
        invented = {
            "intent": "delivery",
            "fields": {
                "code": item(None, "não faço ideia", "unknown"),
                "customer_name": item("Maria Souza", "Maria Souza"),
            },
        }
        message = "eu não sei meu código, mas sou Maria Souza"
        _, model, result = run(
            "customer", message, [invented, self.CUSTOMER_UNKNOWN, self.respond(None)], state
        )
        self.assertIsNone(result.failure)
        self.assertIn("does not appear in the message", model.calls[1][1])

    def test_placeholder_text_as_a_value_is_rejected_with_a_clear_error_then_fixed(self):
        state = self.after_first_question()
        message = "eu não sei meu código, mas sou Maria Souza"
        answers = [self.CUSTOMER_UNKNOWN, self.respond("não informado"), self.respond(None)]
        _, model, result = run("customer", message, answers, state)
        self.assertIsNone(result.failure)
        self.assertIn("placeholder text", model.calls[2][1])

    def test_the_summary_keeps_what_the_user_said_about_the_unknown_field(self):
        state = self.after_first_question()
        message = "eu não sei meu código, mas sou Maria Souza"
        _, _, result = run("customer", message, [self.CUSTOMER_UNKNOWN, self.respond(None)], state)
        stored = result.state.field("code")
        self.assertEqual(
            (stored.value, stored.quote, stored.origin), (None, "não sei meu código", "unknown")
        )


class RecordClaimFlowTests(unittest.TestCase):
    def test_the_assistant_cannot_say_it_prepared_a_record_when_nothing_is_handed_over(self):
        claims = customer_respond(
            speech=(
                "O prazo do ABC123 é 20/11/2026. Preparei o registro para a equipe. "
                "Qual é o seu nome?"
            )
        )
        _, model, result = run(
            "customer",
            "meu pacote ABC123 não chegou",
            [customer_understand(), claims, customer_respond()],
        )
        self.assertIsNone(result.failure)
        self.assertIn("does not hand the case over", model.calls[2][1])


class EscalationTests(unittest.TestCase):
    def test_after_three_rejected_answers_the_turn_escalates_to_a_person(self):
        wrong = customer_respond(speech="Seu pacote ABC123 chega em 22/11/2026. Qual é o seu nome?")
        flow, model, result = run(
            "customer", "meu pacote ABC123 não chegou", [customer_understand(), wrong, wrong, wrong]
        )
        self.assertEqual(result.failure, "validation_failed")
        self.assertTrue(result.escalated)
        self.assertIsNone(result.speech)
        self.assertEqual(result.next_action, "escalate_to_human")
        self.assertEqual(result.model_calls, 4)  # 1 understand + exactly 3 respond attempts
        self.assertTrue(result.errors)
        self.assertTrue(result.state.escalated)
        self.assertEqual(model.remaining, 0)

    def test_the_retry_limit_is_respected_even_if_the_model_keeps_failing(self):
        model = ScriptedModel(["not json"] * 50)
        flow = Flow(LIBRARY, model, DELIVERIES)
        result = flow.turn(flow.start("customer"), "oi")
        self.assertEqual(result.failure, "validation_failed")
        self.assertEqual(result.model_calls, 3)
        self.assertEqual(model.remaining, 47)

    def test_a_model_error_escalates_without_retrying(self):
        _, model, result = run("customer", "oi", [ModelError("service unavailable")])
        self.assertEqual(result.failure, "model_error")
        self.assertTrue(result.escalated)
        self.assertEqual(result.model_calls, 1)
        self.assertIn("service unavailable", result.errors[0])

    def test_a_failed_turn_does_not_lose_what_was_remembered(self):
        flow = Flow(LIBRARY, ScriptedModel([customer_understand(), customer_respond()]), DELIVERIES)
        first = flow.turn(flow.start("customer"), "meu pacote ABC123 não chegou")
        failing = Flow(LIBRARY, ScriptedModel([ModelError("down")]), DELIVERIES)
        second = failing.turn(first.state, "e agora?")
        self.assertEqual(second.state.field("code").value, "ABC123")
        self.assertTrue(second.state.escalated)
        self.assertEqual(second.state.last_next_action, "escalate_to_human")


class AskLimitTests(unittest.TestCase):
    """A field is asked at most twice; after that it is treated as unknown and never asked again."""

    PARTNER_UNDERSTAND = {
        "intent": "delivery",
        "fields": {
            "code": item("DEF456", "pacote DEF456"),
            "status": item("entregue", "entregue"),
            "moment": ABSENT,
        },
    }

    def ask(self, speech="Qual foi a data e a hora da entrega?"):
        return {
            "speech": speech,
            "facts": [],
            "asking": ["moment"],
            "next_action": "ask_missing_information",
        }

    def conclude(self):
        return {
            "speech": "Tudo bem, vou deixar a data e a hora da entrega como desconhecidas.",
            "facts": [],
            "asking": [],
            "next_action": "hand_off_to_team",
        }

    def first_turn_state(self):
        scenario = load_scenario("partner")
        flow = Flow(LIBRARY, scenario.scripted_model(), DELIVERIES)
        first = flow.turn(flow.start("partner"), scenario.turns[0].user)
        self.assertEqual(first.state.asked, ("moment",))
        self.assertEqual(first.state.times_asked("moment"), 1)
        return first.state

    def test_after_one_question_the_field_is_still_missing_and_may_be_asked_again(self):
        state = self.first_turn_state()
        _, _, result = run("partner", "não entendi", [self.PARTNER_UNDERSTAND, self.ask()], state)
        self.assertIsNone(result.failure)
        self.assertEqual(result.next_action, "ask_missing_information")
        self.assertEqual(result.state.times_asked("moment"), 2)

    def test_concluding_after_only_one_question_is_refused(self):
        state = self.first_turn_state()
        answers = [self.PARTNER_UNDERSTAND, self.conclude(), self.ask()]
        _, model, result = run("partner", "não entendi", answers, state)
        self.assertIsNone(result.failure)
        self.assertIn("required fields are missing", model.calls[2][1])

    def test_after_two_questions_the_field_is_unknown_and_asking_again_is_refused(self):
        state = self.first_turn_state()
        state = run("partner", "hm", [self.PARTNER_UNDERSTAND, self.ask()], state)[2].state
        answers = [self.PARTNER_UNDERSTAND, self.ask(), self.conclude()]
        _, model, result = run("partner", "ainda não sei", answers, state)
        self.assertIsNone(result.failure)
        self.assertEqual(result.next_action, "hand_off_to_team")
        self.assertIn("nothing is missing", model.calls[2][1])
        self.assertIn('"unknown": ["moment"]', model.calls[1][1])


class HandOffOnceTests(unittest.TestCase):
    """After a hand-off the assistant only answers, unless the user gives something new."""

    def handed_off_state(self):
        scenario = load_scenario("operator")
        flow = Flow(LIBRARY, scenario.scripted_model(), DELIVERIES)
        result = flow.turn(flow.start("operator"), scenario.turns[0].user)
        self.assertTrue(result.state.handed_off)
        return result.state

    def operator_respond(self, action):
        return {
            "speech": "A entrega XYZ789 segue em trânsito, com prazo em 18/11/2026.",
            "facts": [{"field": "status", "value": "in_transit", "origin": "base"}],
            "asking": [],
            "next_action": action,
            "summary": "Caminhão quebrou na BR-116 km 80.",
            "internal_note": {
                "priority": "high",
                "priority_origin": "inferred",
                "text": "XYZ789: caminhão quebrado. Prioridade alta (inferida).",
            },
        }

    def same_fields(self):
        return {
            "intent": "occurrence",
            "fields": {
                "code": item("XYZ789", "XYZ789"),
                "description": item("caminhão quebrou", "caminhão quebrou"),
                "location": item("BR-116 km 80", "BR-116 km 80"),
                "time": item("14h", "avisou 14h"),
            },
        }

    def test_a_second_hand_off_without_new_information_is_refused(self):
        state = self.handed_off_state()
        answers = [
            self.same_fields(),
            self.operator_respond("hand_off_to_team"),
            self.operator_respond("provide_information"),
        ]
        _, model, result = run("operator", "e o prazo dele?", answers, state)
        self.assertIsNone(result.failure)
        self.assertEqual(result.next_action, "provide_information")
        self.assertIn("already handed to the team", model.calls[2][1])

    def test_new_information_allows_a_new_hand_off(self):
        state = self.handed_off_state()
        updated = self.same_fields()
        updated["fields"]["time"] = item("15h", "agora são 15h")
        _, _, result = run(
            "operator", "agora são 15h", [updated, self.operator_respond("hand_off_to_team")], state
        )
        self.assertIsNone(result.failure)
        self.assertEqual(result.next_action, "hand_off_to_team")


class ProfileRulesInTheFlowTests(unittest.TestCase):
    def test_the_driver_must_state_the_registered_address(self):
        scenario = load_scenario("driver")
        understand, respond = scenario.turns[0].model
        without = {
            **respond,
            "speech": "Preparei o registro do problema de endereço do pacote ABC123.",
        }
        _, model, result = run("driver", scenario.turns[0].user, [understand, without, respond])
        self.assertIsNone(result.failure)
        self.assertIn("must state the registered address", model.calls[2][1])

    def test_the_partner_cannot_be_told_the_customer_name_or_address(self):
        scenario = load_scenario("partner")
        flow = Flow(LIBRARY, scenario.scripted_model(), DELIVERIES)
        first = flow.turn(flow.start("partner"), scenario.turns[0].user)
        understand, respond = scenario.turns[1].model
        leaking = {
            **respond,
            "speech": (
                "Entendi: o pacote DEF456 foi entregue em 13/11 às 9h. "
                "No sistema consta o cliente Carla Dias, na Rua C, 3."
            ),
        }
        _, model, result = run(
            "partner", scenario.turns[1].user, [understand, leaking, respond], first.state
        )
        self.assertIsNone(result.failure)
        self.assertIn("reveals the source field", model.calls[2][1])


class NoRepeatedQuestionTests(unittest.TestCase):
    def test_concluding_with_missing_fields_is_refused_the_first_time(self):
        understand = customer_understand()
        concludes = customer_respond(next_action="hand_off_to_team")
        _, model, result = run(
            "customer", "meu pacote ABC123 não chegou", [understand, concludes, customer_respond()]
        )
        self.assertIsNone(result.failure)
        self.assertIn("required fields are missing", model.calls[2][1])


if __name__ == "__main__":
    unittest.main()
