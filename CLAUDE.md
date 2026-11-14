# ChronoVoice Brain — CLAUDE.md

Solution HealthTech pour le **Future Health Digital Innovation Challenge — Challenge 08 : Protecting Brain Health Earlier**.

Idée : transformer des enregistrements de **récits de vie** de personnes âgées en **biomarqueurs vocaux et linguistiques longitudinaux**, pour repérer tôt les signes de déclin cognitif (MCI / Alzheimer) sans test clinique anxiogène ni biais culturel. On compare chaque personne **à elle-même** dans le temps, pas à une norme de population.

**Cadre du challenge** : énoncé, règles, critères du jury et template de soumission dans [`docs/challenge.md`](docs/challenge.md). **Prototype à rendre le 20 novembre 2026**, pour une population cible à **Abu Dhabi**. Aucune donnée n'est fournie par les organisateurs.

---

## Phase actuelle : PROTOTYPE (remise le 20 novembre 2026)

La discovery scientifique a été close le 2026-11-12, par manque de temps : le prototype est à rendre 8 jours plus tard.

- **Ce qu'on code** est défini par les specs v1 dans [`docs/specs/`](docs/specs/index.md) : vue d'ensemble, pipeline, interface soignant et micro, API, données synthétiques. Le calendrier est dans [`TODO.md`](TODO.md).
- **La discovery reste la source des preuves.** Les fiches d'études, la synthèse et l'architecture v0.3 sont dans [`docs/discovery/`](docs/discovery/index.md), avec le protocole dans [`docs/discovery/README.md`](docs/discovery/README.md). La lecture continue seulement sur les fiches 07 et 09 ; un passage qui change une spec est noté dans la fiche, puis dans la synthèse.
- **Toute référence citée (fiche, code, pitch) doit être vérifiée** via l'API PubMed (E-utilities) ou Europe PMC avant d'être écrite. La liste de départ contenait des identifiants faux pour 4 études sur 5.

## Base de connaissances — Open Knowledge Format (OKF v0.2)

Toute la connaissance projet (`docs/`) est structurée selon l'**Open Knowledge Format (OKF v0.2)** :

- **Point d'entrée du bundle** : [`docs/index.md`](docs/index.md) (`okf_version: "0.2"`), relayé par les index de sous-dossiers ([`docs/discovery/index.md`](docs/discovery/index.md), [`docs/discovery/studies/index.md`](docs/discovery/studies/index.md)).
- **Lecture par *progressive disclosure*** : les agents commencent par lire `docs/index.md`, descendent via l'`index.md` du dossier concerné, puis ouvrent uniquement les fiches utiles au lieu de charger tout `docs/`.
- **Frontmatter YAML obligatoire** sur chaque `.md` de `docs/` :
  - `type` (obligatoire, ex. `index`, `log`, `challenge-spec`, `protocol`, `architecture-synthesis`, `literature-candidates`, `study-note`, `biomarker`, `safeguard`) ;
  - `title`, `description`, `status` (`draft` | `stable` | `deprecated`), `tags` ;
  - signaux de confiance v0.2 : `sources` et `verified` (obligatoires pour toute étude ou métrique sourcée) ou `generated`, et `stale_after` si applicable.
- **Maintenance & journalisation** : tout ajout, suppression, renommage ou décision structurante dans `docs/` met à jour l'`index.md` parent et ajoute une entrée en tête de [`docs/log.md`](docs/log.md) (groupée par `## YYYY-MM-DD`).
- **Validation** : `backend/tests/test_okf.py` (exécuté via `uv run pytest`) vérifie la présence de `docs/index.md` (`okf_version: "0.2"`), `docs/log.md`, la validité du frontmatter OKF et l'absence de liens Markdown internes cassés dans `docs/`.

## Architecture (v0.3, précisée par les specs v1)

```
Enregistrement (micro ou intégration) + métadonnées
  → [0] Capture et qualité   ElevenLabs Scribe v3 + calcul   → SessionTranscript, QualityReport
  → [1] Marqueurs            calcul pur                       → SessionMetrics
  → [2] Analyste du récit    LLM (Mistral ou Claude), expérimental → NarrativeAnalysis
  → [3] Dérive               statistique                      → LongitudinalComparisonResult
  → [4] Synthèse clinique    LLM (Mistral ou Claude), contraint → ClinicalSummaryReport
  → Interface soignant (soins primaires)
```

