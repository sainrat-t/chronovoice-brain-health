# ChronoVoice Brain

HealthTech solution built for the **Future Health Digital Innovation Challenge — Challenge 08: Protecting Brain Health Earlier** (Abu Dhabi).

ChronoVoice Brain turns **life-story voice recordings** from older adults into **longitudinal speech and language biomarkers** to detect early signs of cognitive change without anxiety-inducing clinical tests or cultural bias. Each person is compared **against their own personal baseline** over time rather than a population norm.

> **Screening support only — not a diagnostic tool.**  
> No real patient data is stored in this repository: all demo personas and sessions are synthetic (`synthetic: true`).

---

## Pipeline Architecture

Each recording session flows through a 5-step pipeline strictly typed with the Pydantic v2 contracts in [`backend/app/schemas.py`](backend/app/schemas.py):

```text
Audio recording + metadata (RecordingMetadata)
  → [0] Capture & quality      (ElevenLabs Scribe v3 + rules)     → SessionTranscript, QualityReport
  → [1] Markers                (pure deterministic computation)    → SessionMetrics
  → [2] Narrative analyst      (LLM, experimental, outside index)  → NarrativeAnalysis
  → [3] Longitudinal drift     (statistics, Crawford & Howell)     → LongitudinalComparisonResult
  → [4] Clinical summary       (constrained LLM, human oversight)  → ClinicalSummaryReport
  → Clinician dashboard (primary care)
```

- **Only two LLM steps** (steps 2 and 4): all measurements and orientation level decisions are deterministic.
- **Multilingual design**: all language-specific processing sits behind a `LanguageAdapter` ([`backend/app/language/`](backend/app/language/)); the prototype implements the English adapter (`eng`) using `spaCy` (`en_core_web_sm`) and `wordfreq`.

### Clinical Safety Rules

1. **No diagnosis**: diagnostic vocabulary is blocked by schema validation on `ClinicalSummaryReport`.
2. **Personal baseline required**: no orientation level is issued before 3 `usable` baseline sessions (`building_baseline`), and uncertainty is displayed alongside every score.
3. **Scientific traceability**: every metric, threshold, and prevention note cites a verified source (PubMed / Crossref) or is explicitly documented as a design choice.
4. **Human oversight**: every clinical summary remains a `draft` until explicitly validated by a clinician.
5. **Synthetic data only**: no real patient audio or data is committed to the repository.

---

## Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint (GET /health)
│   │   ├── schemas.py           # Pydantic v2 contracts and clinical safety validators
│   │   ├── demo_data.py         # Synthetic persona and session loader/runner
│   │   ├── agents/              # Pipeline steps (capture, segmentation, markers, drift, pipeline)
│   │   └── language/            # Language adapters (protocol + English)
│   ├── data/
│   │   ├── prompts.json         # Life-story prompt bank and follow-ups
│   │   └── synthetic/           # Personas, generation params, stories, and 30 generated sessions
│   ├── scripts/                 # Synthetic data generator, trajectory report, Monte Carlo simulation
│   └── tests/                   # pytest suite (pipeline, schemas, synthetic data, OKF docs)
├── frontend/                    # Clinician dashboard (Vite + React + TS, to be scaffolded)
├── docs/                        # OKF v0.2 knowledge bundle (discovery, specs v1, tech, log)
├── CLAUDE.md                    # Full project guide and development rules
├── AGENTS.md                    # Reference instructions for coding agents
└── TODO.md                      # Schedule through the November 20, 2026 submission
```

---

## Quick Start (Backend)

Prerequisites: Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
```

### Run the API

```bash
cd backend
uv run uvicorn app.main:app --reload
# http://127.0.0.1:8000/health
```

### Tests, Linting, and Type Checking

```bash
cd backend
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy app
```

### Utility Scripts (Synthetic Data & Simulation)

```bash
cd backend
# Inspect measured trajectories on the 3 synthetic personas
uv run python -m scripts.report_synthetic_trajectories

# Regenerate synthetic sessions from stories/ and generation_params.json
uv run python -m scripts.generate_synthetic_data

# Monte Carlo check of step 3 orientation rules
uv run python -m scripts.simulate_orientation_rules
```

---

## Documentation & Specifications

Project documentation follows the **Open Knowledge Format (OKF v0.2)**, rooted at [`docs/index.md`](docs/index.md) (historical discovery/v1 spec files are in French; new documentation is written in English):

- **Overview & scope**: [`docs/specs/overview.md`](docs/specs/overview.md)
- **Pipeline specification (steps 0–4)**: [`docs/specs/pipeline.md`](docs/specs/pipeline.md)
- **API, storage & integration**: [`docs/specs/api.md`](docs/specs/api.md)
- **Clinician UI & microphone capture**: [`docs/specs/clinician-ui.md`](docs/specs/clinician-ui.md)
- **Synthetic demo data**: [`docs/specs/synthetic-data.md`](docs/specs/synthetic-data.md)
- **Scientific synthesis & studies**: [`docs/discovery/synthesis.md`](docs/discovery/synthesis.md)
- **Technical references (Scribe v3, third-party licenses)**: [`docs/tech/index.md`](docs/tech/index.md)
- **Knowledge log**: [`docs/log.md`](docs/log.md)

---

## Current Status

- [x] OKF v0.2 knowledge bundle, scientific discovery, and v1 specifications
- [x] Pydantic v2 contracts ([`backend/app/schemas.py`](backend/app/schemas.py))
- [x] Deterministic step 0 (`capture.py`), step 1 (`segmentation.py`, `markers.py`), and step 3 (`drift.py`)
- [x] Synthetic data for 3 demo personas (Margaret Hale, Rajesh Menon, Grace Santos) and trajectory tests
- [ ] ElevenLabs Scribe v3 client (step 0 network integration) and audio calibration
- [ ] LLM steps 2 (narrative analyst) and 4 (clinical summary)
- [ ] Full FastAPI endpoints, SQLite persistence, and external integration endpoint
- [ ] Clinician frontend (Vite + React + TypeScript + Tailwind + Recharts)
