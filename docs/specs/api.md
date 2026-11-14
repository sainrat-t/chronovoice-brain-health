---
type: spec
title: API, stockage et intégration — spec v1
description: Endpoints FastAPI du prototype, traitement asynchrone des séances, stockage SQLite, suppression de l'audio et endpoint d'intégration pour une application externe (MyMémoires).
status: draft
tags: [specs, api, fastapi, storage, integration, mymemoires]
generated: "2026-11-12"
---

# API, stockage et intégration : spec v1

> Spec v1 du 2026-11-12, issue des questions Q17 et Q24 à Q28 du [questionnaire](questions.md). Les objets échangés sont les modèles de [pipeline.md](pipeline.md) (section « Contrats entre étapes »).

## 1. Principes

- **Un seul service** : FastAPI expose l'API sous `/api` et sert le frontend construit (Q24).
- **Pydantic v2** à toutes les frontières. Le JSON est en snake_case.
- **Pas de compte dans la démo** (accès invité). L'endpoint d'intégration est protégé par une clé d'API partagée, passée dans l'en-tête `X-Integration-Key`.
- **Secrets** : `ELEVENLABS_API_KEY`, `MISTRAL_API_KEY` (ou `ANTHROPIC_API_KEY`) et `INTEGRATION_API_KEY` viennent de variables d'environnement (`backend/.env`, jamais commité). Les réglages du modèle sont dans [pipeline.md](pipeline.md), « Appel au modèle ».

## 2. Endpoints

| Méthode et chemin | Rôle | Réponse |
|---|---|---|
| `GET /health` | état du service | `{status, phase}` |
| `GET /api/people` | liste des personnes avec leur niveau d'orientation | liste de `PersonSummary` |
| `POST /api/people` | créer une personne (pseudonyme, année de naissance, langue) | `Person` |
| `GET /api/people/{person_id}` | fiche complète : profil de risque, trajectoire, dernière synthèse | `PersonDetail` |
| `GET /api/people/{person_id}/trajectory` | marqueurs, index et sous-scores dans le temps, référence et niveaux | `Trajectory` |
| `POST /api/people/{person_id}/sessions` | nouvelle séance : audio en multipart, plus `RecordingMetadata` | `202` et `{session_id, status}` |
| `GET /api/sessions/{session_id}` | détail de la séance : transcription, qualité, marqueurs, comparaison, récit | `SessionDetail` |
| `GET /api/sessions/{session_id}/status` | avancement du traitement | `{status, step, error?}` |
| `POST /api/sessions/{session_id}/retry` | relancer une séance `failed` dont l'audio est encore là (ajouté le 2026-11-14) | `202` et `{session_id, status}` |
| `POST /api/people/{person_id}/summary/review` | le soignant valide la synthèse (nom, date) | `ClinicalSummaryReport` |
| `GET /api/prompts?person_id=…` | une question d'amorce jamais posée à cette personne, et ses relances | `Prompt` |
| `POST /api/integrations/recordings` | une application externe dépose un enregistrement | `202` et `{session_id, status}` |

## 3. Traitement asynchrone d'une séance

Statuts successifs : `received → transcribing → analysing → summarising → done`. Deux autres issues sont possibles : `rejected` (contrôle qualité, avec ses raisons) et `failed` (erreur technique, avec un message).

- **Exécution** : le traitement tourne en tâche de fond (`BackgroundTasks` de FastAPI). Ça suffit pour un prototype à une seule instance.
- **Suivi** : le frontend interroge `/status` toutes les 2 secondes.
- **Erreurs** :
  - Si Scribe échoue, on fait un nouvel essai, puis la séance passe en `failed` ; l'audio est gardé pour pouvoir relancer (`POST /api/sessions/{session_id}/retry`).
  - Si l'étape 2 ou 4 échoue, les marqueurs et le niveau restent valables. La séance passe en `done`, avec la mention « summary unavailable ».
- **Cible** : moins de 2 minutes pour 5 minutes d'audio (Q17).

## 4. Stockage (Q25)

- **SQLite**, un seul fichier dans `backend/data/`.
- Tables :
  - `people` ;
  - `sessions` (métadonnées, statut, qualité) ;
  - `session_results` (transcription de la personne, marqueurs, comparaison, récit, en JSON validé par Pydantic) ;
  - `summaries` ;
  - `risk_profiles`.
