# ChronoVoice Brain

Solution HealthTech développée pour le **Future Health Digital Innovation Challenge — Challenge 08 : Protecting Brain Health Earlier** (Abu Dhabi).

ChronoVoice Brain transforme des enregistrements de **récits de vie** de personnes âgées en **biomarqueurs vocaux et linguistiques longitudinaux**, afin de repérer tôt les signaux de changement cognitif sans test clinique anxiogène ni biais culturel. Chaque personne est comparée **à sa propre référence personnelle** dans le temps, jamais à une norme de population.

> **Outil d’aide au repérage uniquement — non diagnostique.**  
> Aucune donnée réelle de patient n’est présente dans ce dépôt : l’ensemble des personas et séances de démonstration est synthétique (`synthetic: true`).

---

## Architecture du pipeline

Le traitement d’une séance suit un pipeline en 5 étapes strictement typé par les contrats Pydantic v2 de [`backend/app/schemas.py`](backend/app/schemas.py) :

```text
Enregistrement audio + métadonnées (RecordingMetadata)
  → [0] Capture & qualité      (ElevenLabs Scribe v3 + calcul)  → SessionTranscript, QualityReport
  → [1] Marqueurs              (calcul déterministe pur)          → SessionMetrics
  → [2] Analyste du récit      (LLM, expérimental, hors index)    → NarrativeAnalysis
  → [3] Dérive longitudinale   (statistique, Crawford & Howell)   → LongitudinalComparisonResult
  → [4] Synthèse clinique      (LLM contraint, supervision humaine)→ ClinicalSummaryReport
  → Interface soignant (soins primaires)
```

- **Seulement deux étapes LLM** (étapes 2 et 4) : toute mesure et toute décision de niveau d’orientation reposent sur des calculs déterministes.
- **Conception multilingue** : tout traitement dépendant de la langue passe par un `LanguageAdapter` ([`backend/app/language/`](backend/app/language/)); le prototype implémente l’adaptateur anglais (`eng`) via `spaCy` (`en_core_web_sm`) et `wordfreq`.

### Principes de sécurité clinique

1. **Jamais de diagnostic** : le vocabulaire diagnostique est bloqué par validation sur `ClinicalSummaryReport`.
2. **Baseline personnelle obligatoire** : aucun niveau d’orientation n’est émis avant 3 séances `usable` de référence (`building_baseline`), et l’incertitude accompagne chaque score.
3. **Traçabilité scientifique** : chaque métrique, seuil et recommandation de prévention cite sa source vérifiée (PubMed / Crossref) ou est explicitement documenté comme choix de conception.
4. **Supervision humaine** : toute synthèse clinique reste au statut `draft` jusqu’à validation explicite par le soignant.
5. **Données synthétiques uniquement** : aucun audio ni donnée réelle de patient dans le dépôt.

---

## Structure du dépôt

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py              # Point d'entrée FastAPI (GET /health)
│   │   ├── schemas.py           # Contrats Pydantic v2 et règles cliniques
│   │   ├── demo_data.py         # Chargement et analyse des personas synthétiques
│   │   ├── agents/              # Étapes du pipeline (capture, segmentation, markers, drift, pipeline)
│   │   └── language/            # Adaptateurs de langue (base + anglais)
│   ├── data/
│   │   ├── prompts.json         # Banque de questions d'amorce et relances
│   │   └── synthetic/           # Personas, paramètres, récits et 30 séances générées
│   ├── scripts/                 # Génération synthétique, rapport de trajectoires, simulation Monte Carlo
│   └── tests/                   # Suite pytest (pipeline, contrats, données synthétiques, OKF)
├── frontend/                    # Dashboard soignant (Vite + React + TS, à échafauder)
├── docs/                        # Base de connaissances OKF v0.2 (discovery, specs v1, tech, log)
├── CLAUDE.md                    # Guide complet du projet et conventions
├── AGENTS.md                    # Règles de référence pour les agents
└── TODO.md                      # Suivi jusqu'à la remise du 20 novembre 2026
```

---

## Démarrage rapide (Backend)

Prérequis : Python 3.12 et [`uv`](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
```

### Lancer l’API

```bash
cd backend
uv run uvicorn app.main:app --reload
# http://127.0.0.1:8000/health
```

### Tests, lint et typage

```bash
cd backend
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy app
```

### Scripts utiles (données synthétiques et simulation)

```bash
cd backend
# Vérifier les trajectoires mesurées sur les 3 personas synthétiques
uv run python -m scripts.report_synthetic_trajectories

# Régénérer les séances synthétiques depuis stories/ et generation_params.json
uv run python -m scripts.generate_synthetic_data

# Simulation Monte Carlo des règles d'orientation (étape 3)
uv run python -m scripts.simulate_orientation_rules
```

---

## Documentation et spécifications

La documentation suit le format **Open Knowledge Format (OKF v0.2)**, à parcourir depuis [`docs/index.md`](docs/index.md) :

- **Vue d’ensemble et périmètre** : [`docs/specs/overview.md`](docs/specs/overview.md)
- **Spécification du pipeline (étapes 0–4)** : [`docs/specs/pipeline.md`](docs/specs/pipeline.md)
- **API, stockage et intégration externe** : [`docs/specs/api.md`](docs/specs/api.md)
- **Interface soignant et micro** : [`docs/specs/clinician-ui.md`](docs/specs/clinician-ui.md)
- **Données synthétiques** : [`docs/specs/synthetic-data.md`](docs/specs/synthetic-data.md)
- **Synthèse scientifique et études** : [`docs/discovery/synthesis.md`](docs/discovery/synthesis.md)
- **Références techniques (Scribe v3, licences tierces)** : [`docs/tech/index.md`](docs/tech/index.md)
- **Journal des décisions** : [`docs/log.md`](docs/log.md)

---

## État d’avancement

- [x] Base de connaissances OKF v0.2, discovery scientifique et spécifications v1
- [x] Contrats Pydantic v2 ([`backend/app/schemas.py`](backend/app/schemas.py))
- [x] Étape 0 déterministe (`capture.py`), étape 1 (`segmentation.py`, `markers.py`), étape 3 (`drift.py`)
- [x] Données synthétiques des 3 personas (Margaret Hale, Rajesh Menon, Grace Santos) et tests associés
- [ ] Client ElevenLabs Scribe v3 (étape 0 réseau) et calibration audio
- [ ] Étapes LLM 2 (analyste du récit) et 4 (synthèse clinique)
- [ ] Endpoints API complets, persistance SQLite et intégration externe
- [ ] Frontend soignant (Vite + React + TypeScript + Tailwind + Recharts)
