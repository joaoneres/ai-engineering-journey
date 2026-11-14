"""Terminal interface: a profile menu, then a conversation box with the assistant.

Run it with `python -m ai_assistant` (real conversation, needs DEEPSEEK_API_KEY) or with `--demo`
(replays the recorded scenarios, no key and no network). Input, output, style and the model are
injectable so the whole interface can be tested without a terminal.
"""

import argparse
import sys
from collections.abc import Callable, Sequence

from ai_assistant import ui_text
from ai_assistant.config import ConfigError, Settings, load_settings
from ai_assistant.deliveries import DeliveryDataError, load_deliveries
from ai_assistant.flow import Flow, TurnResult
from ai_assistant.library import PROFILE_IDS, Library, LibraryError, load_library
from ai_assistant.memory import ConversationState
from ai_assistant.model import DeepSeekClient, Model
from ai_assistant.scenarios import ScenarioError, load_scenario
from ai_assistant.ui_style import CLEAR_LINE, Style, detect_style

ModelFactory = Callable[[str], Model]
MENU_OPTIONS = {str(number): profile for number, profile in enumerate(PROFILE_IDS, start=1)}

# What a finished turn means for the conversation.
OPEN, ASK_MORE, END = "open", "ask_more", "end"


def _stdout_write(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


class Console:
    """Reads, prints and styles output, so tests can replace the terminal."""

    def __init__(
        self,
        input_fn: Callable[[str], str],
        print_fn: Callable[..., None],
        style: Style,
        write_fn: Callable[[str], None] = _stdout_write,
    ) -> None:
        self.input = input_fn
        self.print = print_fn
        self.style = style
        self._write = write_fn

    def working(self) -> None:
        """Show that the model is busy (only where the line can be redrawn)."""
        if self.style.interactive:
            self._write(self.style.paint(ui_text.WORKING, "dim"))

    def idle(self) -> None:
        """Erase the busy indicator."""
        if self.style.interactive:
            self._write(CLEAR_LINE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-assistant", description="FilaFácil assistant")
    parser.add_argument("--demo", action="store_true", help="replay the recorded scenarios")
    return parser


def _show_menu(console: Console) -> None:
    style = console.style
    console.print()
    console.print(style.paint(style.rule(ui_text.MENU_TITLE), "bold", "cyan"))
    console.print(ui_text.MENU_QUESTION)
    for number, profile in MENU_OPTIONS.items():
        console.print(f"  {style.paint(number, 'bold')}  {ui_text.PROFILE_LABELS[profile]}")
    console.print(f"  {style.paint('0', 'bold')}  {ui_text.MENU_EXIT}")


def _open_conversation(console: Console, profile_id: str, notice: str | None = None) -> None:
    style = console.style
    title = ui_text.CHAT_TITLE.format(profile=ui_text.PROFILE_LABELS[profile_id])
    console.print()
    console.print(style.paint(style.rule(title), "bold", "cyan"))
    console.print(style.paint(ui_text.CHAT_COMMANDS, "dim"))
    console.print(
        style.wrap(notice or ui_text.PRIVACY_NOTICE, painter=lambda t: style.paint(t, "yellow"))
    )


def _say(console: Console, speech: str) -> None:
    """The assistant's reply: wrapped, with a coloured label and blank lines around it."""
    style = console.style

    def painter(prefix: str) -> str:
        return style.paint(prefix, "bold", "green")

    console.print()
    console.print(style.wrap(speech, prefix=ui_text.ASSISTANT_PREFIX, painter=painter))
    console.print()


def _notice(console: Console, text: str, *styles: str) -> None:
    console.print(console.style.paint(text, *styles))


def _show_turn(console: Console, result: TurnResult, library: Library, profile_id: str) -> str:
    """Print the outcome of a turn and say whether the conversation goes on."""
    profile = library.profiles[profile_id]

    def summary() -> str:
        return ui_text.format_summary(result.state, profile, console.style)

    if result.failure:
        _say(console, ui_text.FAILED)
        console.print(summary())
        _notice(console, ui_text.ESCALATED, "bold", "yellow")
        return END
    _say(console, result.speech or "")
    if result.next_action == "escalate_to_human":
        console.print(summary())
        _notice(console, ui_text.ESCALATED, "bold", "yellow")
        return END
    if result.next_action == "close":
        console.print(summary())
        _notice(console, ui_text.CONCLUDED, "bold", "green")
        return END
    if result.next_action == "hand_off_to_team":
        console.print(summary())
        return ASK_MORE
    return OPEN


def _wants_to_continue(console: Console) -> bool:
    answer = console.input(ui_text.ASK_CONTINUE).strip().lower()
    return answer in ui_text.YES_ANSWERS


def _chat(console: Console, library: Library, flow: Flow, profile_id: str) -> None:
    profile = library.profiles[profile_id]
    _open_conversation(console, profile_id)
    state: ConversationState = flow.start(profile_id)
    while True:
        text = console.input(ui_text.USER_PROMPT).strip()
        if not text:
            continue
        if text == "/sair":
            return
        if text == "/novo":
            state = flow.start(profile_id)
            _notice(console, ui_text.NEW_CONVERSATION, "dim")
            continue
        if text == "/resumo":
            console.print(ui_text.format_summary(state, profile, console.style))
            continue
        console.working()
        result = flow.turn(state, text)
        console.idle()
        state = result.state
        outcome = _show_turn(console, result, library, profile_id)
        if outcome == END:
            return
        if outcome == ASK_MORE:
            if not _wants_to_continue(console):
                _notice(console, ui_text.CONCLUDED, "bold", "green")
                return
            _notice(console, ui_text.CONTINUE_HINT, "dim")


def _demo_runner(console: Console, library: Library, deliveries: dict) -> Callable[[str], None]:
    """Replays the recorded scenario of a profile through the real flow and validators."""

    def run(profile_id: str) -> None:
        scenario = load_scenario(profile_id)
        flow = Flow(library, scenario.scripted_model(), deliveries)
        _open_conversation(console, profile_id, ui_text.DEMO_BANNER)
        state = flow.start(profile_id)
        for turn in scenario.turns:
            console.print(console.style.wrap(turn.user, prefix=ui_text.USER_PROMPT))
            result = flow.turn(state, turn.user)
            state = result.state
            outcome = _show_turn(console, result, library, profile_id)
            if outcome == ASK_MORE:
                _notice(console, ui_text.CONCLUDED, "bold", "green")
            if outcome != OPEN:
                return

    return run


def _menu_loop(console: Console, run_profile: Callable[[str], None]) -> None:
    while True:
        _show_menu(console)
        choice = console.input(ui_text.MENU_PROMPT).strip()
        if choice == "0":
            console.print(ui_text.GOODBYE)
            return
        if choice in MENU_OPTIONS:
            run_profile(MENU_OPTIONS[choice])
            _notice(console, ui_text.BACK_TO_MENU, "dim")
        else:
            console.print(ui_text.INVALID_OPTION)


def _real_runner(
    console: Console,
    library: Library,
    deliveries: dict,
    settings: Settings,
    model_factory: ModelFactory | None,
) -> Callable[[str], None]:
    def run(profile_id: str) -> None:
        model = (
            model_factory(profile_id)
            if model_factory
            else DeepSeekClient(
                settings.api_key, settings.model, settings.timeout, thinking=settings.thinking
            )
        )
        _chat(console, library, Flow(library, model, deliveries), profile_id)

    return run


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[..., None] = print,
    write_fn: Callable[[str], None] = _stdout_write,
    style: Style | None = None,
    settings: Settings | None = None,
    model_factory: ModelFactory | None = None,
) -> int:
    """Run the interface. Returns the exit code: 0 ok, 1 error, 2 missing key."""
    args = build_parser().parse_args(argv)
    console = Console(input_fn, print_fn, style or detect_style(), write_fn)
    try:
        library, deliveries = load_library(), load_deliveries()
        if args.demo:
            run_profile = _demo_runner(console, library, deliveries)
        else:
            settings = settings or load_settings()
            if model_factory is None and not settings.api_key:
                console.print(ui_text.MISSING_KEY)
                return 2
            run_profile = _real_runner(console, library, deliveries, settings, model_factory)
        _menu_loop(console, run_profile)
        return 0
    except (LibraryError, DeliveryDataError, ScenarioError) as error:
        console.print(ui_text.LOAD_ERROR.format(detail=error))
        return 1
    except ConfigError as error:
        console.print(ui_text.SETTINGS_ERROR.format(detail=error))
        return 1
    except (EOFError, KeyboardInterrupt):
        console.print(f"\n{ui_text.GOODBYE}")
        return 0
    except Exception as error:  # the terminal never shows a traceback to the user
        console.print(ui_text.UNEXPECTED_ERROR.format(kind=type(error).__name__))
        return 1