- **Audio** :
  - écrit dans un dossier temporaire ;
  - **supprimé dès que la transcription est enregistrée** ;
  - la transcription est ensuite supprimée chez ElevenLabs (`DELETE /v1/speech-to-text/transcripts/{id}`).
- **Personas** : leurs séances sont chargées au démarrage depuis `backend/data/synthetic/` ([synthetic-data.md](synthetic-data.md)), avec `synthetic: true`.
- **Remise à zéro** : une commande remet la base dans l'état de la démo, pour pouvoir rejouer le scénario.

## 5. Endpoint d'intégration : module branchable (Q28)

`POST /api/integrations/recordings` montre comment une application qui enregistre déjà de la parole, comme MyMémoires, envoie ses enregistrements à ChronoVoice.

**Requête** : multipart avec :

- `audio` : le fichier ;
- `metadata` : un JSON qui contient :
  - `source_app`, par exemple `"mymemoires"` ;
  - `external_person_id` : l'identifiant de la personne dans l'application source, que l'API associe à une personne ChronoVoice et crée si elle n'existe pas ;
  - `task_type`, `language`, `consent`, `recorded_at` ;
  - en option, `target_speaker_hint` (quelle voix suivre) et `context`.

**Réponse** : `202`, avec `session_id` et l'URL de suivi.

**Webhook sortant** : hors prototype. On le documente dans le deck comme prochaine étape.

L'endpoint sera documenté dans l'OpenAPI générée par FastAPI (`/docs`), avec un exemple d'appel `curl` dans le README du backend.

## 6. Mise en ligne

