"""Bank of opening questions for a life-story session (docs/specs/clinician-ui.md, screen 4).

A person is never asked the same theme twice while unused ones remain
(docs/specs/api.md, section 7).
"""

from __future__ import annotations

import random
from collections.abc import Collection, Mapping
from datetime import datetime
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.api.models import Prompt
from app.schemas import Identifier, LanguageCode, NonEmptyText, TaskType

PROMPTS_FILE = Path(__file__).resolve().parents[1] / "data" / "prompts.json"


class _PromptEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Identifier
    theme: NonEmptyText
    question: NonEmptyText


class PromptBank(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    synthetic: bool
    task_type: TaskType
    language: LanguageCode
    follow_ups: tuple[NonEmptyText, ...]
    prompts: tuple[_PromptEntry, ...]

    def get(self, prompt_id: str | None) -> Prompt | None:
        entry = next((p for p in self.prompts if p.id == prompt_id), None)
        return None if entry is None else self._prompt(entry)

    def choose(
        self,
        last_asked: Mapping[str, datetime],
        exclude: Collection[str] = (),
        rng: random.Random | None = None,
    ) -> Prompt:
        """A theme never asked, at random; if all were asked, the one asked longest ago.

        ``last_asked`` maps a prompt id to when the person was last asked it;
        ``exclude`` holds themes already offered on screen.
        """
        rng = rng or random.Random()
        offered = [p for p in self.prompts if p.id not in exclude] or list(self.prompts)
        never = [p for p in offered if p.id not in last_asked]
        if never:
            return self._prompt(rng.choice(never))
        return self._prompt(min(offered, key=lambda p: last_asked[p.id]))

    def _prompt(self, entry: _PromptEntry) -> Prompt:
        return Prompt(
            prompt_id=entry.id,
            theme=entry.theme,
            question=entry.question,
            follow_ups=self.follow_ups,
        )


@cache
def load_prompt_bank(path: Path = PROMPTS_FILE) -> PromptBank:
    return PromptBank.model_validate_json(path.read_text())
