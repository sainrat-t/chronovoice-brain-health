"""LLMClient backed by the Claude API (Anthropic SDK), with structured outputs."""

from __future__ import annotations

from typing import Final

import anthropic

from app.llm.base import TIMEOUT_S, LLMError, LLMReply, T

MODEL = "claude-opus-5-5"
"""Chosen on 2026-11-12 (docs/specs/questions.md, Q36)."""

EFFORT: Final = "medium"
"""Set explicitly. `medium` keeps a session under the two-minute target (Q17)."""

MAX_TOKENS = 16000
MAX_RETRIES = 1

FALLBACK_BETA = "server-side-fallback-2026-07-01"
"""If the model declines a request on policy grounds, the API re-runs it on a fallback
model inside the same call. The model that actually answered is in LLMReply.model_id."""


class ClaudeClient:
    """LLMClient backed by the Claude API."""

    def __init__(
        self, client: anthropic.Anthropic | None = None, *, api_key: str | None = None
    ) -> None:
        # Without an explicit key, the SDK reads its credentials from the environment.
        self._client = client or anthropic.Anthropic(
            api_key=api_key, timeout=TIMEOUT_S, max_retries=MAX_RETRIES
        )

    def generate(self, *, system: str, user: str, output: type[T]) -> LLMReply[T]:
        try:
            response = self._client.beta.messages.parse(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=output,
                output_config={"effort": EFFORT},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as error:
            raise LLMError("Claude API credentials are missing or invalid") from error
        except anthropic.RateLimitError as error:
            raise LLMError("Claude API rate limit reached") from error
        except anthropic.APIStatusError as error:
            raise LLMError(f"Claude API returned status {error.status_code}") from error
        except anthropic.APIConnectionError as error:
            raise LLMError("Claude API could not be reached") from error

        # A refusal or a truncated answer comes back as a normal response.
        if response.stop_reason != "end_turn":
            raise LLMError(f"Claude stopped with reason {response.stop_reason!r}")
        if response.parsed_output is None:
            raise LLMError("Claude returned no structured output")
        return LLMReply(output=response.parsed_output, model_id=response.model)