- **Spec détaillée** : [`docs/specs/pipeline.md`](docs/specs/pipeline.md).
- **Justification scientifique** : [`docs/discovery/synthesis.md`](docs/discovery/synthesis.md), section 4.
- **Seulement 2 étapes LLM.** Tout ce qui est une mesure est du calcul déterministe. Le LLM rédige ; il ne décide jamais du niveau d'orientation. Ce qui est déjà décidé ou chiffré (titre de la synthèse, phrase sur l'incertitude, suite proposée à la personne) est écrit par le code, pas par le LLM.
- **La réponse d'un LLM est une donnée non fiable.** Elle est vérifiée contre la transcription et les mesures avant d'être gardée (citations retrouvées dans la transcription, marqueurs existants, vocabulaire interdit), et un passage affiché est toujours le texte de la transcription, jamais celui du modèle. Les tests n'appellent jamais le réseau : ils utilisent `tests/llm_doubles.py`.

**Décisions produit (2026-11-12)** :

- Prototype et démo **en anglais**, pour une population anglophone. Conception **multilingue** : tout ce qui dépend de la langue passe par un adaptateur.
- ChronoVoice est un **module branchable** sur toute action qui produit un enregistrement de parole. Premier cas d'intégration : MyMémoires.
- Transcription : **ElevenLabs Scribe v3** (verbatim, horodatage par mot, séparation des voix). Réglages, format de réponse et limites dans [`docs/tech/elevenlabs-scribe.md`](docs/tech/elevenlabs-scribe.md) ; ne jamais activer `no_verbatim`.
- Pas de contrainte RGPD sur les choix techniques : les LLM peuvent être appelés par API. Les données restent synthétiques (règle 3).

**Contrat d'interface** : [`backend/app/schemas.py`](backend/app/schemas.py). Il contient :

- les modèles d'entrée : `RecordingMetadata`, `RecordingContext` ;
- les sorties des étapes : `SessionTranscript`, `QualityReport`, `SessionMetrics`, `NarrativeAnalysis`, `LongitudinalComparisonResult`, `ClinicalSummaryReport` ;
- `RiskProfile`.

Les règles 1 et 5 de sécurité clinique y sont vérifiées par validation : vocabulaire diagnostique interdit, et pas de niveau d'orientation sans 3 séances de référence. Un niveau ne peut pas non plus contredire le nombre de marqueurs significatifs sur lequel il repose.

## Monorepo

```
backend/    Python 3.12, FastAPI, Pydantic v2 (géré avec uv)
              app/schemas.py   contrat entre les étapes
              app/main.py      routes de l'API (docs/specs/api.md) ; configuration lue dans les variables d'environnement
              app/api/         modèles des réponses (models.py), vues (views.py), transcription annotée (transcript_view.py)
              app/store.py     stockage SQLite (CHRONOVOICE_DB, par défaut data/chronovoice.sqlite3, exclu de git)
              app/processing.py traitement d'une séance en tâche de fond, du fichier audio à la synthèse
              app/demo.py      chargement des personas, avec les textes figés des étapes 2 et 4 (data/synthetic/llm_snapshot/)
              app/prompts.py   banque des questions d'amorce
              app/agents/      étapes du pipeline (transcription.py = appel à Scribe, capture.py = reste de l'étape 0, segmentation.py et markers.py = étape 1,
                               narrative.py = étape 2, drift.py = étape 3, summary.py = étape 4,
                               passages.py = vérification des citations, pipeline.py = enchaînement des étapes 0 et 1)
              app/llm/         modèle des étapes 2 et 4 : contrat commun LLMClient (base.py), Mistral (mistral.py), Claude (claude.py) ;
                               fournisseur choisi par LLM_PROVIDER ou par la clé présente dans backend/.env
              app/language/    adaptateurs de langue (anglais : spaCy + wordfreq)
              app/demo_data.py lecture des personas et séances synthétiques
              data/            prompts.json (questions d'amorce) et synthetic/ (3 personas, 30 séances générées)
              scripts/         données synthétiques, rapport des trajectoires, simulation des règles, essai réel des LLM,
                               textes figés des personas (build_demo_snapshot), remise à zéro de la démo (reset_demo)
frontend/   Vite + React + TypeScript + Tailwind + Lucide + Recharts : interface soignant (docs/specs/clinician-ui.md)
              src/api/         types générés depuis l'OpenAPI du backend (schema.d.ts), alias (types.ts), appels (client.ts)
              src/pages/       les 5 écrans ; src/components/ sections et graphiques ; src/lib/ utilitaires, micro
docs/       base de connaissances OKF v0.2 (racine docs/index.md) : discovery, tech, challenge
```

