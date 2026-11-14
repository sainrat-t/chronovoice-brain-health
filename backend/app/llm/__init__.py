"""Language model used by steps 2 and 4, behind one provider-neutral contract.

Two providers are available (docs/specs/pipeline.md, "Appel au modèle"):
Mistral (app.llm.mistral) and Anthropic (app.llm.claude).
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from app.llm.base import LLMClient, LLMError, LLMReply

__all__ = ["LLMClient", "LLMError", "LLMReply", "create_llm_client"]


def create_llm_client(env: Mapping[str, str] | None = None) -> LLMClient | None:
    """Build the client of the configured provider, or None when no key is set.

    LLM_PROVIDER ("mistral" or "anthropic") decides. Without it, the provider whose
    key is present is used, Anthropic first when both are. Without any key the
    pipeline runs with no model: step 2 is skipped and step 4 uses its fixed wording.
    """
    env = os.environ if env is None else env
    provider = env.get("LLM_PROVIDER", "").strip().lower()
    if not provider:
        if env.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif env.get("MISTRAL_API_KEY"):
            provider = "mistral"
        else:
            return None

    # Each SDK is imported only when its provider is used.
    if provider == "mistral":
        if not env.get("MISTRAL_API_KEY"):
            raise ValueError("LLM_PROVIDER is 'mistral' but MISTRAL_API_KEY is not set")
        from app.llm.mistral import DEFAULT_MODEL, MistralClient

        return MistralClient(
            api_key=env["MISTRAL_API_KEY"],
            model=env.get("MISTRAL_MODEL") or DEFAULT_MODEL,
            reasoning_effort=env.get("MISTRAL_REASONING_EFFORT") or None,
        )
    if provider == "anthropic":
        if not env.get("ANTHROPIC_API_KEY"):
            raise ValueError("LLM_PROVIDER is 'anthropic' but ANTHROPIC_API_KEY is not set")
        from app.llm.claude import ClaudeClient

        return ClaudeClient(api_key=env["ANTHROPIC_API_KEY"])
    raise ValueError(f"unknown LLM_PROVIDER {provider!r}: expected 'mistral' or 'anthropic'")
