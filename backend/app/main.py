"""ChronoVoice Brain API entrypoint (docs/specs/api.md).

One service: the API under /api, the health probe, and later the built frontend.
Configuration comes from environment variables (backend/.env, never committed).
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import tempfile
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, TypeVar

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from app.agents.transcription import ScribeClient, Transcriber
from app.api import views
from app.api.models import (
    IntegrationMetadata,
    Person,
    PersonCreate,
    PersonDetail,
    PersonSummary,
    Prompt,
    ReviewRequest,
    SessionAccepted,
    SessionDetail,
    SessionStatus,
    SessionStatusView,
    SessionUpload,
    Trajectory,
)
from app.demo import seed_demo
from app.language import UnsupportedLanguageError, get_adapter
from app.llm import LLMClient, create_llm_client
from app.processing import Processor, Services
from app.prompts import load_prompt_bank
from app.schemas import (
    ClinicalSummaryReport,
    RecordingMetadata,
    RecordingSource,
    ReviewRecord,
    ReviewStatus,
)
from app.store import SessionRecord, Store

logger = logging.getLogger(__name__)

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "chronovoice.sqlite3"
DEFAULT_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"
"""The built clinician interface, served by the same service (docs/specs/api.md, section 1)."""
MAX_AUDIO_BYTES = 100 * 1024 * 1024
"""15 minutes of opus is about 15 MB (docs/specs/api.md, section 7)."""
_CHUNK = 1024 * 1024
_SUFFIX = re.compile(r"^\.[a-z0-9]{1,5}$")
_SUFFIX_BY_TYPE = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/aiff": ".aiff",
}


@dataclass
class AppConfig:
    db_path: Path = DEFAULT_DB
    audio_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "chronovoice")
    seed_demo: bool = True
    demo_people: tuple[str, ...] | None = None
    frontend_dist: Path | None = DEFAULT_FRONTEND
    integration_key: str | None = None
    transcriber: Transcriber | None = None
    llm: LLMClient | None = None


def config_from_env() -> AppConfig:
    scribe_key = os.environ.get("ELEVENLABS_API_KEY")
    return AppConfig(
        db_path=Path(os.environ.get("CHRONOVOICE_DB") or DEFAULT_DB),
        audio_dir=Path(
            os.environ.get("CHRONOVOICE_AUDIO_DIR") or Path(tempfile.gettempdir()) / "chronovoice"
        ),
        integration_key=os.environ.get("INTEGRATION_API_KEY") or None,
        frontend_dist=Path(os.environ.get("CHRONOVOICE_FRONTEND_DIST") or DEFAULT_FRONTEND),
        transcriber=ScribeClient(scribe_key) if scribe_key else None,
        llm=create_llm_client(),
    )


@dataclass(frozen=True)
class Runtime:
    config: AppConfig
    services: Services
    processor: Processor

    @property
    def store(self) -> Store:
        return self.services.store


def create_app(config: AppConfig | Callable[[], AppConfig] = config_from_env) -> FastAPI:
    """Build the app; the configuration is read when it starts, not at import."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings = config() if callable(config) else config
        store = Store(settings.db_path)
        store.initialise()
        if settings.seed_demo and store.is_empty():
            seed_demo(store, only=settings.demo_people)
        interrupted = store.mark_interrupted()
        if interrupted:
            logger.warning("%d session(s) interrupted by the last stop marked failed", interrupted)
        settings.audio_dir.mkdir(parents=True, exist_ok=True)
        services = Services(store=store, transcriber=settings.transcriber, llm=settings.llm)
        app.state.runtime = Runtime(settings, services, Processor(services))
        yield

    app = FastAPI(
        title="ChronoVoice Brain API",
        version="0.2.0",
        description=(
            "Longitudinal speech and language biomarkers from life-story recordings, "
            "for early detection of cognitive change. Screening support only - non-diagnostic."
        ),
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe. `phase` tracks the project stage (see CLAUDE.md)."""
        return {"status": "ok", "phase": "prototype"}

    app.include_router(router)
    _serve_frontend(app, config if isinstance(config, AppConfig) else None)
    return app


def _serve_frontend(app: FastAPI, config: AppConfig | None) -> None:
    """Serve the built interface, when it exists, for every path outside the API.

    The interface routes its own pages (/people/..., /sessions/...): any other path
    gets index.html. Read at import time, since routes cannot be added once started.
    """
    dist = config.frontend_dist if config is not None else _env_frontend()
    if dist is None or not (dist / "index.html").is_file():
        return
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    index = dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown API route")
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist.resolve()):
            return FileResponse(file)
        return FileResponse(index)


def _env_frontend() -> Path | None:
    return Path(os.environ.get("CHRONOVOICE_FRONTEND_DIST") or DEFAULT_FRONTEND)


router = APIRouter(prefix="/api")


def _runtime(request: Request) -> Runtime:
    runtime: Runtime = request.app.state.runtime
    return runtime


RuntimeDep = Annotated[Runtime, Depends(_runtime)]
Model = TypeVar("Model", bound=BaseModel)


# --- People ---------------------------------------------------------------


@router.get("/people")
def list_people(runtime: RuntimeDep) -> list[PersonSummary]:
    return views.person_summaries(runtime.store)


@router.post("/people", status_code=status.HTTP_201_CREATED)
def create_person(body: PersonCreate, runtime: RuntimeDep) -> Person:
    _require_language(body.language)
    person = Person(
        person_id=_new_id("p"),
        display_name=body.display_name.strip(),
        birth_year=body.birth_year,
        language=body.language,
        created_at=datetime.now(UTC),
    )
    runtime.store.add_person(person)
    return person


@router.get("/people/{person_id}")
def get_person(person_id: str, runtime: RuntimeDep) -> PersonDetail:
    return views.person_detail(runtime.store, _person(runtime, person_id))


@router.get("/people/{person_id}/trajectory")
def get_trajectory(person_id: str, runtime: RuntimeDep) -> Trajectory:
    _person(runtime, person_id)
    return views.trajectory(runtime.store, person_id)


@router.post("/people/{person_id}/summary/review")
def review_summary(
    person_id: str, body: ReviewRequest, runtime: RuntimeDep
) -> ClinicalSummaryReport:
    """The clinician validates the summary of the person's last processed session."""
    _person(runtime, person_id)
    store = runtime.store
    sessions = store.sessions_of(person_id)
    summaries = store.summaries_of([s.session_id for s in sessions])
    latest = next(
        (summaries[s.session_id] for s in reversed(sessions) if s.session_id in summaries), None
    )
    if latest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "this person has no summary yet")
    if latest.review.status is ReviewStatus.VALIDATED:
        raise HTTPException(status.HTTP_409_CONFLICT, "this summary is already validated")
    reviewed = latest.model_copy(
        update={
            "review": ReviewRecord(
                status=ReviewStatus.VALIDATED,
                reviewed_by=body.reviewed_by.strip(),
                reviewed_at=datetime.now(UTC),
            )
        }
    )
    store.save_summary(reviewed)
    return reviewed