## Commandes

### Backend (depuis `backend/`)

```bash
uv sync                                    # installe Python 3.12 + dépendances
uv run --env-file .env uvicorn app.main:app --reload  # API sur http://127.0.0.1:8000 (/health, /api, /docs)
uv run --env-file .env python -m scripts.reset_demo   # remet la base dans l'état de la démo
uv run pytest                              # tests
uv run ruff check . && uv run ruff format . # lint + format
uv run mypy app                            # typage strict
```

### Frontend (depuis `frontend/`)

```bash
npm install
VITE_API_TARGET=http://127.0.0.1:8000 npm run dev  # http://localhost:5173, /api renvoyé vers le backend
npm run build      # frontend/dist, servi ensuite par FastAPI
npm run lint && npm run typecheck
npm run gen:api    # après un changement du backend : régénère les types (après scripts.export_openapi)
```

## Règles de développement

### Sécurité clinique (non négociable)

1. **Jamais de diagnostic.** Le produit repère et oriente ; il ne diagnostique pas. Vocabulaire interdit dans les sorties : « diagnostic », « le patient a Alzheimer », « démence confirmée ». Vocabulaire attendu : « signaux à surveiller », « écart à la baseline personnelle », « une consultation mémoire peut être utile ». (Un logiciel qui pose un diagnostic devient un dispositif médical de classe IIa ou plus sous le MDR européen.)
2. **Chaque métrique, seuil ou pondération cite sa source** : une fiche de `docs/discovery/studies/` ou une référence (auteurs, année, DOI). Pas de « nombre magique » sans référence en commentaire ou docstring.
3. **Pas de données réelles de patient** dans le dépôt. Uniquement des données synthétiques, marquées comme telles (`"synthetic": true`).
4. **Pas de comparaison à une norme de population quand une baseline personnelle existe.** Le signal principal, c'est l'écart intra-individuel ; les normes de population servent seulement de contexte.
5. Toujours afficher l'**incertitude** (intervalle, nombre de sessions de baseline, qualité de l'audio) avec un score. Avec moins de 3 sessions de baseline, on n'affiche pas d'alerte.

### Code

- Identifiants, docstrings, commentaires de code et **nouvelle documentation** (à partir du 2026-11-13, `README.md` inclus) en **anglais**. Les documents historiques de discovery/specs v1 déjà rédigés restent en français.
- Python : typage complet (`mypy --strict`), Pydantic v2 pour toute donnée qui passe une frontière (API, agents, fichiers JSON). Les calculs de métriques sont des **fonctions pures**, testées sur des cas connus calculés à la main.
- Les agents échangent **uniquement** des modèles Pydantic de `schemas.py`, jamais de dict libres.
- On ajoute une dépendance lourde (Whisper, spaCy, sentence-transformers…) seulement quand l'agent qui en a besoin est validé. Chaque composant tiers ajouté est inscrit, avec sa licence vérifiée, dans [`docs/tech/third-party-components.md`](docs/tech/third-party-components.md).
- TypeScript en `strict`. Les types du frontend reflètent `schemas.py` (même nommage de champs, en snake_case dans le JSON).

### Méthode de travail

- **On valide chaque étape avec l'utilisateur avant de passer à la suivante.** On livre une étape, on s'arrête, on attend la validation.
- Une hypothèse d'architecture remise en cause par une étude doit être notée dans `docs/discovery/synthesis.md` (section « Hypothèses ») avant d'être codée.
- Un écart entre le code et une spec de `docs/specs/` se règle en mettant d'abord la spec à jour, puis le code.

## Identité visuelle (dashboard)

Palette sobre : **ardoise** (texte, structure), **sauge / vert doux** (état stable, baseline), **terracotta** (alertes, écarts significatifs). Typographie soignée, beaucoup d'air, pas de rouge alarmiste : le public est clinique, mais le patient peut voir l'écran.
