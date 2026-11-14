"""The model interface and a scripted model for tests and the offline demo.

The flow only knows the `Model` protocol. The real client (DeepSeek) is added in a later phase and
plugs in through the same interface, so everything else can be tested without network or cost.
"""

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from typing import Protocol

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MAX_TOKENS = 4096

Transport = Callable[[str, dict[str, str], bytes, float], bytes]


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


def http_post(url: str, headers: dict[str, str], body: bytes, timeout: float) -> bytes:
    """The real transport. Errors are turned into ModelError without echoing request details."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        hint = " (check DEEPSEEK_API_KEY)" if error.code in (401, 403) else ""
        raise ModelError(f"the model service answered HTTP {error.code}{hint}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ModelError("could not reach the model service") from None


class DeepSeekClient:
    """Calls the DeepSeek chat API (OpenAI-compatible) in JSON mode, with the standard library only.

    The transport is injectable, so tests never need the network. The API key is only placed in the
    Authorization header; it never appears in `repr()` or in any error message.
    """

    def __init__(
        self,
        api_key: str | None,
        model: str = "deepseek-flash",
        timeout: float = 30.0,
        transport: Transport = http_post,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        url: str = API_URL,
        thinking: bool = False,
    ) -> None:
        if not api_key:
            raise ModelError("DEEPSEEK_API_KEY is not set")
        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.url = url
        self.thinking = thinking
        self._transport = transport

    def __repr__(self) -> str:
        return f"DeepSeekClient(model={self.model!r})"

    def complete(self, system: str, user: str) -> str:
        """Send one chat request and return the message content ("" if the service sent none)."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.max_tokens,
            # Reasoning is off by default: these are structured tasks, and reasoning tokens eat the
            # max_tokens budget (a cut-off answer comes back blank in JSON mode). Temperature only
            # applies when thinking is off.
            "thinking": {"type": "enabled" if self.thinking else "disabled"},
            "temperature": 0,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        raw = self._transport(
            self.url, headers, json.dumps(payload, ensure_ascii=False).encode("utf-8"), self.timeout
        )
        try:
            content = json.loads(raw)["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise ModelError("the model service returned an unexpected response") from None
        return content or ""
