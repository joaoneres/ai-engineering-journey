"""Conversation memory: an immutable state, replaced by a new one at every turn.

Same idea as the immutable state of the earlier modules: functions return a new state and never
change the old one. The memory keeps only what is needed (the fields collected so far, which fields
were already asked and the last few turns), not the whole history.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace

MAX_RECENT_TURNS = 4


@dataclass(frozen=True)
class FieldValue:
    """A value collected from the user, with the quote that supports it."""

    value: str | None
    quote: str | None
    origin: str

    @property
    def present(self) -> bool:
        return self.value is not None and self.origin != "absent"


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
    asked: tuple[str, ...] = ()
    recent_turns: tuple[Turn, ...] = ()
    last_next_action: str | None = None
    extras: tuple[tuple[str, object], ...] = ()
    escalated: bool = False

    def field(self, name: str) -> FieldValue | None:
        return dict(self.fields).get(name)


def initial_state(profile_id: str) -> ConversationState:
    """An empty conversation for a profile."""
    return ConversationState(profile_id=profile_id)


def with_understanding(
    state: ConversationState, intent: str, answer_fields: Mapping[str, Mapping[str, object]]
) -> ConversationState:
    """Merge the fields of an `understand` answer. A value already known is never forgotten."""
    merged = dict(state.fields)
    for name, item in answer_fields.items():
        new = FieldValue(item["value"], item["quote"], item["origin"])
        if new.present or name not in merged:
            merged[name] = new
    keep_previous = intent == "unclear" and state.intent not in (None, "unclear")
    return replace(
        state, intent=state.intent if keep_previous else intent, fields=tuple(merged.items())
    )


def missing_fields(state: ConversationState, required: tuple[str, ...]) -> tuple[str, ...]:
    """Required fields that still have no value."""
    known = dict(state.fields)
    return tuple(name for name in required if name not in known or not known[name].present)


def unknown_after_asking(missing: tuple[str, ...], state: ConversationState) -> tuple[str, ...]:
    """Missing fields that were already asked once: they are treated as unknown, never re-asked."""
    return tuple(name for name in missing if name in state.asked)


def memory_texts(state: ConversationState) -> tuple[str, ...]:
    """User-written texts the model may quote from: stored values, quotes and recent messages."""
    texts = []
    for _, item in state.fields:
        if item.present:
            texts += [item.value, item.quote or ""]
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
        "unknown_after_asking": list(unknown),
        "already_asked": list(state.asked),
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
    """Record a finished turn."""
    asked = state.asked + tuple(name for name in newly_asked if name not in state.asked)
    turns = (*state.recent_turns, Turn(user, assistant))[-MAX_RECENT_TURNS:]
    return replace(
        state,
        asked=asked,
        recent_turns=turns,
        last_next_action=next_action,
        extras=tuple(extras.items()),
        escalated=state.escalated or next_action == "escalate_to_human",
    )


def escalated(state: ConversationState) -> ConversationState:
    """Mark the conversation as handed over to a person."""
    return replace(state, escalated=True, last_next_action="escalate_to_human")
