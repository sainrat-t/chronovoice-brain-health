"""Language adapters: one per supported language (English only in the prototype)."""

from __future__ import annotations

from functools import cache

from app.language.base import CONTENT_POS, NOUN_POS, LanguageAdapter, Pos, WordAnalysis

__all__ = [
    "CONTENT_POS",
    "NOUN_POS",
    "LanguageAdapter",
    "Pos",
    "UnsupportedLanguageError",
    "WordAnalysis",
    "get_adapter",
]


class UnsupportedLanguageError(ValueError):
    """Raised when no adapter exists for the requested language."""


@cache
def get_adapter(language: str) -> LanguageAdapter:
    """Return the shared adapter for an ISO 639-3 language code.

    Adapters load their models on first use and are then reused.
    """
    if language == "eng":
        # Imported here so that spaCy is only loaded when English is actually needed.
        from app.language.english import EnglishAdapter

        return EnglishAdapter()
    raise UnsupportedLanguageError(f"no language adapter for {language!r}")
