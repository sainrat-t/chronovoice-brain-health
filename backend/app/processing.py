"""Processing of one session, from the audio file to the summary (docs/specs/api.md, section 3).

Statuses: received -> transcribing -> analysing -> summarising -> done, or rejected
(quality check) or failed (technical error). It runs as a FastAPI background task.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.agents.capture import ScribeTranscription
from app.agents.drift import compare_trajectory
from app.agents.narrative import analyse_narrative
from app.agents.pipeline import analyse_transcription
from app.agents.summary import write_summary
from app.agents.transcription import Transcriber, TranscriptionError
from app.api.models import SessionStatus
from app.language import get_adapter
from app.llm import LLMClient
from app.schemas import (
    AnalysedSession,
    LongitudinalComparisonResult,
    NarrativeAnalysis,
    QualityStatus,
    RecordingSource,
    SessionTranscript,
    TaskType,
)
from app.store import SessionRecord, Store, StoredAnalysis

logger = logging.getLogger(__name__)

TRANSCRIPTION_ATTEMPTS = 2
"""One call, then one retry, before the session fails (docs/specs/api.md, section 3)."""

SUMMARY_UNAVAILABLE = "summary unavailable"

NARRATIVE_QUALITIES = frozenset({QualityStatus.USABLE, QualityStatus.PARTIAL})
"""Step 2 runs on life stories of usable or partial quality (docs/specs/pipeline.md)."""


@dataclass(frozen=True)
class Services:
    store: Store
    transcriber: Transcriber | None
    llm: LLMClient | None


class Processor:
    """Runs sessions through the pipeline; one person's steps 2 to 4 run one at a time."""

    def __init__(self, services: Services) -> None:
        self._services = services
        self._guard = threading.Lock()
        self._person_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

    def process(self, session_id: str) -> None:
        store = self._services.store
        record = store.get_session(session_id)
        if record is None:
            return
        try:
            self._process(record)
        except Exception:
            logger.exception("processing of %s failed", session_id)
            store.set_status(session_id, SessionStatus.FAILED, "internal error while processing")

    def _process(self, record: SessionRecord) -> None:
        store = self._services.store
        session_id = record.session_id

        store.set_status(session_id, SessionStatus.TRANSCRIBING)
        scribe = self._transcribe(record)
        if scribe is None:
            return

        store.set_status(session_id, SessionStatus.ANALYSING)
        transcript, analysed = analyse_transcription(session_id, record.metadata, scribe)
        store.save_results(session_id, transcript, analysed)
        self._discard_audio(record, scribe)
        if analysed.quality.status is QualityStatus.REJECTED:
            store.set_status(session_id, SessionStatus.REJECTED)
            return

        with self._lock_for(record.person_id):
            error = self._narrate_and_summarise(record, transcript, analysed)
        store.set_status(session_id, SessionStatus.DONE, error)

    def _transcribe(self, record: SessionRecord) -> ScribeTranscription | None:
        store = self._services.store
        transcriber = self._services.transcriber
        if transcriber is None or record.audio_path is None:
            store.set_status(
                record.session_id, SessionStatus.FAILED, "transcription is not available"
            )
            return None
        # A recording made in the interface holds two voices: the person and the clinician.
        speakers = 2 if record.metadata.source is RecordingSource.CLINICIAN_UI else None
        problem = ""
        for _ in range(TRANSCRIPTION_ATTEMPTS):
            try:
                return transcriber.transcribe(
                    Path(record.audio_path),
                    language=record.metadata.language,
                    num_speakers=speakers,
                )
            except TranscriptionError as error:
                problem = str(error)
                logger.warning("transcription of %s failed: %s", record.session_id, error)
        # The audio is kept so that the session can be retried.
        store.set_status(record.session_id, SessionStatus.FAILED, f"transcription: {problem}")
        return None

    def _discard_audio(self, record: SessionRecord, scribe: ScribeTranscription) -> None:
        """Once the transcript is stored, the audio and ElevenLabs' copy are deleted."""
        if record.audio_path is not None:
            Path(record.audio_path).unlink(missing_ok=True)
            self._services.store.set_audio_path(record.session_id, None)
        transcriber = self._services.transcriber
        if transcriber is not None and scribe.transcription_id:
            try:
                transcriber.delete(scribe.transcription_id)
            except TranscriptionError as error:
                logger.warning(
                    "transcript of %s not deleted at ElevenLabs: %s", record.session_id, error
                )

    def _narrate_and_summarise(
        self, record: SessionRecord, transcript: SessionTranscript, analysed: AnalysedSession
    ) -> str | None:
        """Steps 2, 3 and 4. Returns a note when the summary could not be written."""
        store = self._services.store
        llm = self._services.llm
        adapter = get_adapter(record.metadata.language)
        sessions = store.sessions_of(record.person_id)
        analyses = store.analyses_of([s.session_id for s in sessions])

        narrative: NarrativeAnalysis | None = None
        if (
            llm is not None
            and record.metadata.task_type is TaskType.LIFE_STORY
            and analysed.quality.status in NARRATIVE_QUALITIES
        ):
            previous = earlier_narratives(record, sessions, analyses)
            narrative = analyse_narrative(transcript, previous, llm, adapter)
            if narrative is not None:
                store.save_narrative(record.session_id, narrative)

        store.set_status(record.session_id, SessionStatus.SUMMARISING)
        comparison = comparison_of(record.session_id, [a.analysed for a in analyses.values()])
        if comparison is None:
            return SUMMARY_UNAVAILABLE
        try:
            report = write_summary(
                transcript=transcript,
                analysed=analysed,
                comparison=comparison,
                llm=llm,
                adapter=adapter,
            )
        except Exception:
            logger.exception("summary of %s could not be written", record.session_id)
            return SUMMARY_UNAVAILABLE
        store.save_summary(report)
        return None

    def _lock_for(self, person_id: str) -> threading.Lock:
        with self._guard:
            return self._person_locks[person_id]


def earlier_narratives(
    record: SessionRecord,
    sessions: Sequence[SessionRecord],
    analyses: Mapping[str, StoredAnalysis],
) -> list[NarrativeAnalysis]:
    """The step 2 analyses of the person's sessions recorded before this one."""
    found: list[NarrativeAnalysis] = []
    for session in sessions:
        stored = analyses.get(session.session_id)
        if (
            session.metadata.recorded_at < record.metadata.recorded_at
            and stored is not None
            and stored.narrative is not None
        ):
            found.append(stored.narrative)
    return found


def comparison_of(
    session_id: str, analysed: Sequence[AnalysedSession]
) -> LongitudinalComparisonResult | None:
    """Step 3 for one session, recomputed over the person's whole trajectory."""
    for result in compare_trajectory(analysed):
        if result.session_id == session_id:
            return result
    return None
