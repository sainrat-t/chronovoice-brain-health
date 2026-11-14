"""LLMClient backed by the Mistral API (mistralai SDK), with structured outputs."""

from __future__ import annotations

import httpx2
from mistralai.client import Mistral, errors
from mistralai.client.errors.mistralerror import MistralError

from app.llm.base import TIMEOUT_S, LLMError, LLMReply, T

DEFAULT_MODEL = "mistral-small-latest"
"""Small model proposed by Thibaut on 2026-11-13 for the real trials; MISTRAL_MODEL
overrides it (docs/specs/pipeline.md, "Appel au modèle")."""

MAX_TOKENS = 8000


class MistralClient:
    """LLMClient backed by the Mistral API."""

    def __init__(
        self,
        client: Mistral | None = None,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        reasoning_effort: str | None = None,
    ) -> None:
        self._client = client or Mistral(api_key=api_key, timeout_ms=int(TIMEOUT_S * 1000))
        self._model = model
        # Sent only when set: the accepted values differ from one model to the next
        # (docs/specs/pipeline.md, "Appel au modèle").
        self._reasoning: dict[str, str] = (
            {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
        )

    def generate(self, *, system: str, user: str, output: type[T]) -> LLMReply[T]:
        try:
            response = self._client.chat.parse(
                response_format=output,
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=MAX_TOKENS,
                # Greedy sampling: some models (Mistral Large) refuse temperature 0
                # unless top_p is exactly 1 (docs/specs/pipeline.md, "Appel au modèle").
                temperature=0,
                top_p=1,
                **self._reasoning,
            )
        except MistralError as error:
            status = getattr(error, "status_code", "unknown")
            raise LLMError(f"Mistral API returned status {status}") from error
        except (errors.NoResponseError, httpx2.HTTPError) as error:
            raise LLMError("Mistral API could not be reached") from error
        except ValueError as error:
            # The SDK validates the answer against the schema while parsing it.
            raise LLMError("Mistral returned an answer outside the expected format") from error

        choice = response.choices[0] if response.choices else None
        if choice is None or choice.finish_reason != "stop":
            reason = choice.finish_reason if choice else "no answer"
            raise LLMError(f"Mistral stopped with reason {reason!r}")
        if choice.message is None or choice.message.parsed is None:
            raise LLMError("Mistral returned no structured output")
        return LLMReply(output=choice.message.parsed, model_id=response.model)
