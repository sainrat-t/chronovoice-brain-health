"""Synthetic demonstration data: personas and their recorded sessions.

Everything under backend/data/synthetic/ is fictional and generated
(docs/specs/synthetic-data.md). A session file holds what the real pipeline would
receive after transcription: the recording metadata and a Scribe-shaped response.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agents.capture import ScribeTranscription
from app.agents.pipeline import analyse_transcription
from app.schemas import AnalysedSession, RecordingMetadata, RiskProfile, SessionTranscript

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
SYNTHETIC_ROOT = DATA_ROOT / "synthetic"


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Persona(_Strict):
    person_id: str
    display_name: str
    birth_year: int
    language: str
    summary: str
    risk_profile: RiskProfile


class PersonaFile(_Strict):
    synthetic: Literal[True]
    personas: tuple[Persona, ...]


class SyntheticSession(_Strict):
    """One generated session, as stored in sessions/<person_id>/<NN>.json."""

    synthetic: Literal[True]
    session_id: str
    metadata: RecordingMetadata
    generation: dict[str, float | int | str | bool | None] = Field(
        description="Parameters the session was generated with, kept for traceability."
    )
    scribe_response: ScribeTranscription


def load_personas(root: Path = SYNTHETIC_ROOT) -> tuple[Persona, ...]:
    return PersonaFile.model_validate_json((root / "personas.json").read_text()).personas


def load_sessions(person_id: str, root: Path = SYNTHETIC_ROOT) -> tuple[SyntheticSession, ...]:
    """Sessions of one persona, in file order (01.json, 02.json, ...)."""
    files = sorted((root / "sessions" / person_id).glob("*.json"))
    return tuple(SyntheticSession.model_validate_json(path.read_text()) for path in files)


def analyse_sessions(
    sessions: Sequence[SyntheticSession],
) -> tuple[tuple[SessionTranscript, AnalysedSession], ...]:
    """Run the deterministic pipeline steps (0 after transcription, and 1) on each session."""
    return tuple(
        analyse_transcription(session.session_id, session.metadata, session.scribe_response)
        for session in sessions
    )
