"""Chaining of the deterministic pipeline steps for one session.

From a Scribe transcription to what step 3 needs: transcript and quality control
(step 0), then markers (step 1). No network call, no LLM.
"""

from __future__ import annotations

from app.agents.capture import ScribeTranscription, assess_quality, build_transcript
from app.agents.markers import compute_session_metrics
from app.language import LanguageAdapter, get_adapter
from app.schemas import AnalysedSession, QualityStatus, RecordingMetadata, SessionTranscript


def analyse_transcription(
    session_id: str,
    metadata: RecordingMetadata,
    scribe: ScribeTranscription,
    adapter: LanguageAdapter | None = None,
) -> tuple[SessionTranscript, AnalysedSession]:
    """Run steps 0 (after transcription) and 1 on one session.

    A rejected session has no markers: it is shown with the reasons of its rejection.
    """
    adapter = adapter or get_adapter(metadata.language)
    transcript = build_transcript(session_id, metadata, scribe)
    quality = assess_quality(transcript, metadata, adapter)
    metrics = (
        None
        if quality.status is QualityStatus.REJECTED
        else compute_session_metrics(transcript, adapter)
    )
    return transcript, AnalysedSession(metadata=metadata, quality=quality, metrics=metrics)
