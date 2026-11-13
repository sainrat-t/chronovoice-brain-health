---
okf_version: "0.2"
type: index
title: ChronoVoice Brain — Knowledge Bundle
description: Base de connaissances OKF v0.2 du projet ChronoVoice Brain (Future Health Digital Innovation Challenge — Challenge 08).
status: draft
tags: [chronovoice, okf, brain-health, hackathon, discovery]
---

# ChronoVoice Brain — Knowledge Bundle

Ce dossier est structuré selon l'**Open Knowledge Format (OKF v0.2)**.
Les agents doivent le parcourir en *progressive disclosure* (d'abord cet index, puis l'`index.md` du sous-dossier ciblé, puis les fiches utiles) et journaliser toute évolution structurante dans [`log.md`](log.md).

## Carte du bundle

| Ressource | Rôle | Statut |
|---|---|---|
| [`challenge.md`](challenge.md) | Énoncé officiel du Challenge 08, règles, critères du jury, template de soumission et analyse des écarts | `stable` |
| [`discovery/index.md`](discovery/index.md) | Phase de discovery scientifique : protocole, synthèse des preuves, hypothèses H1–H10, architecture v0.3 et corpus d'études | `draft` |
| [`specs/index.md`](specs/index.md) | Spécifications du prototype : questionnaire, puis specs de la pipeline, de l'interface soignant et de l'enregistrement au micro | `draft` |
| [`tech/index.md`](tech/index.md) | Références techniques d'intégration (STT ElevenLabs Scribe v3, réglages étape 0, conformité) | `stable` |
| [`log.md`](log.md) | Historique chronologique des modifications et décisions de la base de connaissances | `stable` |

## Conventions OKF du projet

- Les métadonnées de chaque document utilisent le frontmatter YAML (`type`, `title`, `description`, `status`, `tags`, `sources`, `verified`).
- Les règles d'ingénierie, de sécurité clinique et de maintenance OKF sont définies dans [`../CLAUDE.md`](../CLAUDE.md) (et résumées dans [`../AGENTS.md`](../AGENTS.md)).
