"""SQLite storage of the prototype (docs/specs/api.md, sections 4 and 7).

One file, five tables. Pipeline outputs are stored as JSON validated by their
Pydantic contract, both on the way in and on the way out. Step 3 is not stored: it
is recomputed from the stored sessions at each read.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.api.models import IN_PROGRESS, Person, SessionStatus
from app.schemas import (
    AnalysedSession,
    ClinicalSummaryReport,
    NarrativeAnalysis,
    RecordingMetadata,
    RiskProfile,
    SessionTranscript,
)

INTERRUPTED = "interrupted: the server stopped while this session was being processed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    person_id TEXT PRIMARY KEY,
    source_app TEXT,
    external_person_id TEXT,
    data TEXT NOT NULL,
    UNIQUE (source_app, external_person_id)
);
CREATE TABLE IF NOT EXISTS risk_profiles (
    person_id TEXT PRIMARY KEY REFERENCES people (person_id) ON DELETE CASCADE,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES people (person_id) ON DELETE CASCADE,
    recorded_at TEXT NOT NULL,
    metadata TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    audio_path TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_by_person ON sessions (person_id, recorded_at);
CREATE TABLE IF NOT EXISTS session_results (
    session_id TEXT PRIMARY KEY REFERENCES sessions (session_id) ON DELETE CASCADE,
    transcript TEXT NOT NULL,
    analysed TEXT NOT NULL,
    narrative TEXT
);
CREATE TABLE IF NOT EXISTS summaries (
    session_id TEXT PRIMARY KEY REFERENCES sessions (session_id) ON DELETE CASCADE,
    person_id TEXT NOT NULL,
    report TEXT NOT NULL
);
"""


