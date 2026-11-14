"""Rubrics: pure functions that check whether a model answer is grounded in its sources.

Every function returns a list of violations, written so they can be sent back to the model in a
guided retry. An empty list means the answer passed. The functions assume the structure was already
validated by `schemas.py`.

What is verified:
    * every quote exists in the user message or in the memory;
    * values marked "informed" were really written by the user;
    * facts marked "base" equal the source record exactly;
    * the text shown to people only cites codes, dates and names found in the sources;
    * the assistant never claims an action it cannot perform;
    * the next action is coherent with what is still missing.

Known limit: the entity check looks at codes, dates and capitalised names. It does not judge the
meaning of the whole sentence.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

HUMAN_ESCALATION = "human_escalation"
UNCLEAR = "unclear"
CONCLUDING_ACTIONS = ("hand_off_to_team", "close")

CODE_PATTERN = re.compile(r"\b[A-Z]{2,5}\d{2,6}\b")
DATE_PATTERN = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b|\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
WORD_PATTERN = re.compile(r"[A-Za-zÀ-ÿ]+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
# Capitalised words that are not people or places in the assistant's own wording.
ALLOWED_CAPITALISED = frozenset({"logística", "brasil", "ia"})
# First-person Portuguese verbs that claim an action this assistant cannot perform.
FALSE_ACTION_PATTERN = re.compile(
    r"\b(registrei|gravei|salvei|cancelei|agendei|cadastrei|alterei|atualizei|corrigi)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Evidence:
    """Everything the model was allowed to use in this turn."""

    message: str
    memory_texts: tuple[str, ...] = ()
    source: dict[str, str] | None = None

    def user_texts(self) -> tuple[str, ...]:
        """Texts written by the user: the current message and what the memory kept."""
        return (self.message, *self.memory_texts)

    def all_texts(self) -> tuple[str, ...]:
        """User texts plus the values of the source record."""
        source_texts = tuple(str(value) for value in self.source.values()) if self.source else ()
        return (*self.user_texts(), *source_texts)


# --- Text helpers -----------------------------------------------------------------------------


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def _contains(texts: Iterable[str], needle: str) -> bool:
    """Whether `needle` appears in any text, ignoring case, spacing and edge punctuation."""
    wanted = _squash(needle).strip(" .,;:!?")
    return bool(wanted) and any(wanted in _squash(text) for text in texts)


def _dates_in(text: str) -> set[tuple[int | None, int, int]]:
    """Dates found in a text as (year or None, month, day). Handles ISO and DD/MM[/YYYY]."""
    found = set()
    for iso_y, iso_m, iso_d, day, month, year in DATE_PATTERN.findall(text):
        if iso_y:
            found.add((int(iso_y), int(iso_m), int(iso_d)))
        else:
            full_year = None if not year else (int(year) + 2000 if len(year) == 2 else int(year))
            found.add((full_year, int(month), int(day)))
    return found


def _date_supported(
    date: tuple[int | None, int, int], known: set[tuple[int | None, int, int]]
) -> bool:
    year, month, day = date
    return any(
        (month, day) == (k_month, k_day) and (year is None or k_year is None or year == k_year)
        for k_year, k_month, k_day in known
    )


# --- Entities in text shown to people ---------------------------------------------------------


def check_entities(text: str, evidence: Evidence, label: str) -> list[str]:
    """Codes, dates and capitalised names in `text` must come from the evidence."""
    errors = []
    texts = evidence.all_texts()
    for code in dict.fromkeys(CODE_PATTERN.findall(text)):
        if not _contains(texts, code):
            errors.append(f"{label}: the code '{code}' is not in the message, memory or source")
    known_dates = set().union(*(_dates_in(item) for item in texts))
    for date in sorted(_dates_in(text), key=str):
        if not _date_supported(date, known_dates):
            errors.append(
                f"{label}: the date {_format_date(date)} is not in the message, memory or source"
            )
    for name in _capitalised_words(text):
        if name.casefold() not in ALLOWED_CAPITALISED and not _contains(texts, name):
            errors.append(f"{label}: the name '{name}' is not in the message, memory or source")
    return errors


def _format_date(date: tuple[int | None, int, int]) -> str:
    year, month, day = date
    return f"{day:02d}/{month:02d}" + (f"/{year}" if year else "")


def _capitalised_words(text: str) -> list[str]:
    """Capitalised words that are not the first word of a sentence (likely names or places)."""
    found = []
    for sentence in SENTENCE_SPLIT.split(text):
        for word in WORD_PATTERN.findall(sentence)[1:]:
            if len(word) > 1 and word[0].isupper() and word[1:].islower() and word not in found:
                found.append(word)
    return found


def check_false_actions(text: str, label: str) -> list[str]:
    """The assistant cannot register, save, change or cancel anything, so it must not say it did."""
    return [
        f"{label}: claims an action the assistant cannot perform ('{match.group(0)}')"
        for match in FALSE_ACTION_PATTERN.finditer(text)
    ]


# --- Understand stage -------------------------------------------------------------------------


def check_understand(output: dict, evidence: Evidence) -> list[str]:
    """Check the extracted fields of an `understand` answer."""
    errors = []
    for name, item in output["fields"].items():
        errors += _check_extracted(f"fields.{name}", item, evidence)
    return errors


def _check_extracted(where: str, item: dict, evidence: Evidence) -> list[str]:
    value, quote, origin = item["value"], item["quote"], item["origin"]
    if origin == "absent":
        if value is not None or quote is not None:
            return [f"{where}: an absent field must have value null and quote null"]
        return []
    errors = []
    if value is None:
        errors.append(
            f"{where}: the origin is '{origin}' but the value is null; use origin 'absent'"
        )
    if quote is None:
        errors.append(f"{where}: a value with origin '{origin}' needs the exact supporting quote")
    elif not _contains(evidence.user_texts(), quote):
        errors.append(f"{where}: the quote '{quote}' does not appear in the message or the memory")
    if origin == "informed" and value is not None and not _contains(evidence.user_texts(), value):
        errors.append(
            f"{where}: the informed value '{value}' is not in the message or the memory; "
            "copy it as the user wrote it or mark the origin as 'inferred'"
        )
    return errors


# --- Respond stage ----------------------------------------------------------------------------


def check_facts(facts: list[dict], evidence: Evidence) -> list[str]:
    """Facts marked 'base' must equal the source record; 'informed' ones must be user text."""
    errors = []
    for index, fact in enumerate(facts):
        where = f"facts[{index}] ({fact['field']})"
        if fact["origin"] == "base":
            errors += _check_base_fact(where, fact, evidence.source)
        elif fact["origin"] == "informed" and not _contains(evidence.user_texts(), fact["value"]):
            errors.append(
                f"{where}: the informed value '{fact['value']}' is not in the message or memory"
            )
    return errors


def _check_base_fact(where: str, fact: dict, source: dict[str, str] | None) -> list[str]:
    if source is None:
        return [f"{where}: origin is 'base' but no source record was found"]
    if fact["field"] not in source:
        return [f"{where}: the source record has no field '{fact['field']}'"]
    expected = str(source[fact["field"]])
    if expected != fact["value"]:
        return [f"{where}: the source says '{expected}' but the output says '{fact['value']}'"]
    return []


def check_record(record: dict, evidence: Evidence) -> list[str]:
    """Check a standard record: absent means null, informed means user text, base means source."""
    errors = []
    for name, item in record.items():
        where, value, origin = f"record.{name}", item["value"], item["origin"]
        if (origin == "absent") != (value is None):
            errors.append(f"{where}: the value is null if and only if the origin is 'absent'")
        elif origin == "informed" and not _contains(evidence.user_texts(), value):
            errors.append(f"{where}: the informed value '{value}' is not in the message or memory")
        elif origin == "base":
            errors += _check_base_fact(where, {"field": name, "value": value}, evidence.source)
    return errors


def check_internal_note(note: dict, evidence: Evidence) -> list[str]:
    """Priority and its origin go together; the note text follows the entity rules."""
    errors = []
    if (note["priority"] is None) != (note["priority_origin"] == "absent"):
        errors.append("internal_note: priority is null if and only if priority_origin is 'absent'")
    return errors + check_entities(note["text"], evidence, "internal_note.text")


def check_next_action(
    action: str, intent: str, missing: tuple[str, ...], unresolved_ok: bool = False
) -> list[str]:
    """The next action must be coherent with the intent and with what is still missing."""
    if intent == HUMAN_ESCALATION and action != "escalate_to_human":
        return ["next_action: an escalation intent requires 'escalate_to_human'"]
    if missing and not unresolved_ok and action in CONCLUDING_ACTIONS:
        return [f"next_action: cannot conclude while required fields are missing: {list(missing)}"]
    if not missing and action == "ask_missing_information" and intent != UNCLEAR:
        return ["next_action: nothing is missing, so do not ask the user for more information"]
    return []


def check_respond(
    output: dict,
    evidence: Evidence,
    *,
    intent: str,
    missing: tuple[str, ...],
    unresolved_ok: bool = False,
) -> list[str]:
    """Check a `respond` answer: facts, texts shown to people, extras and the next action."""
    errors = check_facts(output["facts"], evidence)
    for label in ("speech", "summary"):
        if label in output:
            errors += check_entities(output[label], evidence, label)
            errors += check_false_actions(output[label], label)
    if "internal_note" in output:
        errors += check_internal_note(output["internal_note"], evidence)
    if "record" in output:
        errors += check_record(output["record"], evidence)
    return errors + check_next_action(output["next_action"], intent, missing, unresolved_ok)
