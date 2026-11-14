"""Loads and validates the prompt library: task prompts, profiles, global rules and vocabulary.

The library lives in plain TOML files so that prompts can be edited and versioned without touching
code. Every file is validated on load: an incomplete prompt or profile is refused with a message
that names the file and the problem.
"""

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TASK_IDS = (
    "classification",
    "extraction",
    "summarization",
    "internal_response",
    "text_transformation",
)
PROFILE_IDS = ("customer", "operator", "partner", "driver")
CORE_TASKS = ("classification", "extraction")
STAGES = ("understand", "respond")
EXAMPLE_TYPES = ("positive", "negative", "counterexample", "escalation")
ESCALATION_INTENT = "human_escalation"
UNCLEAR_INTENT = "unclear"
VOCABULARY_KEYS = ("intents", "origins", "priorities", "statuses", "next_actions")


class LibraryError(Exception):
    """The prompt library is missing, incomplete or inconsistent."""


@dataclass(frozen=True)
class Example:
    """One few-shot example of a task prompt."""

    type: str
    input: str
    output: dict
    note: str | None


@dataclass(frozen=True)
class Prompt:
    """A reusable task prompt."""

    id: str
    version: int
    stage: str
    objective: str
    context: str
    constraints: tuple[str, ...]
    criteria: tuple[str, ...]
    output_fields: tuple[str, ...]
    output_format: str
    examples: tuple[Example, ...]


@dataclass(frozen=True)
class Profile:
    """Who the user is: it composes the task prompts used in the conversation."""

    id: str
    role: str
    intents: tuple[str, ...]
    required_fields: tuple[str, ...]
    tasks: tuple[str, ...]


@dataclass(frozen=True)
class Vocabulary:
    """The closed lists of values the model is allowed to use."""

    intents: tuple[str, ...]
    origins: tuple[str, ...]
    priorities: tuple[str, ...]
    statuses: tuple[str, ...]
    next_actions: tuple[str, ...]


@dataclass(frozen=True)
class Library:
    """Everything the assistant needs to build prompts."""

    prompts: dict[str, Prompt]
    profiles: dict[str, Profile]
    rules: tuple[str, ...]
    vocabulary: Vocabulary

    def tasks_for(self, profile_id: str, stage: str) -> tuple[Prompt, ...]:
        """Return the prompts of the profile that belong to a stage, in library order."""
        profile = self.profiles[profile_id]
        return tuple(
            self.prompts[task_id]
            for task_id in TASK_IDS
            if task_id in profile.tasks and self.prompts[task_id].stage == stage
        )


# --- Low-level validation helpers -------------------------------------------------------------


def _read_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as file:
            return tomllib.load(file)
    except FileNotFoundError as error:
        raise LibraryError(f"{path.name}: file not found") from error
    except tomllib.TOMLDecodeError as error:
        raise LibraryError(f"{path.name}: invalid TOML ({error})") from error


