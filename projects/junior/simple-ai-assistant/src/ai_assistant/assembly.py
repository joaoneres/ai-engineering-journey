"""Builds the prompts sent to the model.

The system prompt is stable for a profile and stage (role, global rules, tasks, output format and
few-shot examples). The user prompt changes every turn (memory, source record and message).
User text is wrapped in tags and treated as data, never as instructions.
"""

import json
import re

from ai_assistant.library import UNCLEAR_INTENT, Library, Profile, Prompt
from ai_assistant.schemas import stage_keys

UNDERSTAND = "understand"
RESPOND = "respond"

INTENT_MEANINGS = {
    "delivery": "a question or an update about a delivery",
    "occurrence": "an incident that happened on the road",
    "proof": "proof of delivery",
    "address": "a problem with a delivery address",
    "human_escalation": "the user needs a person, or the case must be handled by a person",
    "unclear": "the message is too vague to decide; ask a clarifying question",
}

RESPOND_BASE_FORMAT = (
    '{"speech": "<reply to the user in Brazilian Portuguese>", '
    '"facts": [{"field": "<field name>", "value": "<text>", '
    '"origin": "informed | inferred | base"}], '
    '"next_action": "<one allowed next action>"}'
)

CONVERSATION_RULES = (
    "Read memory.missing. If it is not empty, ask ONE short question about those fields, in "
    "Brazilian Portuguese, and set next_action to ask_missing_information.",
    "If memory.missing is empty, do not ask for more information. Answer from the source with "
    "provide_information, or finish with hand_off_to_team when the case is complete.",
    "Use escalate_to_human when the intent is human_escalation or when a person must handle "
    "the case.",
    "Fields in memory.unknown_after_asking were already requested and the user did not provide "
    "them. Say that they are unknown and never ask for them again.",
    "If the source says found is false, say that you could not find the delivery and ask the "
    "user to check the code. Never use the origin base in that case.",
    "Put in facts every value you mention that came from the source, with origin base, the "
    "source field name and the exact source value.",
)

_TAG_PATTERN = re.compile(r"</?(message|memory|source|rejected_answer|validation_errors)>", re.I)


def _neutralise_tags(text: str) -> str:
    """Stop user text from closing or opening one of our own tags."""
    return _TAG_PATTERN.sub(lambda match: match.group(0).replace("<", "&lt;"), text)


def _bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {item}" for item in items]


def _task_section(task: Prompt) -> list[str]:
    lines = [f"## Task: {task.id} (v{task.version})", f"Objective: {task.objective}", ""]
    lines += [f"Context: {task.context}", "", "Constraints:", *_bullets(task.constraints), ""]
    lines += ["Quality criteria:", *_bullets(task.criteria), ""]
    lines += [f"Output fragment: {task.output_format}", "", "Examples:"]
    for example in task.examples:
        lines += [f"### {example.type}", f"Message: {example.input}"]
        if example.note:
            lines.append(f"Note: {example.note}")
        lines.append(f"Output: {json.dumps(example.output, ensure_ascii=False)}")
        lines.append("")
    return lines


def build_system(library: Library, profile: Profile, stage: str) -> str:
    """The stable instructions for a profile and a stage."""
    vocabulary = library.vocabulary
    lines = ["# Role", profile.role, "", "# Global rules"]
    lines += [f"{number}. {rule}" for number, rule in enumerate(library.rules, start=1)]
    lines += ["", "# Required fields", ", ".join(profile.required_fields)]
    if stage == UNDERSTAND:
        lines += ["", "# Allowed intents"]
        lines += [
            f"- {intent}: {INTENT_MEANINGS[intent]}"
            for intent in (*profile.intents, UNCLEAR_INTENT)
        ]
    else:
        lines += ["", "# Conversation rules", *[f"- {rule}" for rule in CONVERSATION_RULES]]
    lines += [
        "",
        "# Allowed values",
        f"origins: {', '.join(vocabulary.origins)}",
        f"priorities: {', '.join(vocabulary.priorities)}",
        f"next_actions: {', '.join(vocabulary.next_actions)}",
        f"statuses (source field 'status'): {', '.join(vocabulary.statuses)}",
        "",
        "# Tasks",
    ]
    for task in library.tasks_for(profile.id, stage):
        lines += _task_section(task)
    keys = stage_keys(library, profile, stage)
    lines += ["# Output format", f"Return ONE json object with exactly these keys: {list(keys)}."]
    if stage == RESPOND:
        lines.append(f"Base fragment: {RESPOND_BASE_FORMAT}")
    lines.append("Merge the output fragments of all tasks into that single json object.")
    return "\n".join(lines)


def source_view(record: dict[str, str] | None, code: str | None) -> dict:
    """What the model is told about the lookup: the record, or why there is none."""
    if record is not None:
        return {"found": True, "record": record}
    reason = "no code was provided" if not code else f"no delivery has the code {code}"
    return {"found": False, "reason": reason}


def build_user(memory: dict, message: str, source: dict | None = None) -> str:
    """The per-turn prompt: memory, optional source and the user message, each in its tag."""
    parts = [f"<memory>\n{json.dumps(memory, ensure_ascii=False)}\n</memory>"]
    if source is not None:
        parts.append(f"<source>\n{json.dumps(source, ensure_ascii=False)}\n</source>")
    parts.append(f"<message>\n{_neutralise_tags(message)}\n</message>")
    return "\n".join(parts)


def with_errors(user_prompt: str, rejected_answer: str, errors: list[str]) -> str:
    """The guided retry: the same prompt plus the rejected answer and the exact errors."""
    listed = "\n".join(f"- {error}" for error in errors)
    return (
        f"{user_prompt}\n"
        f"<rejected_answer>\n{_neutralise_tags(rejected_answer)}\n</rejected_answer>\n"
        f"<validation_errors>\n{listed}\n</validation_errors>\n"
        "Your previous answer was rejected for the errors above. Fix ALL of them and return the "
        "corrected json object only."
    )
