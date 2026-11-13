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
  at: "2026-11-13"
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
| [NumPy](https://numpy.org) | 2.x | Outil de développement seulement : simulation des règles d'orientation | BSD 3-Clause, avec des composants sous 0BSD, MIT, Zlib et CC0 | 2026-11-13 |

## Contenus générés

- **Récits des personas** (`backend/data/synthetic/stories/`) : écrits le 2026-11-13 par Claude Sonnet 5.5, à partir de biographies fictives. Ce sont des données synthétiques créées pour le projet, sans contenu tiers.

## Transcription (étape 0)

| Composant | Rôle | Conditions | Vérifié le |
|---|---|---|---|
| ElevenLabs Scribe v3 | Transcription mot pour mot, horodatée, avec séparation des voix | Service commercial par API. Détails dans [elevenlabs-scribe.md](elevenlabs-scribe.md) | 2026-11-12 |

## À compléter

- Le LLM des étapes 2 et 4 (Claude Opus 5.5, par l'API Anthropic), quand ces étapes seront codées.
- Les bibliothèques du backend (FastAPI, Pydantic) et du frontend (React, Tailwind, Recharts, Lucide).
