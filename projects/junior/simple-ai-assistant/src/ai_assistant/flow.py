"""The conversation flow: one turn in three steps, with guided retry and escalation.

    1. understand  (model)  -> intent and extracted fields, validated
    2. look up     (code)   -> exact search of the extracted code in the deliveries base
    3. respond     (model)  -> reply grounded in the message, the memory and the source, validated

Each model step is validated by the schema and the rubrics. If the answer is rejected, the model is
asked again with the exact errors, at most `max_attempts` times. If it never passes (or the model
fails), the turn ends in an escalation to a person. There is no unbounded loop.
"""

from collections.abc import Callable
from dataclasses import dataclass

from ai_assistant import assembly, memory, rubrics, schemas
from ai_assistant.deliveries import find_delivery
from ai_assistant.library import Library
from ai_assistant.memory import ConversationState
from ai_assistant.model import Model, ModelError

MAX_ATTEMPTS = 3
EXTRA_KEYS = ("summary", "internal_note", "record")


class TurnFailure(Exception):
    """A step could not produce a valid answer."""

    def __init__(self, code: str, errors: list[str]) -> None:
        super().__init__(code)
        self.code = code
        self.errors = errors


@dataclass(frozen=True)
class TurnResult:
    """What a turn produced. `speech` is None when the turn was escalated by a failure."""

    state: ConversationState
    speech: str | None
    next_action: str
    escalated: bool
    model_calls: int
    failure: str | None = None
    errors: tuple[str, ...] = ()


class Flow:
    """Runs conversation turns for any profile of the library."""

    def __init__(
        self,
        library: Library,
        model: Model,
        deliveries: dict[str, dict[str, str]],
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self.library = library
        self.model = model
        self.deliveries = deliveries
        self.max_attempts = max_attempts
        self._calls = 0

    def start(self, profile_id: str) -> ConversationState:
        """Begin an empty conversation for a profile."""
        if profile_id not in self.library.profiles:
            raise KeyError(f"unknown profile '{profile_id}'")
        return memory.initial_state(profile_id)

    def turn(self, state: ConversationState, message: str) -> TurnResult:
        """Run one turn. Never raises for model or validation problems: it escalates instead."""
        self._calls = 0
        try:
            return self._run(state, message)
        except TurnFailure as failure:
            return TurnResult(
                state=memory.escalated(state),
                speech=None,
                next_action="escalate_to_human",
                escalated=True,
                model_calls=self._calls,
                failure=failure.code,
                errors=tuple(failure.errors),
            )

    # --- the three steps ---------------------------------------------------------------------

    def _run(self, state: ConversationState, message: str) -> TurnResult:
        profile = self.library.profiles[state.profile_id]
        required = profile.required_fields

        # 1. understand
        evidence = rubrics.Evidence(message, memory.memory_texts(state))
        understood = self._ask(
            assembly.build_system(self.library, profile, assembly.UNDERSTAND),
            assembly.build_user(memory.memory_view(state, (), ()), message),
            lambda data: (
                schemas.understand_errors(data, self.library, profile)
                or rubrics.check_understand(data, evidence)
            ),
        )
        state = memory.with_understanding(state, understood["intent"], understood["fields"])

        # 2. look up (plain code, no model)
        code_field = state.field("code")
        code = code_field.value if code_field and code_field.present else None
        record = find_delivery(self.deliveries, code)

        # 3. respond
        missing_all = memory.missing_fields(state, required)
        unknown = memory.unknown_after_asking(missing_all, state)
        missing = tuple(name for name in missing_all if name not in unknown)
        evidence = rubrics.Evidence(message, memory.memory_texts(state), record)
        responded = self._ask(
            assembly.build_system(self.library, profile, assembly.RESPOND),
            assembly.build_user(
                memory.memory_view(state, missing, unknown),
                message,
                assembly.source_view(record, code),
            ),
            lambda data: (
                schemas.respond_errors(data, self.library, profile)
                or rubrics.check_respond(
                    data,
                    evidence,
                    intent=state.intent or "",
                    missing=missing,
                    hidden_fields=profile.hidden_fields,
                    conclude_with=profile.conclude_with,
                )
            ),
        )

        next_action = responded["next_action"]
        newly_asked = missing if next_action == "ask_missing_information" else ()
        extras = {key: responded[key] for key in EXTRA_KEYS if key in responded}
        state = memory.with_turn(
            state, message, responded["speech"], next_action, extras, newly_asked
        )
        return TurnResult(
            state=state,
            speech=responded["speech"],
            next_action=next_action,
            escalated=state.escalated,
            model_calls=self._calls,
        )

    def _ask(self, system: str, user: str, check: Callable[[dict], list[str]]) -> dict:
        """Ask the model; on rejection ask again with the exact errors, up to max_attempts."""
        prompt = user
        errors: list[str] = []
        for _ in range(self.max_attempts):
            self._calls += 1
            try:
                raw = self.model.complete(system, prompt)
            except ModelError as error:
                raise TurnFailure("model_error", [str(error)]) from error
            data, errors = schemas.parse_json(raw)
            if not errors:
                errors = check(data)
            if not errors:
                return data
            prompt = assembly.with_errors(user, raw if isinstance(raw, str) else "", errors)
        raise TurnFailure("validation_failed", errors)
