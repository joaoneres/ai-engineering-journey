"""Pre-recorded conversations (one per profile) used by the tests and by the offline `--demo`.

A scenario lists the user messages and, for each of them, the answers a model would give in order
(understand, respond, plus any retries). They are replayed through a `ScriptedModel`, so the whole
flow, validators included, runs without network.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from ai_assistant.library import PROFILE_IDS, PROJECT_ROOT
from ai_assistant.model import ScriptedModel

SCENARIOS_DIR = PROJECT_ROOT / "scenarios"


class ScenarioError(Exception):
    """A scenario file is missing or malformed."""


@dataclass(frozen=True)
class ScenarioTurn:
    user: str
    model: tuple[dict, ...]


@dataclass(frozen=True)
class Scenario:
    profile: str
    description: str
    turns: tuple[ScenarioTurn, ...]

    def scripted_model(self) -> ScriptedModel:
        """A model that replays every answer of the scenario, in order."""
        return ScriptedModel(answer for turn in self.turns for answer in turn.model)


def load_scenario(profile_id: str, directory: Path = SCENARIOS_DIR) -> Scenario:
    """Load the scenario of a profile."""
    if profile_id not in PROFILE_IDS:
        raise ScenarioError(f"unknown profile '{profile_id}'")
    path = Path(directory) / f"{profile_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        turns = tuple(
            ScenarioTurn(user=item["user"], model=tuple(item["model"])) for item in data["turns"]
        )
        return Scenario(profile=data["profile"], description=data["description"], turns=turns)
    except OSError as error:
        raise ScenarioError(f"cannot read {path.name}: {error.strerror}") from error
    except (ValueError, KeyError, TypeError) as error:
        raise ScenarioError(f"{path.name} is malformed ({error})") from error
