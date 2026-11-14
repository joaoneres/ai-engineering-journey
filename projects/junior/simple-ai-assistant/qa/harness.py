"""Harness for the manual test map: runs a conversation with the real model and checks it.

Each check returns None when it passes or a short message when it fails. Checks look at invariants
(what must and must never happen), not at exact wording, because a language model phrases things
differently on every run.
"""

import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from ai_assistant.config import load_settings
from ai_assistant.deliveries import load_deliveries
from ai_assistant.flow import Flow, TurnResult
from ai_assistant.library import load_library
from ai_assistant.memory import ConversationState
from ai_assistant.model import DeepSeekClient

LIBRARY = load_library()
DELIVERIES = load_deliveries()
SETTINGS = load_settings()


def norm(text: str) -> str:
    return " ".join((text or "").lower().split())


@dataclass
class TurnLog:
    message: str
    result: TurnResult

    @property
    def speech(self) -> str:
        return self.result.speech or ""


@dataclass
class Run:
    turns: list[TurnLog] = field(default_factory=list)
    state: ConversationState | None = None

    def speech(self, index: int) -> str:
        return norm(self.turns[index].speech)

    def extras(self) -> dict:
        return dict(self.state.extras) if self.state else {}

    def all_text(self) -> str:
        parts = [turn.speech for turn in self.turns]
        extras = self.extras()
        if "summary" in extras:
            parts.append(extras["summary"])
        if "internal_note" in extras:
            parts.append(extras["internal_note"]["text"])
        return norm(" ".join(parts))

    def calls(self) -> int:
        return sum(turn.result.model_calls for turn in self.turns)


Check = Callable[[Run], str | None]


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    profile: str
    messages: tuple[str, ...]
    expectation: str
    checks: tuple[Check, ...]
    note: str = ""


def execute(case: Case) -> Run:
    """One real conversation."""
    client = DeepSeekClient(
        SETTINGS.api_key, SETTINGS.model, SETTINGS.timeout, thinking=SETTINGS.thinking
    )
    flow = Flow(LIBRARY, client, DELIVERIES)
    state = flow.start(case.profile)
    run = Run()
    for message in case.messages:
        result = flow.turn(state, message)
        state = result.state
        run.turns.append(TurnLog(message, result))
    run.state = state
    return run


def evaluate(case: Case, run: Run) -> list[str]:
    failures = []
    for index, turn in enumerate(run.turns):
        if turn.result.failure:
            failures.append(f"turno {index + 1}: falha do fluxo ({turn.result.failure})")
    failures += [message for check in case.checks if (message := check(run))]
    return failures


@dataclass
class CaseResult:
    case: Case
    runs: int
    passed: int
    failures: list[list[str]]
    samples: list[Run]
    calls: int

    @property
    def ok(self) -> bool:
        return self.passed == self.runs


def run_case(case: Case, runs: int) -> CaseResult:
    logs, failures, passed = [], [], 0
    for _ in range(runs):
        run = execute(case)
        problems = evaluate(case, run)
        logs.append(run)
        failures.append(problems)
        passed += not problems
    return CaseResult(case, runs, passed, failures, logs, sum(r.calls() for r in logs))


def run_all(cases: list[Case], runs: int, workers: int = 8) -> list[CaseResult]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda case: run_case(case, runs), cases))


# --- Checks ---------------------------------------------------------------------------------


def _scope(run: Run, turn: int | None) -> str:
    return run.all_text() if turn is None else run.speech(turn)


def says(*needles: str, turn: int | None = None, any_of: bool = False) -> Check:
    """The text (a turn's reply, or everything) must contain the needles (all, or any)."""

    def check(run: Run) -> str | None:
        text = _scope(run, turn)
        found = [n for n in needles if norm(n) in text]
        if (any_of and found) or (not any_of and len(found) == len(needles)):
            return None
        where = "a resposta" if turn is not None else "o texto"
        connector = " ou " if any_of else " e "
        return f"{where} deveria conter {connector.join(repr(n) for n in needles)}"

    return check


def never_says(*needles: str, turn: int | None = None) -> Check:
    def check(run: Run) -> str | None:
        text = _scope(run, turn)
        found = [n for n in needles if norm(n) in text]
        return f"não deveria conter {found}" if found else None

    return check


def never_matches(pattern: str, turn: int | None = None, label: str = "") -> Check:
    def check(run: Run) -> str | None:
        match = re.search(pattern, _scope(run, turn))
        return (
            f"não deveria conter {label or pattern!r} (achou {match.group(0)!r})" if match else None
        )

    return check


def action_is(turn: int, *allowed: str) -> Check:
    def check(run: Run) -> str | None:
        actual = run.turns[turn].result.next_action
        return (
            None if actual in allowed else f"turno {turn + 1}: ação {actual!r}, esperado {allowed}"
        )

    return check


def escalated() -> Check:
    def check(run: Run) -> str | None:
        last = run.turns[-1].result
        if last.escalated and last.next_action == "escalate_to_human":
            return None
        return (
            f"deveria encaminhar para humano (ação {last.next_action!r}, escalou={last.escalated})"
        )

    return check


def intent_is(*allowed: str) -> Check:
    def check(run: Run) -> str | None:
        intent = run.state.intent if run.state else None
        return None if intent in allowed else f"intenção {intent!r}, esperado {allowed}"

    return check


def field_is(name: str, predicate: Callable[[str], bool], description: str) -> Check:
    def check(run: Run) -> str | None:
        item = run.state.field(name) if run.state else None
        if item is None or not item.present or not predicate(item.value):
            shown = item.value if item and item.present else None
            return f"campo {name}: {shown!r}, esperado {description}"
        return None

    return check


def field_not_present(name: str) -> Check:
    def check(run: Run) -> str | None:
        item = run.state.field(name) if run.state else None
        if item is not None and item.present:
            return f"campo {name} não deveria ter valor (tem {item.value!r})"
        return None

    return check


def field_unknown(name: str) -> Check:
    def check(run: Run) -> str | None:
        item = run.state.field(name) if run.state else None
        return (
            None
            if item is not None and item.unknown
            else f"campo {name} deveria ser 'desconhecido'"
        )

    return check


def asked(*names: str) -> Check:
    def check(run: Run) -> str | None:
        done = set(run.state.asked) if run.state else set()
        missing = [n for n in names if n not in done]
        return f"deveria ter perguntado por {missing}" if missing else None

    return check


def asked_times(name: str, times: int) -> Check:
    def check(run: Run) -> str | None:
        actual = run.state.times_asked(name) if run.state else 0
        return None if actual == times else f"{name} perguntado {actual}x, esperado {times}x"

    return check


def priority_is(priority: str) -> Check:
    def check(run: Run) -> str | None:
        note = run.extras().get("internal_note")
        if note and note["priority"] == priority and note["priority_origin"] == "inferred":
            return None
        shown = (note["priority"], note["priority_origin"]) if note else None
        return f"prioridade {shown}, esperado {priority!r} inferida"

    return check


def has_extra(name: str) -> Check:
    def check(run: Run) -> str | None:
        return None if name in run.extras() else f"deveria ter {name!r} no registro"

    return check


def reply_has_question(turn: int) -> Check:
    def check(run: Run) -> str | None:
        return (
            None if "?" in run.turns[turn].speech else f"turno {turn + 1}: sem pergunta na resposta"
        )

    return check


NOT_FOUND = ("não encontr", "não consegui encontrar", "não localiz", "não consegui localizar")
