"""The model interface and a scripted model for tests and the offline demo.

The flow only knows the `Model` protocol. The real client (DeepSeek) is added in a later phase and
plugs in through the same interface, so everything else can be tested without network or cost.
"""

import json
from collections.abc import Iterable
from typing import Protocol


class ModelError(Exception):
    """The model could not be reached or answered with an error."""


class Model(Protocol):
    """Anything that can answer a system prompt and a user prompt with text."""

    def complete(self, system: str, user: str) -> str: ...


class ScriptedModel:
    """Answers with pre-recorded responses, in order. Used only by tests and `--demo`."""

    def __init__(self, responses: Iterable[str | dict | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if not self._responses:
            raise ModelError("the scripted model has no more responses")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)

    @property
    def remaining(self) -> int:
        return len(self._responses)
