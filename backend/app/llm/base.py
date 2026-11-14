"""What steps 2 and 4 need from a language model, whatever the provider.

The steps depend on the small LLMClient protocol, not on a vendor SDK: tests use a
scripted client, and a failure of the model never breaks the pipeline, because
callers catch LLMError and fall back to deterministic behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

TIMEOUT_S = 90.0
"""A session must be analysed in under two minutes (docs/specs/questions.md, Q17)."""

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """The model could not produce a usable answer (API error, refusal, truncation)."""


@dataclass(frozen=True, slots=True)
class LLMReply(Generic[T]):
    output: T
    model_id: str
    """The model that produced the output: recorded with every generated text."""


class LLMClient(Protocol):
    def generate(self, *, system: str, user: str, output: type[T]) -> LLMReply[T]:
        """Return an answer validated against ``output``, or raise LLMError."""
        ...
