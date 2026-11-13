---
type: log
title: ChronoVoice Brain — Knowledge Log
description: Journal chronologique des mises à jour, vérifications de sources et décisions d'architecture dans le bundle OKF docs/.
status: stable
tags: [okf, changelog, decisions]
---

# Knowledge Log

Historique chronologique du bundle `docs/` (entrées les plus récentes en premier).

## 2026-11-13

- **Données de démonstration générées** ([`specs/synthetic-data.md`](specs/synthetic-data.md) mise à jour) : 3 personas, 30 séances au format Scribe sous `backend/data/synthetic/`, récits écrits par Claude Sonnet 5.5, banque de 12 questions `backend/data/prompts.json`. Les trajectoires sont verrouillées par `backend/tests/test_synthetic_data.py`. Constat noté dans [`specs/pipeline.md`](specs/pipeline.md) : le thème du récit pèse sur les marqueurs sémantiques.
- **Partie déterministe de l'étape 0 codée** : `backend/app/agents/capture.py` (réponse Scribe vers transcription, choix de la voix suivie, contrôle qualité) et `backend/app/agents/pipeline.py`. Le seuil de confiance de 50 % est provisoire. L'appel à Scribe reste à écrire.
- **Règle de décision de l'étape 3 validée par Thibaut** (au moins 2 marqueurs sur 6 ; chute rapide à partir de 4).
- **Étape 3 du pipeline codée (dérive)** : `backend/app/agents/drift.py` (référence personnelle de 3 à 5 séances, test par marqueur, niveaux d'orientation). Le contrat `backend/app/schemas.py` est adapté (`AnalysedSession`, `ChangeIndexScore`, `SignificanceTest`).
- **Règle de décision corrigée dans [`specs/pipeline.md`](specs/pipeline.md)** avant le code : une simulation a montré que le test prévu sur l'indice donnait 9 à 14 % de fausses alertes au lieu de 5 %. La décision se prend maintenant sur le nombre de marqueurs significatifs : au moins 2 sur 6 pour une séance en écart, au moins 4 pour une chute rapide. Simulation reproductible : `backend/scripts/simulate_orientation_rules.py`. Répercuté dans [`specs/overview.md`](specs/overview.md), [`specs/clinician-ui.md`](specs/clinician-ui.md), [`specs/questions.md`](specs/questions.md) et le journal de [`discovery/synthesis.md`](discovery/synthesis.md).
- **Étape 1 du pipeline codée (marqueurs)** : `backend/app/agents/segmentation.py`, `backend/app/agents/markers.py` et l'adaptateur de langue anglais `backend/app/language/`. La spec [`specs/pipeline.md`](specs/pipeline.md) a été précisée avant le code :
  - les marqueurs se calculent sur les mots lexicaux, hors hésitations et mots coupés ;
  - un mot peut porter plusieurs étiquettes grammaticales ;
  - la fréquence des mots vient de `wordfreq` (échelle de Zipf), sur les mots pleins hors noms propres ;
  - une répétition immédiate porte sur un mot ou un groupe de 2 ou 3 mots ;
  - un écart qui contient un rire ou une toux n'est pas une pause.
- **Référence MATTR vérifiée** : Covington & McFall 2010 (DOI 10.1080/09296171003643098), sur Crossref, car la revue n'est indexée ni par PubMed ni par Europe PMC.
- **Nouvelle fiche** [`tech/third-party-components.md`](tech/third-party-components.md) : composants tiers et licences (spaCy et son modèle anglais : MIT ; wordfreq : Apache 2.0 pour le code, CC BY-SA 4.0 pour les données), pour la slide 13 du deck.

## 2026-11-12

- **Clôture de la discovery et passage en phase prototype**, décidée par Thibaut faute de temps : remise le 2026-11-20. Les specs v1 de [`specs/`](specs/index.md) deviennent la référence du code. La lecture continue seulement sur les fiches 07 et 09. `../CLAUDE.md` et `../AGENTS.md` sont mis à jour, et le contrat d'interface `backend/app/schemas.py` est écrit.
- **Arbitrage des points incertains des specs** (questions Q29 à Q43 de [`specs/questions.md`](specs/questions.md)), reportés dans les specs :
  - revue recommandée après 2 séances significatives consécutives, ou une chute rapide (α = 0,01) ;
  - référence de 3 à 5 séances, puis figée ;
  - un contexte défavorable plafonne à « à surveiller » ;
  - séance partielle sous 150 mots ou 2 minutes ;
  - voix suivie choisie automatiquement ;
  - fréquence calculée sur les mots pleins ;
  - Claude Opus 5.5 ;
  - score renommé « Change from baseline » ;
  - des mots d'abord, les chiffres dans « Details » ;
  - une ligne génomique « not shared » ;
  - personas validées ;
  - hébergement sur Render (Vercel écarté) ;
  - Thibaut seul dans l'équipe.
- **Specs v1 du prototype** : réponses au questionnaire validées, puis rédaction de [`specs/overview.md`](specs/overview.md), [`specs/pipeline.md`](specs/pipeline.md), [`specs/clinician-ui.md`](specs/clinician-ui.md), [`specs/api.md`](specs/api.md) et [`specs/synthetic-data.md`](specs/synthetic-data.md). Elles précisent la v0.3 sur trois points : l'indice de changement fiable est remplacé par le test t modifié pour petits échantillons (Crawford & Garthwaite 2002, PMID 11931923) ; le Brain Health Index compte 6 marqueurs, sans les pauses ni le MATTR ; H7 sort de la v1. Références vérifiées sur PubMed : Crawford & Garthwaite 2002, Livingston et al. 2024 (PMID 39096926).
- **Lancement des specs du prototype** : ajout de [`specs/index.md`](specs/index.md) et du questionnaire [`specs/questions.md`](specs/questions.md) (28 questions avec proposition par défaut : démo, micro, pipeline, interface soignant, mise en ligne, équipe). Ajout de la todo de projet jusqu'au 2026-11-20 (`TODO.md` à la racine du dépôt).
- **Mise en place de l'Open Knowledge Format (OKF v0.2)** dans `docs/` : ajout de [`index.md`](index.md), [`log.md`](log.md), [`discovery/index.md`](discovery/index.md), [`discovery/studies/index.md`](discovery/studies/index.md), [`tech/index.md`](tech/index.md), enrichissement du frontmatter YAML sur l'ensemble des fiches, documentation des règles OKF dans [`../CLAUDE.md`](../CLAUDE.md) et [`../AGENTS.md`](../AGENTS.md), et ajout d'un test de conformité (`backend/tests/test_okf.py`).
- **Choix STT : ElevenLabs Scribe v3** ([`tech/elevenlabs-scribe.md`](tech/elevenlabs-scribe.md)) : remplace Mistral Voxtral pour obtenir en un appel la transcription verbatim (`no_verbatim=false`), l'horodatage par mot et la diarisation à l'étape 0.
- **Cadrage hackathon et écarts** ([`challenge.md`](challenge.md)) : intégration de l'énoncé Challenge 08, des 6 critères d'évaluation, du template de 16 slides et du calendrier (remise le 2026-11-20).
- **Décisions produit & architecture v0.3** ([`discovery/synthesis.md`](discovery/synthesis.md)) : prototype en anglais avec conception multilingue par adaptateurs de langue, module branchable (premier cas : MyMémoires), transcription par Mistral Voxtral Transcribe 3 (horodatage par segment + VAD pour les pauses), 5 étapes dont 2 LLM.
- **Élargissement du corpus** : ajout des fiches `06` à `10` dans [`discovery/studies/index.md`](discovery/studies/index.md) pour couvrir le récit autobiographique, le suivi longitudinal et le stade MCI.

## 2026-11-11

- **Création du corpus initial et vérification PubMed** : rédaction des fiches `01` à `05` et de [`discovery/candidates.md`](discovery/candidates.md) après vérification des identifiants (DOI, PMID, PMCID) via l'API PubMed E-utilities (correction d'identifiants erronés sur 4 des 5 études initiales).
