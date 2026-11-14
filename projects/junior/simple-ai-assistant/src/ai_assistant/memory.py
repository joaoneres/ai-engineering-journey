"""Conversation memory: an immutable state, replaced by a new one at every turn.

Same idea as the immutable state of the earlier modules: functions return a new state and never
change the old one. The memory keeps only what is needed: the fields collected so far, how many
times each field was asked, and the last few turns.

A required field is *resolved* when it has a value, when the user explicitly said they do not know
it (origin "unknown", with the quote), or when it was asked MAX_ASKS times without an answer.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace

MAX_RECENT_TURNS = 4
MAX_ASKS = 2


@dataclass(frozen=True)
class FieldValue:
    """A value collected from the user, with the quote that supports it."""

    value: str | None
    quote: str | None
    origin: str

    @property
    def present(self) -> bool:
        return self.value is not None and self.origin not in ("absent", "unknown")

    @property
    def unknown(self) -> bool:
        """The user said they do not know the value (or will not give it)."""
        return self.origin == "unknown"


@dataclass(frozen=True)
class Turn:
    """One exchange, kept short."""

    user: str
    assistant: str


@dataclass(frozen=True)
class ConversationState:
    """Everything the assistant remembers about the conversation."""

    profile_id: str
    intent: str | None = None
    fields: tuple[tuple[str, FieldValue], ...] = ()
    ask_counts: tuple[tuple[str, int], ...] = ()
    recent_turns: tuple[Turn, ...] = ()
    last_next_action: str | None = None
    extras: tuple[tuple[str, object], ...] = ()
    escalated: bool = False
    handed_off: bool = False

    def field(self, name: str) -> FieldValue | None:
        return dict(self.fields).get(name)

    @property
    def asked(self) -> tuple[str, ...]:
        """Names of the fields asked at least once."""
        return tuple(name for name, _ in self.ask_counts)

    def times_asked(self, name: str) -> int:
        return dict(self.ask_counts).get(name, 0)


def initial_state(profile_id: str) -> ConversationState:
    """An empty conversation for a profile."""
    return ConversationState(profile_id=profile_id)


def _is_new_information(old: FieldValue | None, new: FieldValue) -> bool:
    if new.present:
        return old is None or not old.present or old.value != new.value
    if new.unknown:
        return old is None or not (old.present or old.unknown)
    return False


def with_understanding(
    state: ConversationState, intent: str, answer_fields: Mapping[str, Mapping[str, object]]
) -> ConversationState:
    """Merge the fields of an `understand` answer.

    A known value is never forgotten and an "unknown" is not erased by a later "absent". New
    information (a new value or a new "unknown") allows a new hand-off to the team.
    """
    merged = dict(state.fields)
    new_information = False
    for name, item in answer_fields.items():
        new = FieldValue(item["value"], item["quote"], item["origin"])
        old = merged.get(name)
        if old is not None and (old.present or old.unknown) and not (new.present or new.unknown):
            continue
        if _is_new_information(old, new):
            new_information = True
        if old is None or new.present or new.unknown:
            merged[name] = new
    keep_previous = intent == "unclear" and state.intent not in (None, "unclear")
    return replace(
        state,
        intent=state.intent if keep_previous else intent,
        fields=tuple(merged.items()),
        handed_off=False if new_information else state.handed_off,
    )


def missing_fields(state: ConversationState, required: tuple[str, ...]) -> tuple[str, ...]:
    """Required fields that are still unresolved: no value and not declared unknown."""
    known = dict(state.fields)
    return tuple(
        name
        for name in required
        if name not in known or not (known[name].present or known[name].unknown)
    )


def unknown_fields(state: ConversationState, required: tuple[str, ...]) -> tuple[str, ...]:
    """Required fields the user said they do not know."""
    known = dict(state.fields)
    return tuple(name for name in required if name in known and known[name].unknown)


def unknown_after_asking(missing: tuple[str, ...], state: ConversationState) -> tuple[str, ...]:
    """Missing fields already asked MAX_ASKS times: they are treated as unknown, not asked again."""
    return tuple(name for name in missing if state.times_asked(name) >= MAX_ASKS)


def memory_texts(state: ConversationState) -> tuple[str, ...]:
    """User-written texts the model may quote from: stored values, quotes and recent messages."""
    texts = []
    for _, item in state.fields:
        if item.present:
            texts.append(item.value)
        if item.present or item.unknown:
            texts.append(item.quote or "")
    texts += [turn.user for turn in state.recent_turns]
    return tuple(text for text in texts if text)


def memory_view(
    state: ConversationState, missing: tuple[str, ...], unknown: tuple[str, ...]
) -> dict:
    """The compact memory shown to the model (only present fields, never the whole history)."""
    return {
        "intent": state.intent,
        "fields": {
            name: {"value": item.value, "quote": item.quote, "origin": item.origin}
            for name, item in state.fields
            if item.present
        },
        "missing": list(missing),
        "unknown": list(unknown),
        "already_asked": list(state.asked),
        "handed_off": state.handed_off,
        "recent_turns": [
            {"user": turn.user, "assistant": turn.assistant} for turn in state.recent_turns
        ],
    }


def with_turn(
    state: ConversationState,
    user: str,
    assistant: str,
    next_action: str,
    extras: Mapping[str, object],
    newly_asked: tuple[str, ...] = (),
) -> ConversationState:
    """Record a finished turn: count the questions asked and remember a hand-off."""
    counts = dict(state.ask_counts)
    for name in newly_asked:
        counts[name] = counts.get(name, 0) + 1
    turns = (*state.recent_turns, Turn(user, assistant))[-MAX_RECENT_TURNS:]
    return replace(
        state,
        ask_counts=tuple(counts.items()),
        recent_turns=turns,
        last_next_action=next_action,
        extras=tuple(extras.items()),
        escalated=state.escalated or next_action == "escalate_to_human",
        handed_off=state.handed_off or next_action == "hand_off_to_team",
    )


def escalated(state: ConversationState) -> ConversationState:
    """Mark the conversation as handed over to a person."""
    return replace(state, escalated=True, last_next_action="escalate_to_human")