@router.get("/prompts")
def choose_prompt(
    runtime: RuntimeDep,
    person_id: str,
    exclude: Annotated[list[str] | None, Query()] = None,
) -> Prompt:
    """A theme never asked to this person; ``exclude`` skips themes already offered."""
    _person(runtime, person_id)
    asked = views.last_asked(runtime.store.sessions_of(person_id))
    return load_prompt_bank().choose(asked, exclude=set(exclude or ()))


# --- Sessions -------------------------------------------------------------


@router.post("/people/{person_id}/sessions", status_code=status.HTTP_202_ACCEPTED)
async def upload_session(
    person_id: str,
    runtime: RuntimeDep,
    background: BackgroundTasks,
    audio: Annotated[UploadFile, File()],
    metadata: Annotated[str, Form()],
) -> SessionAccepted:
    person = _person(runtime, person_id)
    upload = _parse(SessionUpload, metadata)
    session_id = _new_id("s")
    recording = RecordingMetadata(
        person_id=person.person_id,
        task_type=upload.task_type,
        language=person.language,
        consent=upload.consent,
        recorded_at=upload.recorded_at or datetime.now(UTC),
        source=RecordingSource.CLINICIAN_UI,
        context=upload.context,
        prompt_id=upload.prompt_id,
        synthetic=person.synthetic,
    )
    return await _accept(runtime, background, session_id, recording, audio)


@router.get("/sessions/{session_id}")
def get_session(session_id: str, runtime: RuntimeDep) -> SessionDetail:
    return views.session_detail(runtime.store, _session(runtime, session_id))


@router.get("/sessions/{session_id}/status")
def get_session_status(session_id: str, runtime: RuntimeDep) -> SessionStatusView:
    return views.session_status(_session(runtime, session_id))


