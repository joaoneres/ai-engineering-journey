"""Output schemas and a small validator for the json the model returns at each stage.

Structure only: required keys, types and allowed values. Whether the content is grounded in the
message, the memory and the source record is checked by `rubrics.py`.

A turn has two stages:
    understand -> {"intent": ..., "fields": {...}}
    respond    -> {"speech": ..., "facts": [...], "next_action": ..., + one key per extra task}
"""

import json

from ai_assistant.library import UNCLEAR_INTENT, Library, Profile, Vocabulary

# Origins a value of each kind is allowed to have.
FIELD_ORIGINS = ("informed", "inferred", "absent", "unknown")
PRIORITY_ORIGINS = ("informed", "inferred", "absent")
FACT_ORIGINS = ("informed", "inferred", "base", "absent")
RESPOND_BASE_KEYS = ("speech", "facts", "asking", "next_action")


# --- Spec building blocks ---------------------------------------------------------------------


def _string(nullable: bool = False) -> dict:
    return {"kind": "string", "nullable": nullable}


def _enum(values: tuple[str, ...], nullable: bool = False) -> dict:
    return {"kind": "enum", "values": tuple(values), "nullable": nullable}


def _object(keys: dict[str, dict]) -> dict:
    return {"kind": "object", "keys": keys}


def _name_map(names: tuple[str, ...], value: dict) -> dict:
    return {"kind": "map", "names": tuple(names), "value": value}


def _list(item: dict) -> dict:
    return {"kind": "list", "item": item}


# --- The validator ----------------------------------------------------------------------------


def validate(value: object, spec: dict, path: str) -> list[str]:
    """Return one message per problem found. An empty list means the value follows the spec."""
    if value is None:
        return [] if spec.get("nullable") else [f"{path}: must not be null"]
    kind = spec["kind"]
    if kind == "string":
        if not isinstance(value, str) or not value.strip():
            return [f"{path}: must be a non-empty text"]
        return []
    if kind == "enum":
        if value not in spec["values"]:
            return [f"{path}: must be one of {list(spec['values'])}, got {value!r}"]
        return []
    if kind == "list":
        if not isinstance(value, list):
            return [f"{path}: must be a list"]
        return [
            error
            for index, item in enumerate(value)
            for error in validate(item, spec["item"], f"{path}[{index}]")
        ]
    if not isinstance(value, dict):
        return [f"{path}: must be an object"]
    if kind == "object":
        return _check_keys(value, spec["keys"], path)
    return _check_keys(value, {name: spec["value"] for name in spec["names"]}, path)


def _check_keys(value: dict, keys: dict[str, dict], path: str) -> list[str]:
    errors = [f"{path}: missing key '{key}'" for key in keys if key not in value]
    errors += [f"{path}: unexpected key '{key}'" for key in value if key not in keys]
    for key, sub_spec in keys.items():
        if key in value:
            errors += validate(value[key], sub_spec, f"{path}.{key}")
    return errors


def parse_json(text: object) -> tuple[dict | None, list[str]]:
    """Parse the raw model answer. A blank answer is an error (JSON mode can return one)."""
    if not isinstance(text, str) or not text.strip():
        return None, [
            "the response is empty (it may not have been valid json); "
            "return one valid json object, with no markdown and with quotes escaped inside strings"
        ]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return None, [f"the response is not valid json ({error.msg} at position {error.pos})"]
    if not isinstance(data, dict):
        return None, ["the response must be a json object"]
    return data, []


# --- Specs of each output key -----------------------------------------------------------------


def _output_spec(
    name: str, vocabulary: Vocabulary, intents: tuple[str, ...], field_names: tuple[str, ...]
) -> dict:
    """Spec of one top-level key of a stage output."""
    field_item = _object(
        {"value": _string(True), "quote": _string(True), "origin": _enum(FIELD_ORIGINS)}
    )
    record_item = _object({"value": _string(True), "origin": _enum(vocabulary.origins)})
    specs = {
        "intent": _enum(intents),
        "fields": _name_map(field_names, field_item),
        "summary": _string(),
        "internal_note": _object(
            {
                "priority": _enum(vocabulary.priorities, nullable=True),
                "priority_origin": _enum(PRIORITY_ORIGINS),
                "text": _string(),
            }
        ),
        "record": _name_map(field_names, record_item),
        "speech": _string(),
        "facts": _list(
            _object(
                {
                    "field": _string(),
                    "value": _string(nullable=True),
                    "origin": _enum(FACT_ORIGINS),
                }
            )
        ),
        "asking": _list(_enum(field_names)),
        "next_action": _enum(vocabulary.next_actions),
    }
    if name not in specs:
        raise ValueError(f"no schema for the output field '{name}'")
    return specs[name]


def stage_keys(library: Library, profile: Profile, stage: str) -> tuple[str, ...]:
    """Top-level keys of a stage output: the base keys plus what each task of the profile adds."""
    names = list(RESPOND_BASE_KEYS) if stage == "respond" else []
    for prompt in library.tasks_for(profile.id, stage):
        names += [name for name in prompt.output_fields if name not in names]
    return tuple(names)


def _stage_errors(output: object, library: Library, profile: Profile, stage: str) -> list[str]:
    intents = (*profile.intents, UNCLEAR_INTENT)
    keys = {
        name: _output_spec(name, library.vocabulary, intents, profile.required_fields)
        for name in stage_keys(library, profile, stage)
    }
    return validate(output, _object(keys), "output")


def understand_errors(output: object, library: Library, profile: Profile) -> list[str]:
    """Structure problems of an `understand` answer for this profile."""
    return _stage_errors(output, library, profile, "understand")


def respond_errors(output: object, library: Library, profile: Profile) -> list[str]:
    """Structure problems of a `respond` answer for this profile."""
    return _stage_errors(output, library, profile, "respond")


def example_errors(
    prompt_output_fields: tuple[str, ...], output: dict, library: Library
) -> list[str]:
    """Check a few-shot example output against the schema (field names come from the example)."""
    vocabulary = library.vocabulary
    keys = {}
    for name in prompt_output_fields:
        names = tuple(output.get(name, {})) if name in ("fields", "record") else ()
        keys[name] = _output_spec(name, vocabulary, vocabulary.intents, names)
    return validate(output, _object(keys), "example")
