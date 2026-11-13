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
- **Secrets** : `ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY` et `INTEGRATION_API_KEY` viennent de variables d'environnement (`backend/.env`, jamais commité).

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
| `POST /api/people/{person_id}/summary/review` | le soignant valide la synthèse (nom, date) | `ClinicalSummaryReport` |
| `GET /api/prompts?person_id=…` | une question d'amorce jamais posée à cette personne, et ses relances | `Prompt` |
| `POST /api/integrations/recordings` | une application externe dépose un enregistrement | `202` et `{session_id, status}` |

## 3. Traitement asynchrone d'une séance

Statuts successifs : `received → transcribing → analysing → summarising → done`. Deux autres issues sont possibles : `rejected` (contrôle qualité, avec ses raisons) et `failed` (erreur technique, avec un message).

- **Exécution** : le traitement tourne en tâche de fond (`BackgroundTasks` de FastAPI). Ça suffit pour un prototype à une seule instance.
- **Suivi** : le frontend interroge `/status` toutes les 2 secondes.
- **Erreurs** :
  - Si Scribe échoue, on fait un nouvel essai, puis la séance passe en `failed` ; l'audio est gardé pour pouvoir relancer.
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
- **Variables d'environnement** sur la plateforme ; aucune clé dans le dépôt (Q26 : dépôt GitHub privé).
