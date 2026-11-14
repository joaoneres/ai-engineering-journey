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

    def test_a_vague_message_does_not_erase_a_known_intent(self):
        first = memory.with_understanding(self.state, "occurrence", {"code": ABSENT})
        second = memory.with_understanding(first, "unclear", {"code": item("JKL654", "JKL654")})
        self.assertEqual(second.intent, "occurrence")

    def test_unclear_is_kept_when_nothing_better_is_known(self):
        state = memory.with_understanding(self.state, "unclear", {"code": ABSENT})
        self.assertEqual(state.intent, "unclear")

    def test_a_specific_intent_replaces_unclear_and_a_new_specific_one_replaces_the_old(self):
        state = memory.with_understanding(self.state, "unclear", {"code": ABSENT})
        state = memory.with_understanding(state, "delivery", {"code": ABSENT})
        self.assertEqual(state.intent, "delivery")
        state = memory.with_understanding(state, "human_escalation", {"code": ABSENT})
        self.assertEqual(state.intent, "human_escalation")

    def test_escalating_records_the_escalation_as_the_last_action(self):
        state = memory.with_turn(self.state, "a", "b", "ask_missing_information", {})
        self.assertEqual(memory.escalated(state).last_next_action, "escalate_to_human")
        self.assertTrue(memory.escalated(state).escalated)

    def test_missing_fields_are_the_required_ones_without_a_value(self):
        state = memory.with_understanding(
            self.state, "delivery", {"code": item("ABC123", "ABC123"), "customer_name": ABSENT}
        )
        self.assertEqual(
            memory.missing_fields(state, ("code", "customer_name")), ("customer_name",)
        )
        self.assertEqual(memory.missing_fields(state, ("code", "moment")), ("moment",))

    def test_a_field_asked_once_is_still_open_and_asked_twice_is_given_up(self):
        once = memory.with_turn(
            self.state, "oi", "nome?", "ask_missing_information", {}, ("customer_name",)
        )
        self.assertEqual(memory.unknown_after_asking(("customer_name", "code"), once), ())
        twice = memory.with_turn(
            once, "hm", "nome?", "ask_missing_information", {}, ("customer_name",)
        )
        self.assertEqual(
            memory.unknown_after_asking(("customer_name", "code"), twice), ("customer_name",)
        )
        self.assertEqual(twice.times_asked("customer_name"), 2)

    def test_an_explicit_unknown_resolves_the_field_and_keeps_the_quote(self):
        state = memory.with_understanding(
            self.state, "delivery", {"code": item(None, "não sei meu código", "unknown")}
        )
        self.assertEqual(memory.missing_fields(state, ("code",)), ())
        self.assertEqual(memory.unknown_fields(state, ("code",)), ("code",))
        self.assertIn("não sei meu código", memory.memory_texts(state))
        self.assertFalse(state.field("code").present)

    def test_a_later_absent_does_not_erase_an_unknown_but_a_value_replaces_it(self):
        unknown = memory.with_understanding(
            self.state, "delivery", {"code": item(None, "não sei meu código", "unknown")}
        )
        still = memory.with_understanding(unknown, "delivery", {"code": ABSENT})
        self.assertTrue(still.field("code").unknown)
        found = memory.with_understanding(still, "delivery", {"code": item("ABC123", "ABC123")})
        self.assertEqual(found.field("code").value, "ABC123")
        self.assertEqual(memory.unknown_fields(found, ("code",)), ())

    def test_a_hand_off_is_remembered_and_new_information_reopens_it(self):
        state = memory.with_understanding(
            self.state, "delivery", {"code": item("ABC123", "ABC123")}
        )
        state = memory.with_turn(state, "a", "b", "hand_off_to_team", {})
        self.assertTrue(state.handed_off)
        same = memory.with_understanding(state, "delivery", {"code": item("ABC123", "ABC123")})
        self.assertTrue(same.handed_off)
        new = memory.with_understanding(state, "delivery", {"code": item("XYZ789", "XYZ789")})
        self.assertFalse(new.handed_off)

    def test_the_memory_view_tells_the_model_about_unknown_fields_and_the_hand_off(self):
        view = memory.memory_view(self.state, ("code",), ("customer_name",))
        self.assertEqual(view["unknown"], ["customer_name"])
        self.assertFalse(view["handed_off"])

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
