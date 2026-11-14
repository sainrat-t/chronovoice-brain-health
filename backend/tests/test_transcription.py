"""Tests for the Scribe client, against a stand-in for the ElevenLabs API."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.agents.transcription import API_URL, MODEL_ID, ScribeClient, TranscriptionError

ANSWER = {
    "language_code": "eng",
    "language_probability": 0.99,
    "text": "Hello um there.",
    "transcription_id": "tr-1",
    "audio_duration_secs": 2.0,
    "words": [
        {"text": "Hello", "type": "word", "start": 0.0, "end": 0.4, "speaker_id": "speaker_0"},
        {"text": " ", "type": "spacing", "start": 0.4, "end": 0.5},
        {"text": "um", "type": "word", "start": 0.5, "end": 0.7, "speaker_id": "speaker_0"},
    ],
}


def _client(handler: httpx.MockTransport) -> ScribeClient:
    return ScribeClient("test-key", client=httpx.Client(transport=handler))


@pytest.fixture
def audio(tmp_path: Path) -> Path:
    path = tmp_path / "session.webm"
    path.write_bytes(b"not really audio")
    return path


def test_request_uses_the_verbatim_settings_of_the_spec(audio: Path) -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=ANSWER)

    result = _client(httpx.MockTransport(handler)).transcribe(audio, language="eng", num_speakers=2)

    assert result.transcription_id == "tr-1"
    assert [w.type for w in result.words] == ["word", "spacing", "word"]
    (request,) = sent
    assert str(request.url) == API_URL
    assert request.headers["xi-api-key"] == "test-key"
    body = request.read()
    fields = {
        "model_id": MODEL_ID,
        "diarize": "true",
        "timestamps_granularity": "word",
        "tag_audio_events": "true",
        "no_verbatim": "false",  # never true: it would remove the hesitations
        "numbers_format": "words",
        "temperature": "0",
        "language_code": "eng",
        "num_speakers": "2",
    }
    for name, value in fields.items():
        assert f'name="{name}"\r\n\r\n{value}\r\n'.encode() in body, name
    assert b'name="file"; filename="session.webm"' in body
    assert b"not really audio" in body


def test_unknown_language_and_speaker_count_are_left_to_scribe(audio: Path) -> None:
    sent: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.read())
        return httpx.Response(200, json=ANSWER)

    _client(httpx.MockTransport(handler)).transcribe(audio, language=None, num_speakers=None)

    assert b'name="language_code"' not in sent[0]
    assert b'name="num_speakers"' not in sent[0]


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(401, json={"detail": "invalid key"}), "status 401"),
        (httpx.Response(200, content=b"not json"), "unexpected response"),
        (httpx.Response(200, content=json.dumps({"text": "no words"}).encode()), "unexpected"),
    ],
)
def test_failures_become_transcription_errors(
    audio: Path, response: httpx.Response, message: str
) -> None:
    client = _client(httpx.MockTransport(lambda _: response))

    with pytest.raises(TranscriptionError, match=message):
        client.transcribe(audio, language="eng", num_speakers=None)


def test_unreachable_service_is_a_transcription_error(audio: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(TranscriptionError, match="could not be reached"):
        _client(httpx.MockTransport(handler)).transcribe(audio, language="eng", num_speakers=None)


def test_transcript_is_deleted_at_elevenlabs() -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"status": "ok"})

    _client(httpx.MockTransport(handler)).delete("tr-1")

    (request,) = sent
    assert (request.method, str(request.url)) == ("DELETE", f"{API_URL}/transcripts/tr-1")
    failing = _client(httpx.MockTransport(lambda _: httpx.Response(404)))
    with pytest.raises(TranscriptionError, match="status 404"):
        failing.delete("tr-1")