- **Plateforme** : **Render** (choisi le 2026-11-12), avec un seul service web pour le backend et le frontend construit.
  - Prendre l'offre payante d'entrée pendant l'évaluation, du 20 au 30 novembre : l'offre gratuite se met en veille, et le premier chargement serait lent pour le jury.
  - Vercel a été écarté. D'après sa doc, une requête est limitée à 4,5 Mo, une fonction dure au plus 300 s sur l'offre gratuite, et il n'y a pas de fichier SQLite persistant. Il aurait fallu Vercel Blob pour l'audio, un découpage en 3 appels et une base Postgres ([Vercel Functions Limits](https://vercel.com/docs/functions/limitations)).
- **HTTPS obligatoire**, pour l'accès au micro dans le navigateur.
- **Disque persistant** (ajouté le 2026-11-14) : sur Render, le système de fichiers d'un service est effacé à chaque redémarrage ou déploiement. Sans disque persistant pour la base SQLite, la base revient à l'état de la démo, et les séances enregistrées pendant l'évaluation sont perdues. À décider lors de la mise en ligne.
- **Variables d'environnement** sur la plateforme ; aucune clé dans le dépôt (Q26 : dépôt GitHub privé).

## 7. Précisions du 2026-11-14, avant le code

Choix faits en codant l'API. Ils complètent les sections précédentes sans les contredire.

### Code

| Module | Rôle |
|---|---|
| `app/agents/transcription.py` | client Scribe, la partie réseau de l'étape 0 |
| `app/api/models.py` | modèles des réponses de l'API. `schemas.py` reste le contrat entre les étapes du pipeline |
| `app/store.py` | stockage SQLite |
| `app/processing.py` | traitement d'une séance, du fichier audio à la synthèse |
| `app/demo.py` | chargement des personas dans la base |
| `app/main.py` | les routes |

### Transcription

- **Appel HTTP direct** à `POST /v1/speech-to-text`, avec `httpx`, plutôt que le SDK `elevenlabs` : une dépendance de moins, et les noms d'arguments du SDK n'avaient pas été vérifiés ([elevenlabs-scribe.md](../tech/elevenlabs-scribe.md), section 8).
- **Réglages** : ceux de [elevenlabs-scribe.md](../tech/elevenlabs-scribe.md), section 3. `num_speakers=2` pour une séance enregistrée dans l'interface (la personne et le soignant) ; omis pour une intégration, dont on ne sait pas combien de voix elle contient.
- **Délai** : 300 s par appel.
- **Après l'enregistrement de la transcription** : l'audio est supprimé chez nous, puis la transcription chez ElevenLabs. Un échec de cette suppression est noté dans le journal du serveur, sans faire échouer la séance.

### Envoi d'une séance par le soignant

- **Multipart** : `audio` (le fichier) et `metadata` (un JSON) avec le consentement, le contexte, l'id de la question d'amorce et, en option, la date d'enregistrement (par défaut, l'heure de réception).
- **La personne et sa langue** viennent de la fiche de la personne.
- **Fichier** : au plus 100 Mo ; 15 minutes en opus font environ 15 Mo. Le format est contrôlé par Scribe.

### Ce qui est stocké, et ce qui est recalculé

- **Stocké** : la personne, son profil de risque, les métadonnées et le statut de chaque séance, la transcription, le contrôle qualité, les marqueurs, l'analyse du récit et la synthèse.
- **Recalculé à chaque lecture** : l'étape 3. C'est un calcul pur et rapide, qui ne dépend que des séances de la personne ; le stocker risquerait de garder une comparaison périmée.
- **Limite** : une séance arrivée en retard, avec une date antérieure à d'autres, change la comparaison des séances suivantes ; leurs synthèses, déjà écrites, ne sont pas réécrites.
- **Une personne à la fois** : les étapes 2 à 4 d'une même personne ne tournent pas en parallèle, car chaque séance s'appuie sur les précédentes.

### Base de données

- **Fichier** : `CHRONOVOICE_DB`, par défaut `backend/data/chronovoice.sqlite3`. Il est exclu de git : les séances enregistrées pendant une démo n'entrent jamais dans le dépôt.
- **Démarrage** : si la base est vide, les personas y sont chargées. Une séance restée en cours lors d'un arrêt du serveur passe en `failed`, avec le message « interrupted ».
- **Remise à zéro** : `uv run python -m scripts.reset_demo`.

### Personas : textes des modèles figés

- **Les textes des étapes 2 et 4** des personas sont générés une fois, par `scripts/build_demo_snapshot.py`, avec le modèle retenu. Ils sont enregistrés dans `backend/data/synthetic/llm_snapshot/<personne>.json`.
- **Pourquoi** :
  - le serveur démarre en quelques secondes, au lieu d'une cinquantaine d'appels au modèle ;
  - le jury voit les mêmes textes à chaque redémarrage ;
  - Thibaut peut les relire avant la démo.
- **Au chargement**, chaque texte repasse par la validation Pydantic. Une synthèse dont le niveau ne correspond plus au niveau recalculé (si le code de l'étape 3 a changé depuis) est remplacée par le texte fixe.
- **Sans ces fichiers**, les personas n'ont pas d'analyse du récit, et leurs synthèses sont le texte fixe.
- Les séances enregistrées en direct appellent le modèle normalement.

### Personnes

- **Création** : la langue doit avoir un adaptateur (seul `eng` en a un aujourd'hui) ; sinon, refus `422`. L'année de naissance est facultative.
- **Liste** : le niveau d'une personne est celui de sa dernière séance comparée. Ordre : `review_recommended`, puis `monitor`, puis les autres, puis par nom.

### Question d'amorce

- Un thème tiré au hasard parmi ceux jamais posés à la personne.
- Le paramètre `exclude` écarte les thèmes déjà proposés à l'écran, pour le bouton « tirer un autre thème ».
- Si tous ont servi, on reprend celui posé il y a le plus longtemps.

### Validation de la synthèse

- **Corps** : `{reviewed_by}` ; la date est celle du serveur.
- **Cible** : la synthèse de la dernière séance traitée de la personne.
- **Refus** : `404` s'il n'y a pas de synthèse ; `409` si elle est déjà validée.

### Intégration

- **Clé** : sans `INTEGRATION_API_KEY` configurée, l'endpoint répond `503` ; avec une mauvaise clé, `401`.
- **Personne créée** : son nom est `display_name` s'il est fourni dans les métadonnées, sinon `<source_app> <external_person_id>`.

### Détail d'une séance

- Il contient une **transcription annotée**, calculée par le code : les tours de chaque voix, et pour la personne suivie, les hésitations, les mots coupés, les répétitions, les pauses ≥ 250 ms avec leur durée, et les événements sonores. Le frontend n'a qu'à l'afficher.
