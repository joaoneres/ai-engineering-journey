import unittest

from ai_assistant import ui_text
from ai_assistant.cli import main
from ai_assistant.config import Settings
from ai_assistant.model import ModelError, ScriptedModel
from ai_assistant.scenarios import load_scenario
from ai_assistant.ui_style import CLEAR_LINE, Style


class Terminal:
    """A fake terminal: feeds scripted input lines and records everything printed."""

    def __init__(self, lines):
        self.lines = iter(lines)
        self.out = []

    def input(self, prompt=""):
        self.out.append(prompt)
        try:
            return next(self.lines)
        except StopIteration:
            raise EOFError from None

    def print(self, *parts):
        self.out.append(" ".join(str(part) for part in parts))

    def write(self, text):
        self.out.append(text)

    @property
    def text(self):
        return "\n".join(self.out)


def run(lines, argv=(), settings=None, model_factory=None, style=None, terminal=None):
    terminal = terminal or Terminal(lines)
    code = main(
        list(argv),
        input_fn=terminal.input,
        print_fn=terminal.print,
        write_fn=terminal.write,
        style=style or Style(),
        settings=settings,
        model_factory=model_factory,
    )
    return code, terminal.text


def customer_model(_profile):
    return load_scenario("customer").scripted_model()


class MenuTests(unittest.TestCase):
    def test_the_menu_lists_the_four_profiles_and_exits_with_zero(self):
        code, text = run(["0"], ["--demo"])
        self.assertEqual(code, 0)
        for label in ("Cliente", "Operador", "Parceiro", "Motorista", ui_text.MENU_QUESTION):
            self.assertIn(label, text)
        self.assertIn(ui_text.GOODBYE, text)

    def test_an_invalid_option_is_explained_and_the_menu_returns(self):
        code, text = run(["9", "abc", "0"], ["--demo"])
        self.assertEqual(code, 0)
        self.assertEqual(text.count(ui_text.INVALID_OPTION), 2)


class DemoModeTests(unittest.TestCase):
    def test_each_profile_replays_its_scenario_and_ends_with_a_structured_record(self):
        for option, label in (
            ("1", "Cliente"),
            ("2", "Operador"),
            ("3", "Parceiro"),
            ("4", "Motorista"),
        ):
            code, text = run([option, "0"], ["--demo"])
            self.assertEqual(code, 0, label)
            self.assertIn(f"Conversa: {label}", text)
            self.assertIn(ui_text.DEMO_BANNER, text)
            self.assertIn(ui_text.SUMMARY_TITLE, text)
            self.assertNotIn("Traceback", text)

    def test_the_customer_demo_shows_the_conversation_and_the_record(self):
        _, text = run(["1", "0"], ["--demo"])
        self.assertIn("Você: meu pacote ABC123 não chegou", text)
        self.assertIn("IA:   Localizei o pacote ABC123", text)
        self.assertIn("Nome do cliente: Maria Souza (informado)", text)
        self.assertIn("Próxima ação: Repassar à equipe", text)

    def test_the_driver_demo_is_escalated_to_a_person(self):
        _, text = run(["4", "0"], ["--demo"])
        self.assertIn(ui_text.ESCALATED, text)
        self.assertIn("Registro padronizado:", text)

    def test_the_demo_needs_no_key(self):
        code, _ = run(["0"], ["--demo"], settings=Settings(api_key=None))
        self.assertEqual(code, 0)


class MissingKeyTests(unittest.TestCase):
    def test_without_a_key_and_without_demo_it_explains_how_to_configure_and_exits_with_2(self):
        code, text = run(["0"], settings=Settings(api_key=None))
        self.assertEqual(code, 2)
        self.assertIn("DEEPSEEK_API_KEY", text)
        self.assertIn("--demo", text)
        self.assertNotIn(ui_text.MENU_TITLE, text)


