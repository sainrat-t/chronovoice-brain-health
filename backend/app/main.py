"""ChronoVoice Brain API entrypoint."""

from fastapi import FastAPI

app = FastAPI(
    title="ChronoVoice Brain API",
    version="0.1.0",
    description=(
        "Longitudinal speech and language biomarkers from life-story recordings, "
        "for early detection of cognitive change. Screening support only - non-diagnostic."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. `phase` tracks the project stage (see CLAUDE.md)."""
    return {"status": "ok", "phase": "prototype"}
