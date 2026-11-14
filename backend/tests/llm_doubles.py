"""A scripted stand-in for the language model: tests never call the network."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.llm import LLMReply


class ScriptedLLM:
    """Gives its scripted answers in order, and records what it was asked."""

    def __init__(self, *answers: BaseModel | Exception, model_id: str = "claude-opus-5-5") -> None:
        self._answers = list(answers)
        self.model_id = model_id
        self.prompts: list[str] = []
        self.systems: list[str] = []

    def generate(self, *, system: str, user: str, output: type[Any]) -> LLMReply[Any]:
        self.systems.append(system)
        self.prompts.append(user)
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        assert isinstance(answer, output), f"scripted answer is not a {output.__name__}"
        return LLMReply(output=answer, model_id=self.model_id)
