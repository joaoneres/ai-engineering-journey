"""Terminal interface: a profile menu, then a conversation box with the assistant.

Run it with `python -m ai_assistant` (real conversation, needs DEEPSEEK_API_KEY) or with `--demo`
(replays the recorded scenarios, no key and no network). Input, output and the model are injectable
so the whole interface can be tested without a terminal.
"""

import argparse
from collections.abc import Callable, Sequence

from ai_assistant import ui_text
from ai_assistant.config import ConfigError, Settings, load_settings
from ai_assistant.deliveries import DeliveryDataError, load_deliveries
from ai_assistant.flow import Flow, TurnResult
from ai_assistant.library import PROFILE_IDS, Library, LibraryError, load_library
from ai_assistant.memory import ConversationState
from ai_assistant.model import DeepSeekClient, Model
from ai_assistant.scenarios import ScenarioError, load_scenario

ModelFactory = Callable[[str], Model]
MENU_OPTIONS = {str(number): profile for number, profile in enumerate(PROFILE_IDS, start=1)}


class Console:
    """Reads and prints, so tests can replace the terminal."""

    def __init__(self, input_fn: Callable[[str], str], print_fn: Callable[..., None]) -> None:
        self.input = input_fn
        self.print = print_fn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-assistant", description="FilaFácil assistant")
    parser.add_argument("--demo", action="store_true", help="replay the recorded scenarios")
    return parser


def _show_menu(console: Console) -> None:
    console.print(f"\n{ui_text.MENU_TITLE}\n{ui_text.MENU_QUESTION}")
    for number, profile in MENU_OPTIONS.items():
        console.print(f"{number}. {ui_text.PROFILE_LABELS[profile]}")
    console.print(f"0. {ui_text.MENU_EXIT}")


def _show_turn(console: Console, result: TurnResult, library: Library, profile_id: str) -> bool:
    """Print the outcome of a turn. Returns True when the conversation is over."""
    profile = library.profiles[profile_id]
    if result.failure:
        console.print(f"{ui_text.ASSISTANT_PREFIX}{ui_text.FAILED}")
    else:
        console.print(f"{ui_text.ASSISTANT_PREFIX}{result.speech}")
    if not (result.failure or result.next_action in ui_text.FINAL_ACTIONS):
        return False
    console.print(ui_text.format_summary(result.state, profile))
    console.print(ui_text.ESCALATED if result.escalated else ui_text.CONCLUDED)
    return True


def _chat(console: Console, library: Library, flow: Flow, profile_id: str) -> None:
    profile = library.profiles[profile_id]
    label = ui_text.PROFILE_LABELS[profile_id]
    console.print(f"\n{ui_text.CHAT_HEADER.format(profile=label)}\n{ui_text.PRIVACY_NOTICE}")
    state: ConversationState = flow.start(profile_id)
    while True:
        text = console.input(ui_text.USER_PROMPT).strip()
        if not text:
            continue
        if text == "/sair":
            return
        if text == "/novo":
            state = flow.start(profile_id)
            console.print(ui_text.NEW_CONVERSATION)
            continue
        if text == "/resumo":
            console.print(ui_text.format_summary(state, profile))
            continue
        result = flow.turn(state, text)
        state = result.state
        if _show_turn(console, result, library, profile_id):
            return


def _demo_runner(console: Console, library: Library, deliveries: dict) -> Callable[[str], None]:
    """Replays the recorded scenario of a profile through the real flow and validators."""

    def run(profile_id: str) -> None:
        scenario = load_scenario(profile_id)
        flow = Flow(library, scenario.scripted_model(), deliveries)
        label = ui_text.PROFILE_LABELS[profile_id]
        console.print(f"\n{ui_text.CHAT_HEADER.format(profile=label)}\n{ui_text.DEMO_BANNER}")
        state = flow.start(profile_id)
        for turn in scenario.turns:
            console.print(f"{ui_text.USER_PROMPT}{turn.user}")
            result = flow.turn(state, turn.user)
            state = result.state
            if _show_turn(console, result, library, profile_id):
                return

    return run


def _menu_loop(console: Console, library: Library, run_profile: Callable[[str], None]) -> None:
    while True:
        _show_menu(console)
        choice = console.input(ui_text.MENU_PROMPT).strip()
        if choice == "0":
            console.print(ui_text.GOODBYE)
            return
        if choice in MENU_OPTIONS:
            run_profile(MENU_OPTIONS[choice])
            console.print(ui_text.BACK_TO_MENU)
        else:
            console.print(ui_text.INVALID_OPTION)


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[..., None] = print,
    settings: Settings | None = None,
    model_factory: ModelFactory | None = None,
) -> int:
    """Run the interface. Returns the exit code: 0 ok, 1 error, 2 missing key."""
    args = build_parser().parse_args(argv)
    console = Console(input_fn, print_fn)
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
        _menu_loop(console, library, run_profile)
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