def _text(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LibraryError(f"{where}: '{key}' is missing or empty")
    return value.strip()


def _text_list(data: dict, key: str, where: str) -> tuple[str, ...]:
    value = data.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise LibraryError(f"{where}: '{key}' must be a non-empty list of texts")
    return tuple(item.strip() for item in value)


# --- Prompts ----------------------------------------------------------------------------------


def _load_example(raw: object, where: str, output_fields: tuple[str, ...]) -> Example:
    if not isinstance(raw, dict):
        raise LibraryError(f"{where}: every example must be a table")
    example_type = _text(raw, "type", where)
    if example_type not in EXAMPLE_TYPES:
        raise LibraryError(f"{where}: unknown example type '{example_type}'")
    label = f"{where} example '{example_type}'"
    try:
        output = json.loads(_text(raw, "output", label))
    except json.JSONDecodeError as error:
        raise LibraryError(f"{label}: output is not valid JSON ({error})") from error
    if not isinstance(output, dict) or set(output) != set(output_fields):
        raise LibraryError(f"{label}: output keys must be exactly {list(output_fields)}")
    note = raw.get("note")
    return Example(example_type, _text(raw, "input", label), output, note.strip() if note else None)


def _load_prompt(path: Path) -> Prompt:
    data = _read_toml(path)
    where = path.name
    prompt_id = _text(data, "id", where)
    if prompt_id != path.stem:
        raise LibraryError(f"{where}: id '{prompt_id}' does not match the file name")
    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise LibraryError(f"{where}: 'version' must be an integer >= 1")
    stage = _text(data, "stage", where)
    if stage not in STAGES:
        raise LibraryError(f"{where}: 'stage' must be one of {list(STAGES)}")
    output_fields = _text_list(data, "output_fields", where)
    raw_examples = data.get("examples")
    if not isinstance(raw_examples, list) or not raw_examples:
        raise LibraryError(f"{where}: 'examples' is missing or empty")
    examples = tuple(_load_example(raw, where, output_fields) for raw in raw_examples)
    missing = [kind for kind in EXAMPLE_TYPES if kind not in {e.type for e in examples}]
    if missing:
        raise LibraryError(f"{where}: missing example types {missing}")
    return Prompt(
        id=prompt_id,
        version=version,
        stage=stage,
        objective=_text(data, "objective", where),
        context=_text(data, "context", where),
        constraints=_text_list(data, "constraints", where),
        criteria=_text_list(data, "criteria", where),
        output_fields=output_fields,
        output_format=_text(data, "output_format", where),
        examples=examples,
    )


# --- Global rules and vocabulary --------------------------------------------------------------


def _load_rules_and_vocabulary(path: Path) -> tuple[tuple[str, ...], Vocabulary]:
    data = _read_toml(path)
    where = path.name
    rules_table = data.get("rules")
    vocab_table = data.get("vocabulary")
    if not isinstance(rules_table, dict) or not isinstance(vocab_table, dict):
        raise LibraryError(f"{where}: needs the [rules] and [vocabulary] tables")
    rules = _text_list(rules_table, "items", f"{where} [rules]")
    values = {key: _text_list(vocab_table, key, f"{where} [vocabulary]") for key in VOCABULARY_KEYS}
    return rules, Vocabulary(**values)


# --- Profiles ---------------------------------------------------------------------------------


def _load_profile(path: Path, prompts: dict[str, Prompt], vocabulary: Vocabulary) -> Profile:
    data = _read_toml(path)
    where = path.name
    profile_id = _text(data, "id", where)
    if profile_id != path.stem:
        raise LibraryError(f"{where}: id '{profile_id}' does not match the file name")
    intents = _text_list(data, "intents", where)
    unknown = [intent for intent in intents if intent not in vocabulary.intents]
    if unknown:
        raise LibraryError(f"{where}: unknown intents {unknown}")
    if ESCALATION_INTENT not in intents:
        raise LibraryError(f"{where}: intents must include '{ESCALATION_INTENT}'")
    if UNCLEAR_INTENT in intents:
        raise LibraryError(f"{where}: '{UNCLEAR_INTENT}' is always allowed; do not list it")
    tasks = _text_list(data, "tasks", where)
    unknown_tasks = [task for task in tasks if task not in prompts]
    if unknown_tasks:
        raise LibraryError(f"{where}: unknown tasks {unknown_tasks}")
    if len(set(tasks)) != len(tasks):
        raise LibraryError(f"{where}: tasks must not repeat")
    missing_core = [task for task in CORE_TASKS if task not in tasks]
    if missing_core:
        raise LibraryError(f"{where}: tasks must include {missing_core}")
    return Profile(
        id=profile_id,
        role=_text(data, "role", where),
        intents=intents,
        required_fields=_text_list(data, "required_fields", where),
        tasks=tasks,
    )


# --- Entry point ------------------------------------------------------------------------------


def load_library(root: Path = PROJECT_ROOT) -> Library:
    """Load and validate the whole library from `root/prompts` and `root/profiles`."""
    root = Path(root)
    prompts = {task_id: _load_prompt(root / "prompts" / f"{task_id}.toml") for task_id in TASK_IDS}
    rules, vocabulary = _load_rules_and_vocabulary(root / "prompts" / "global_rules.toml")
    profiles = {
        profile_id: _load_profile(root / "profiles" / f"{profile_id}.toml", prompts, vocabulary)
        for profile_id in PROFILE_IDS
    }
    return Library(prompts=prompts, profiles=profiles, rules=rules, vocabulary=vocabulary)
