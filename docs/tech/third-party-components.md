---
type: tech-reference
title: Composants tiers et licences
description: Liste des composants tiers du prototype (services, bibliothèques, modèles, données), avec leur rôle, leur licence et la date de vérification. Sert à la slide 13 du deck de soumission.
status: draft
tags: [tech, licenses, dependencies, third-party, slide-13]
sources:
  - name: PyPI, fiche du paquet spaCy
    url: https://pypi.org/project/spacy/
  - name: Métadonnées du modèle en_core_web_sm 3.8.0 (dépôt explosion/spacy-models)
    url: https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0
  - name: README du paquet wordfreq (section License)
    url: https://github.com/rspeer/wordfreq
verified:
  by: PyPI et dépôts GitHub officiels des projets
  at: "2026-11-14"
---

# Composants tiers et licences

Le règlement du challenge peut exclure des prix une solution qui dépend de droits tiers non disponibles commercialement ([challenge.md](../challenge.md), section 5). La slide 13 du template demande aussi la liste des composants tiers et de leurs licences. Ce fichier tient cette liste à jour, au fil des dépendances.

## Analyse du langage (étape 1)

| Composant | Version | Rôle | Licence | Vérifié le |
|---|---|---|---|---|
| [spaCy](https://spacy.io) | 3.8.x | Découpage en mots et étiquetage grammatical | MIT | 2026-11-13 |
| Modèle spaCy `en_core_web_sm` | 3.8.0 | Modèle anglais de spaCy (12 Mo) | MIT | 2026-11-13 |
| [wordfreq](https://github.com/rspeer/wordfreq) | 3.1.1 | Fréquence des mots sur l'échelle de Zipf | Code : Apache 2.0. Données : CC BY-SA 4.0 | 2026-11-13 |

**À savoir**

- **wordfreq n'est plus mis à jour** depuis 2024 : son auteur a figé les listes. Pour nous, c'est plutôt un avantage : la référence de fréquence ne bouge pas d'une séance à l'autre.
- **La licence CC BY-SA 4.0 des données de wordfreq** autorise l'usage commercial. Elle demande de citer la source et de partager sous la même licence toute version modifiée des données. On utilise les données telles quelles, sans les modifier.
- **Le modèle `en_core_web_sm`** a été entraîné sur OntoNotes 5 et WordNet 3.0, d'après ses métadonnées. Le modèle lui-même est distribué sous licence MIT.

## Autres bibliothèques

| Composant | Version | Rôle | Licence | Vérifié le |
|---|---|---|---|---|
| [langcodes](https://pypi.org/project/langcodes/) | 3.5.x | Conversion des codes de langue de Scribe (« en ») en codes à 3 lettres (« eng ») | MIT | 2026-11-13 |
| [FastAPI](https://pypi.org/project/fastapi/) | 0.162.x | Serveur de l'API | MIT | 2026-11-14 |
| [Pydantic](https://pypi.org/project/pydantic/) | 2.14.x | Contrats entre étapes, validation à toutes les frontières | MIT | 2026-11-14 |
| [Uvicorn](https://pypi.org/project/uvicorn/) | 0.54.x | Serveur HTTP qui fait tourner FastAPI | BSD 3-Clause | 2026-11-14 |
| [python-multipart](https://pypi.org/project/python-multipart/) | 0.0.x | Lecture des envois multipart (audio et métadonnées) | Apache 2.0 | 2026-11-14 |
| [HTTPX](https://pypi.org/project/httpx/) | 0.28.x | Appels à l'API de Scribe | BSD 3-Clause | 2026-11-14 |
| [httpx2](https://pypi.org/project/httpx2/) | 2.16.x | Client HTTP du SDK de Mistral ; `app/llm/mistral.py` l'importe pour reconnaître ses erreurs de réseau. Dépendance indirecte (via `mistralai`), pas déclarée dans `pyproject.toml` | BSD 3-Clause (métadonnées du paquet) | 2026-11-15 |
| [NumPy](https://numpy.org) | 2.x | Outil de développement seulement : simulation des règles d'orientation | BSD 3-Clause, avec des composants sous 0BSD, MIT, Zlib et CC0 | 2026-11-13 |

## Modèle de langage (étapes 2 et 4)

| Composant | Version | Rôle | Conditions | Vérifié le |
|---|---|---|---|---|
| Claude Opus 5.5, par l'API d'Anthropic | `claude-opus-5-5` | Fournisseur alternatif (`LLM_PROVIDER=anthropic`). Choisi le 2026-11-12, pas encore essayé faute de clé | Service commercial par API | 2026-11-13 |
| [SDK Python d'Anthropic](https://pypi.org/project/anthropic/) | 2.8.x | Appels à l'API, sorties structurées | Apache 2.0 | 2026-11-13 |
| Mistral Small 4, par l'API de Mistral | `mistral-small-latest` | Défaut du code quand `MISTRAL_MODEL` n'est pas réglé | Service commercial par API ; poids publiés sous Apache 2.0 ([fiche du modèle](https://docs.mistral.ai/models/mistral-small-4-0-26-03)) | 2026-11-14 |
| Mistral Medium 3.5, par l'API de Mistral | `mistral-medium-latest` | **Modèle de la démo**, en local et sur Render (réglage `MISTRAL_MODEL`, choix du 2026-11-14) ; il a produit les textes figés des personas | Service commercial par API ; poids publiés sous licence MIT modifiée. **Déprécié par Mistral depuis le 2026-10-31**, remplaçant annoncé : Mistral Large 4 ([fiche du modèle](https://docs.mistral.ai/models/mistral-medium-3-5-26-04)) | 2026-11-14 |
| [SDK Python de Mistral](https://pypi.org/project/mistralai/) | 3.7.x | Appels à l'API, sorties structurées | Apache 2.0 (fichier LICENSE du paquet) | 2026-11-13 |

## Interface (frontend)

| Composant | Version | Rôle | Licence | Vérifié le |
|---|---|---|---|---|
| [React](https://react.dev) et React DOM | 19.3.x | Interface | MIT | 2026-11-14 |
| [React Router](https://reactrouter.com) | 7.18.x | Navigation entre les écrans | MIT | 2026-11-14 |
| [Recharts](https://recharts.org) | 3.10.x | Graphiques | MIT | 2026-11-14 |
| [Lucide](https://lucide.dev) (`lucide-react`) | 1.73.x | Icônes | ISC | 2026-11-14 |
| [Tailwind CSS](https://tailwindcss.com) | 4.3.x | Styles | MIT | 2026-11-14 |
| [Vite](https://vite.dev) | 8.3.x | Outil de développement et de construction | MIT | 2026-11-14 |
| `@vitejs/plugin-react`, `@tailwindcss/vite` | 6.3.x, 4.3.x | Extensions de Vite pour React et Tailwind, à la construction seulement | MIT | 2026-11-15 |
| TypeScript, ESLint, typescript-eslint, openapi-typescript | 5.9.x, 10.x, 8.x, 7.x | Outils de développement seulement | Apache 2.0 (TypeScript) ; MIT (les autres) | 2026-11-14 |

**À savoir** : `npm audit` signale 7 failles de gravité moyenne, toutes dans la chaîne de typescript-eslint, un outil de développement qui n'est pas livré avec l'application. TypeScript reste en 5.9 : la version 7 n'est pas encore prise en charge par typescript-eslint ni par openapi-typescript.

## Contenus générés

- **Récits des personas** (`backend/data/synthetic/stories/`) : écrits le 2026-11-13 par Claude Sonnet 5.5, à partir de biographies fictives. Ce sont des données synthétiques créées pour le projet, sans contenu tiers.
- **Textes figés des personas** (`backend/data/synthetic/llm_snapshot/`) : analyses du récit et synthèses produites le 2026-11-14 par Mistral Medium 3.5, à partir de ces récits synthétiques, puis vérifiées par les garde-fous du pipeline.

## Construction et hébergement

| Composant | Version | Rôle | Licence ou conditions | Vérifié le |
|---|---|---|---|---|
| Image Docker `node` | `22.16-slim` | Construit l'interface ; n'est pas dans l'image livrée | Node.js : MIT | 2026-11-15 |
| Image Docker `python` | `3.12-slim` (Python 3.12.16) | Base de l'image livrée | Python : PSF License (fichier `LICENSE.txt` de l'image) ; paquets Debian sous leurs propres licences libres | 2026-11-15 |
| [uv](https://github.com/astral-sh/uv) (`ghcr.io/astral-sh/uv`) | 0.10.2 | Installe les dépendances Python, dans l'image comme en développement | MIT ou Apache 2.0, au choix (PyPI) | 2026-11-15 |
| [Render](https://render.com) | — | Hébergement du service, région Frankfurt ([deploy-render.md](deploy-render.md)) | Service commercial | 2026-11-14 |

## Transcription (étape 0)

| Composant | Rôle | Conditions | Vérifié le |
|---|---|---|---|
| ElevenLabs Scribe v3 | Transcription mot pour mot, horodatée, avec séparation des voix | Service commercial par API, appelé directement en HTTP (sans le SDK). Détails dans [elevenlabs-scribe.md](elevenlabs-scribe.md) | 2026-11-14 |

## À compléter

- Rien pour l'instant : la liste suit les dépendances au fil de l'eau (dernière revue complète le 2026-11-15, contre `pyproject.toml`, `package.json` et le `Dockerfile`).