class ChatTests(unittest.TestCase):
    def chat(self, lines):
        return run(["1", *lines, "0"], model_factory=customer_model, settings=Settings(api_key="x"))

    def test_the_privacy_notice_is_shown_when_a_conversation_opens(self):
        _, text = self.chat(["/sair"])
        self.assertIn(" ".join(ui_text.PRIVACY_NOTICE.split()), " ".join(text.split()))

    def test_a_conversation_runs_turn_by_turn_and_asks_before_closing(self):
        code, text = self.chat(["meu pacote ABC123 não chegou", "Maria Souza, sim", "n"])
        flat = " ".join(text.split())
        self.assertEqual(code, 0)
        self.assertIn("qual é o seu nome?", flat)
        self.assertIn(ui_text.SUMMARY_TITLE, flat)
        self.assertIn(ui_text.ASK_CONTINUE.strip(), flat)
        self.assertIn(ui_text.CONCLUDED, flat)
        self.assertIn(ui_text.BACK_TO_MENU, flat)

    def test_answering_yes_keeps_the_conversation_open(self):
        _, text = self.chat(["meu pacote ABC123 não chegou", "Maria Souza, sim", "s", "/sair"])
        self.assertIn(ui_text.CONTINUE_HINT, text)
        self.assertNotIn(ui_text.CONCLUDED, text)
        self.assertEqual(text.count(ui_text.ASK_CONTINUE), 1)

    def test_after_a_yes_a_new_case_can_be_started(self):
        lines = [
            "meu pacote ABC123 não chegou",
            "Maria Souza, sim",
            "sim",
            "/novo",
            "/resumo",
            "/sair",
        ]
        _, text = self.chat(lines)
        self.assertIn(ui_text.NEW_CONVERSATION, text)
        self.assertIn(ui_text.SUMMARY_EMPTY, text)

    def test_blank_lines_are_ignored(self):
        _, text = self.chat(["", "   ", "/sair"])
        self.assertNotIn(ui_text.ASSISTANT_PREFIX, text)

    def test_summary_is_empty_at_first_and_filled_after_a_turn(self):
        _, text = self.chat(["/resumo", "meu pacote ABC123 não chegou", "/resumo", "/sair"])
        self.assertIn(ui_text.SUMMARY_EMPTY, text)
        self.assertIn("Código: ABC123 (informado)", text)
        self.assertIn("Nome do cliente: ausente", text)

    def test_new_starts_over_and_forgets_the_memory(self):
        _, text = self.chat(["meu pacote ABC123 não chegou", "/novo", "/resumo", "/sair"])
        self.assertIn(ui_text.NEW_CONVERSATION, text)
        self.assertTrue(text.rstrip().count(ui_text.SUMMARY_EMPTY) >= 1)

    def test_leave_returns_to_the_menu_and_the_app_keeps_running(self):
        code, text = self.chat(["/sair"])
        self.assertEqual(code, 0)
        self.assertEqual(text.count(ui_text.MENU_TITLE), 2)

    def test_end_of_input_inside_a_conversation_exits_gracefully(self):
        code, text = run(["1"], model_factory=customer_model, settings=Settings(api_key="x"))
        self.assertEqual(code, 0)
        self.assertIn(ui_text.GOODBYE, text)
        self.assertNotIn("Traceback", text)


class ClosingTests(unittest.TestCase):
    """Escalations and an explicit close end the chat; a plain hand-off asks first."""

    def test_the_driver_escalation_ends_without_asking_to_continue(self):
        def driver_model(_profile):
            return load_scenario("driver").scripted_model()

        message = load_scenario("driver").turns[0].user
        _, text = run(
            ["4", message, "0"], model_factory=driver_model, settings=Settings(api_key="x")
        )
        self.assertIn(ui_text.ESCALATED, text)
        self.assertNotIn(ui_text.ASK_CONTINUE, text)

    def test_the_demo_never_asks_to_continue(self):
        _, text = run(["1", "0"], ["--demo"])
        self.assertNotIn(ui_text.ASK_CONTINUE, text)
        self.assertIn(ui_text.CONCLUDED, text)


class BusyIndicatorTests(unittest.TestCase):
    def run_one_turn(self, style):
        terminal = Terminal(["1", "meu pacote ABC123 não chegou", "/sair", "0"])
        run(
            [],
            model_factory=customer_model,
            settings=Settings(api_key="x"),
            style=style,
            terminal=terminal,
        )
        return terminal.text

    def test_no_indicator_when_the_output_cannot_be_redrawn(self):
        self.assertNotIn(ui_text.WORKING, self.run_one_turn(Style(interactive=False)))

    def test_the_indicator_is_shown_and_erased_on_an_interactive_terminal(self):
        text = self.run_one_turn(Style(color=True, interactive=True, width=80))
        self.assertIn(ui_text.WORKING, text)
        self.assertIn(CLEAR_LINE, text)
        self.assertLess(text.index(ui_text.WORKING), text.index(CLEAR_LINE))

    def test_colours_appear_only_when_the_style_asks_for_them(self):
        self.assertNotIn("\033[", self.run_one_turn(Style(color=False)))
        self.assertIn("\033[", self.run_one_turn(Style(color=True, interactive=True)))


class SummaryFormatTests(unittest.TestCase):
    def test_an_undefined_priority_is_shown_without_redundancy(self):
        from ai_assistant import memory
        from ai_assistant.library import load_library

        library = load_library()
        state = memory.initial_state("customer")
        state = memory.with_turn(
            state,
            "oi",
            "ok",
            "provide_information",
            {
                "internal_note": {
                    "priority": None,
                    "priority_origin": "absent",
                    "text": "Faltam dados.",
                }
            },
        )
        text = ui_text.format_summary(state, library.profiles["customer"])
        self.assertIn("prioridade não definida", text)
        self.assertNotIn("(ausente)", text)


class FailureTests(unittest.TestCase):
    def test_a_model_failure_is_explained_without_a_traceback_and_hands_over_to_a_person(self):
        def failing(_profile):
            return ScriptedModel([ModelError("could not reach the model service")])

        code, text = run(["1", "oi", "0"], model_factory=failing, settings=Settings(api_key="x"))
        self.assertEqual(code, 0)
        self.assertIn(ui_text.FAILED, text)
        self.assertIn(ui_text.ESCALATED, text)
        self.assertNotIn("Traceback", text)
        self.assertNotIn("could not reach", text)  # internal detail is not shown to the user

    def test_an_unexpected_bug_never_shows_a_traceback(self):
        def broken(_profile):
            raise RuntimeError("boom")

        code, text = run(["1", "0"], model_factory=broken, settings=Settings(api_key="x"))
        self.assertEqual(code, 1)
        self.assertIn("RuntimeError", text)
        self.assertNotIn("Traceback", text)


if __name__ == "__main__":
    unittest.main()