@router.post("/sessions/{session_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_session(
    session_id: str, runtime: RuntimeDep, background: BackgroundTasks
) -> SessionAccepted:
    """Run a failed session again, as long as its audio is still there."""
    record = _session(runtime, session_id)
    if record.status is not SessionStatus.FAILED:
        raise HTTPException(status.HTTP_409_CONFLICT, "only a failed session can be retried")
    if record.audio_path is None or not Path(record.audio_path).exists():
        raise HTTPException(status.HTTP_409_CONFLICT, "the audio of this session is gone")
    runtime.store.set_status(session_id, SessionStatus.RECEIVED)
    background.add_task(runtime.processor.process, session_id)
    return _accepted(session_id, SessionStatus.RECEIVED)


# --- Integration ----------------------------------------------------------


@router.post("/integrations/recordings", status_code=status.HTTP_202_ACCEPTED)
async def receive_recording(
    runtime: RuntimeDep,
    background: BackgroundTasks,
    audio: Annotated[UploadFile, File()],
    metadata: Annotated[str, Form()],
    x_integration_key: Annotated[str | None, Header()] = None,
) -> SessionAccepted:
    """Another application that records speech (for example MyMémoires) sends a recording.

    The person is matched by ``source_app`` and ``external_person_id``, and created
    when unknown (docs/specs/api.md, section 5).
    """
    expected = runtime.config.integration_key
    if expected is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "integration is not configured")
    if x_integration_key is None or not secrets.compare_digest(x_integration_key, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid integration key")
    sent = _parse(IntegrationMetadata, metadata)
    _require_language(sent.language)

    store = runtime.store
    person = store.find_external_person(sent.source_app, sent.external_person_id)
    if person is None:
        person = Person(
            person_id=_new_id("p"),
            display_name=sent.display_name or f"{sent.source_app} {sent.external_person_id}",
            birth_year=sent.birth_year,
            language=sent.language,
            source_app=sent.source_app,
            external_person_id=sent.external_person_id,
            created_at=datetime.now(UTC),
        )
        store.add_person(person)
    recording = RecordingMetadata(
        person_id=person.person_id,
        task_type=sent.task_type,
        language=sent.language,
        consent=sent.consent,
        recorded_at=sent.recorded_at,
        source=RecordingSource.INTEGRATION,
        context=sent.context,
        target_speaker_hint=sent.target_speaker_hint,
    )
    return await _accept(runtime, background, _new_id("s"), recording, audio)


# --- Helpers --------------------------------------------------------------


async def _accept(
    runtime: Runtime,
    background: BackgroundTasks,
    session_id: str,
    metadata: RecordingMetadata,
    audio: UploadFile,
) -> SessionAccepted:
    """Save the audio, record the session and start its processing in the background."""
    if runtime.services.transcriber is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "transcription is not configured")
    path = runtime.config.audio_dir / f"{session_id}{_suffix(audio)}"
    size = 0
    with path.open("wb") as file:
        while chunk := await audio.read(_CHUNK):
            size += len(chunk)
            if size > MAX_AUDIO_BYTES:
                file.close()
                path.unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "audio file over 100 MB")
            file.write(chunk)
    if size == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "the audio file is empty")

    runtime.store.add_session(
        SessionRecord(
            session_id=session_id,
            metadata=metadata,
            status=SessionStatus.RECEIVED,
            audio_path=str(path),
            created_at=datetime.now(UTC),
        )
    )
    background.add_task(runtime.processor.process, session_id)
    return _accepted(session_id, SessionStatus.RECEIVED)


def _accepted(session_id: str, state: SessionStatus) -> SessionAccepted:
    return SessionAccepted(
        session_id=session_id, status=state, status_url=f"/api/sessions/{session_id}/status"
    )


def _parse(model: type[Model], raw: str) -> Model:
    try:
        return model.model_validate_json(raw)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            [
                {"loc": ["metadata", *e["loc"]], "msg": e["msg"], "type": e["type"]}
                for e in error.errors()
            ],
        ) from error


def _person(runtime: Runtime, person_id: str) -> Person:
    person = runtime.store.get_person(person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown person")
    return person


def _session(runtime: Runtime, session_id: str) -> SessionRecord:
    record = runtime.store.get_session(session_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown session")
    return record


def _require_language(language: str) -> None:
    try:
        get_adapter(language)
    except UnsupportedLanguageError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"language {language!r} is not supported yet"
        ) from error


def _suffix(audio: UploadFile) -> str:
    suffix = Path(audio.filename or "").suffix.lower()
    if _SUFFIX.match(suffix):
        return suffix
    content_type = (audio.content_type or "").split(";")[0].strip().lower()
    return _SUFFIX_BY_TYPE.get(content_type, "")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


app = create_app()
