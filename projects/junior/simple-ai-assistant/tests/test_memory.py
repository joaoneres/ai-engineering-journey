import unittest

from ai_assistant import memory
from ai_assistant.memory import MAX_RECENT_TURNS


def item(value, quote, origin="informed"):
    return {"value": value, "quote": quote, "origin": origin}


ABSENT = item(None, None, "absent")


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.state = memory.initial_state("customer")

    def test_starts_empty(self):
        self.assertEqual(self.state.fields, ())
        self.assertIsNone(self.state.intent)
        self.assertFalse(self.state.escalated)

    def test_understanding_stores_fields_and_intent(self):
        state = memory.with_understanding(
            self.state,
            "delivery",
            {"code": item("ABC123", "pacote ABC123"), "customer_name": ABSENT},
        )
        self.assertEqual(state.intent, "delivery")
        self.assertEqual(state.field("code").value, "ABC123")
        self.assertFalse(state.field("customer_name").present)

    def test_the_previous_state_is_never_changed(self):
        memory.with_understanding(self.state, "delivery", {"code": item("ABC123", "ABC123")})
        self.assertEqual(self.state.fields, ())

    def test_a_known_value_is_not_forgotten_when_a_later_answer_says_absent(self):
        first = memory.with_understanding(
            self.state, "delivery", {"code": item("ABC123", "ABC123")}
        )
        second = memory.with_understanding(first, "delivery", {"code": ABSENT})
        self.assertEqual(second.field("code").value, "ABC123")

    def test_a_new_value_replaces_an_old_one(self):
        first = memory.with_understanding(
            self.state, "delivery", {"code": item("ABC123", "ABC123")}
        )
        second = memory.with_understanding(first, "delivery", {"code": item("XYZ789", "XYZ789")})
        self.assertEqual(second.field("code").value, "XYZ789")

    def test_missing_fields_are_the_required_ones_without_a_value(self):
        state = memory.with_understanding(
            self.state, "delivery", {"code": item("ABC123", "ABC123"), "customer_name": ABSENT}
        )
        self.assertEqual(
            memory.missing_fields(state, ("code", "customer_name")), ("customer_name",)
        )
        self.assertEqual(memory.missing_fields(state, ("code", "moment")), ("moment",))

    def test_unknown_after_asking_only_lists_fields_asked_before(self):
        state = memory.with_turn(
            self.state, "oi", "qual o nome?", "ask_missing_information", {}, ("customer_name",)
        )
        self.assertEqual(
            memory.unknown_after_asking(("customer_name", "code"), state), ("customer_name",)
        )

    def test_asked_fields_are_not_duplicated(self):
        state = memory.with_turn(self.state, "a", "b", "ask_missing_information", {}, ("code",))
        state = memory.with_turn(state, "c", "d", "ask_missing_information", {}, ("code", "moment"))
        self.assertEqual(state.asked, ("code", "moment"))

    def test_only_the_last_turns_are_kept(self):
        state = self.state
        for number in range(MAX_RECENT_TURNS + 3):
            state = memory.with_turn(
                state, f"user {number}", f"bot {number}", "provide_information", {}
            )
        self.assertEqual(len(state.recent_turns), MAX_RECENT_TURNS)
        self.assertEqual(state.recent_turns[-1].user, f"user {MAX_RECENT_TURNS + 2}")

    def test_memory_texts_hold_values_quotes_and_recent_messages(self):
        state = memory.with_understanding(
            self.state, "delivery", {"code": item("ABC123", "pacote ABC123")}
        )
        state = memory.with_turn(state, "meu pacote ABC123 sumiu", "ok", "provide_information", {})
        texts = memory.memory_texts(state)
        self.assertIn("ABC123", texts)
        self.assertIn("pacote ABC123", texts)
        self.assertIn("meu pacote ABC123 sumiu", texts)

    def test_memory_view_shows_only_present_fields_and_no_full_history(self):
        state = memory.with_understanding(
            self.state, "delivery", {"code": item("ABC123", "ABC123"), "customer_name": ABSENT}
        )
        view = memory.memory_view(state, ("customer_name",), ())
        self.assertEqual(list(view["fields"]), ["code"])
        self.assertEqual(view["missing"], ["customer_name"])

    def test_escalation_is_sticky(self):
        state = memory.with_turn(self.state, "a", "b", "escalate_to_human", {})
        self.assertTrue(state.escalated)
        state = memory.with_turn(state, "c", "d", "provide_information", {})
        self.assertTrue(state.escalated)


if __name__ == "__main__":
    unittest.main()
