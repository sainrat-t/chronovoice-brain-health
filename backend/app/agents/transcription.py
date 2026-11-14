"""Step 0 of the pipeline, network part: transcription by ElevenLabs Scribe.

Settings, response format and limits: docs/tech/elevenlabs-scribe.md. The call is a
plain HTTP request (docs/specs/api.md, section 7): the deterministic rest of step 0
is in app.agents.capture.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.agents.capture import ScribeTranscription

logger = logging.getLogger(__name__)

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL_ID = "scribe_v3"
TIMEOUT_S = 300.0
SEED = 20261113
"""Fixed seed for the most stable output Scribe allows; it does not guarantee it
(elevenlabs-scribe.md, section 3)."""


class TranscriptionError(Exception):
    """Scribe could not transcribe the recording."""


class Transcriber(Protocol):
    """What the processing of a session needs from a speech-to-text service."""

    def transcribe(
        self, audio: Path, *, language: str | None, num_speakers: int | None
    ) -> ScribeTranscription: ...

    def delete(self, transcription_id: str) -> None: ...


class ScribeClient:
    """ElevenLabs Scribe v3, with the settings of elevenlabs-scribe.md, section 3."""

    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=TIMEOUT_S)
        self._headers = {"xi-api-key": api_key}

    def transcribe(
        self, audio: Path, *, language: str | None, num_speakers: int | None
    ) -> ScribeTranscription:
        form: dict[str, str] = {
            "model_id": MODEL_ID,
            "diarize": "true",
            "timestamps_granularity": "word",
            "tag_audio_events": "true",
            # Never true: it removes the hesitations the fluency markers count.
            "no_verbatim": "false",
            # "forty-two" rather than "42": the words actually said are counted.
            "numbers_format": "words",
            "temperature": "0",
            "seed": str(SEED),
        }
        if language:
            form["language_code"] = language
        if num_speakers:
            form["num_speakers"] = str(num_speakers)
        try:
            with audio.open("rb") as file:
                response = self._client.post(
                    API_URL, headers=self._headers, data=form, files={"file": (audio.name, file)}
                )
        except httpx.HTTPError as error:
            raise TranscriptionError("Scribe could not be reached") from error
        if response.status_code != httpx.codes.OK:
            raise TranscriptionError(
                f"Scribe returned status {response.status_code}: {_detail(response)}"
            )
        try:
            return ScribeTranscription.model_validate_json(response.content)
        except ValidationError as error:
            raise TranscriptionError("Scribe returned an unexpected response") from error

    def delete(self, transcription_id: str) -> None:
        """Remove the transcript kept by ElevenLabs (elevenlabs-scribe.md, section 7)."""
        try:
            response = self._client.delete(
                f"{API_URL}/transcripts/{transcription_id}", headers=self._headers
            )
        except httpx.HTTPError as error:
            raise TranscriptionError("Scribe could not be reached") from error
        if response.status_code >= httpx.codes.BAD_REQUEST:
            raise TranscriptionError(
                f"deleting transcript returned status {response.status_code}: {_detail(response)}"
            )


def _detail(response: httpx.Response) -> str:
    """A short, key-free description of an error response."""
    return response.text[:200].replace("\n", " ")
