"""Settings from environment variables and an optional local `.env` file.

No third-party dependency: a tiny reader parses the `.env` file. A variable that is already set in
the environment always wins over the file. The API key is never shown by `repr()`.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ai_assistant.library import PROJECT_ROOT

ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_MODEL = "deepseek-flash"
DEFAULT_TIMEOUT = 30.0


class ConfigError(Exception):
    """A setting has an invalid value."""


@dataclass(frozen=True)
class Settings:
    """Everything the real model client needs. `api_key` is None when it was not configured."""

    api_key: str | None = field(repr=False)
    model: str = DEFAULT_MODEL
    timeout: float = DEFAULT_TIMEOUT
    thinking: bool = False


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Parse KEY=VALUE lines. Comments, blank lines and malformed lines are ignored."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}
    values = {}
    for line in text.splitlines():
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key.strip():
            values[key.strip()] = value
    return values


def _parse_switch(name: str, raw: str | None) -> bool:
    if raw is None or raw.strip().lower() in ("off", "false", "0", "no", "disabled"):
        return False
    if raw.strip().lower() in ("on", "true", "1", "yes", "enabled"):
        return True
    raise ConfigError(f"{name} must be on or off")


def load_settings(environ: Mapping[str, str] | None = None, env_file: Path = ENV_FILE) -> Settings:
    """Read the settings. The environment wins over the `.env` file; defaults fill the rest."""
    environ = os.environ if environ is None else environ
    file_values = read_env_file(env_file)

    def pick(name: str) -> str | None:
        return environ.get(name) or file_values.get(name) or None

    raw_timeout = pick("DEEPSEEK_TIMEOUT")
    try:
        timeout = float(raw_timeout) if raw_timeout else DEFAULT_TIMEOUT
    except ValueError as error:
        raise ConfigError("DEEPSEEK_TIMEOUT must be a number of seconds") from error
    if timeout <= 0:
        raise ConfigError("DEEPSEEK_TIMEOUT must be greater than zero")
    return Settings(
        api_key=pick("DEEPSEEK_API_KEY"),
        model=pick("DEEPSEEK_MODEL") or DEFAULT_MODEL,
        timeout=timeout,
        thinking=_parse_switch("DEEPSEEK_THINKING", pick("DEEPSEEK_THINKING")),
    )