class SessionRecord(BaseModel):
    """A session as stored: its metadata and where its processing stands."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    metadata: RecordingMetadata
    status: SessionStatus
    error: str | None = None
    audio_path: str | None = None
    created_at: AwareDatetime

    @property
    def person_id(self) -> str:
        return self.metadata.person_id


@dataclass(frozen=True, slots=True)
class StoredAnalysis:
    """What steps 0 to 2 produced for one session."""

    analysed: AnalysedSession
    narrative: NarrativeAnalysis | None


class Store:
    """Every read and write opens its own connection: the store is shared by threads."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialise(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(_SCHEMA)

    def clear(self) -> None:
        """Remove everything (demo reset)."""
        with self._connect() as db:
            db.execute("DELETE FROM people")

    def is_empty(self) -> bool:
        with self._connect() as db:
            count: int = db.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        return count == 0

    # --- People -------------------------------------------------------------

    def add_person(self, person: Person, risk_profile: RiskProfile | None = None) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO people (person_id, source_app, external_person_id, data) "
                "VALUES (?, ?, ?, ?)",
                (
                    person.person_id,
                    person.source_app,
                    person.external_person_id,
                    person.model_dump_json(),
                ),
            )
            if risk_profile is not None:
                db.execute(
                    "INSERT INTO risk_profiles (person_id, data) VALUES (?, ?)",
                    (person.person_id, risk_profile.model_dump_json()),
                )

    def get_person(self, person_id: str) -> Person | None:
        with self._connect() as db:
            row = db.execute("SELECT data FROM people WHERE person_id = ?", (person_id,)).fetchone()
        return None if row is None else Person.model_validate_json(row[0])

    def find_external_person(self, source_app: str, external_person_id: str) -> Person | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT data FROM people WHERE source_app = ? AND external_person_id = ?",
                (source_app, external_person_id),
            ).fetchone()
        return None if row is None else Person.model_validate_json(row[0])

    def list_people(self) -> list[Person]:
        with self._connect() as db:
            rows = db.execute("SELECT data FROM people").fetchall()
        return [Person.model_validate_json(row[0]) for row in rows]

    def risk_profile(self, person_id: str) -> RiskProfile | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT data FROM risk_profiles WHERE person_id = ?", (person_id,)
            ).fetchone()
        return None if row is None else RiskProfile.model_validate_json(row[0])

    # --- Sessions -----------------------------------------------------------

    def add_session(self, record: SessionRecord) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO sessions (session_id, person_id, recorded_at, metadata, status, "
                "error, audio_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.session_id,
                    record.person_id,
                    record.metadata.recorded_at.astimezone(UTC).isoformat(),
                    record.metadata.model_dump_json(),
                    record.status.value,
                    record.error,
                    record.audio_path,
                    record.created_at.isoformat(),
                ),
            )

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._connect() as db:
            row = db.execute(
                f"SELECT {_SESSION_COLUMNS} FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return None if row is None else _session(row)

    def sessions_of(self, person_id: str) -> list[SessionRecord]:
        """The sessions of one person, oldest first."""
        with self._connect() as db:
            rows = db.execute(
                f"SELECT {_SESSION_COLUMNS} FROM sessions WHERE person_id = ? "
                "ORDER BY recorded_at, created_at",
                (person_id,),
            ).fetchall()
        return [_session(row) for row in rows]

    def set_status(self, session_id: str, status: SessionStatus, error: str | None = None) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE sessions SET status = ?, error = ? WHERE session_id = ?",
                (status.value, error, session_id),
            )

    def set_audio_path(self, session_id: str, audio_path: str | None) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE sessions SET audio_path = ? WHERE session_id = ?", (audio_path, session_id)
            )

    def mark_interrupted(self) -> int:
        """Sessions left in progress by a stopped server become failed."""
        placeholders = ", ".join("?" for _ in IN_PROGRESS)
        with self._connect() as db:
            cursor = db.execute(
                f"UPDATE sessions SET status = ?, error = ? WHERE status IN ({placeholders})",
                (SessionStatus.FAILED.value, INTERRUPTED, *(s.value for s in IN_PROGRESS)),
            )
            return cursor.rowcount

    # --- Results ------------------------------------------------------------

    def save_results(
        self, session_id: str, transcript: SessionTranscript, analysed: AnalysedSession
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO session_results (session_id, transcript, analysed) "
                "VALUES (?, ?, ?)",
                (session_id, transcript.model_dump_json(), analysed.model_dump_json()),
            )

    def save_narrative(self, session_id: str, narrative: NarrativeAnalysis) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE session_results SET narrative = ? WHERE session_id = ?",
                (narrative.model_dump_json(), session_id),
            )

    def transcript(self, session_id: str) -> SessionTranscript | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT transcript FROM session_results WHERE session_id = ?", (session_id,)
            ).fetchone()
        return None if row is None else SessionTranscript.model_validate_json(row[0])

    def analyses_of(self, session_ids: Sequence[str]) -> dict[str, StoredAnalysis]:
        """Steps 0 to 2 of the given sessions, for those that have reached them."""
        if not session_ids:
            return {}
        placeholders = ", ".join("?" for _ in session_ids)
        with self._connect() as db:
            rows = db.execute(
                "SELECT session_id, analysed, narrative FROM session_results "
                f"WHERE session_id IN ({placeholders})",
                tuple(session_ids),
            ).fetchall()
        return {
            row[0]: StoredAnalysis(
                analysed=AnalysedSession.model_validate_json(row[1]),
                narrative=None if row[2] is None else NarrativeAnalysis.model_validate_json(row[2]),
            )
            for row in rows
        }

    # --- Summaries ----------------------------------------------------------

    def save_summary(self, report: ClinicalSummaryReport) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO summaries (session_id, person_id, report) VALUES (?, ?, ?)",
                (report.session_id, report.person_id, report.model_dump_json()),
            )

    def summaries_of(self, session_ids: Sequence[str]) -> dict[str, ClinicalSummaryReport]:
        if not session_ids:
            return {}
        placeholders = ", ".join("?" for _ in session_ids)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT session_id, report FROM summaries WHERE session_id IN ({placeholders})",
                tuple(session_ids),
            ).fetchall()
        return {row[0]: ClinicalSummaryReport.model_validate_json(row[1]) for row in rows}


_SESSION_COLUMNS = "session_id, metadata, status, error, audio_path, created_at"


def _session(row: tuple[str, str, str, str | None, str | None, str]) -> SessionRecord:
    return SessionRecord(
        session_id=row[0],
        metadata=RecordingMetadata.model_validate_json(row[1]),
        status=SessionStatus(row[2]),
        error=row[3],
        audio_path=row[4],
        created_at=datetime.fromisoformat(row[5]),
    )
