---
type: log
title: ChronoVoice Brain — Knowledge Log
description: Journal chronologique des mises à jour, vérifications de sources et décisions d'architecture dans le bundle OKF docs/.
status: stable
tags: [okf, changelog, decisions]
---

# Knowledge Log

Historique chronologique du bundle `docs/` (entrées les plus récentes en premier).

## 2026-11-14

- **Interface soignant codée** (`frontend/`, précisions dans [`specs/clinician-ui.md`](specs/clinician-ui.md), section 5) :
  - les 5 écrans de la spec ;
  - types générés depuis l'OpenAPI du backend ;
  - couleurs sauge et terracotta contrôlées pour les daltoniens ;
  - interface servie par FastAPI une fois construite.
  - **Essai dans le navigateur** : chaque écran affiché sur les personas ; une séance envoyée par fichier importé (dialogue de synthèse vocale) est transcrite, analysée et résumée, puis l'écran passe tout seul au détail de la séance. L'enregistrement au micro reste à essayer.
  - **Backend** : chaque point de la trajectoire porte maintenant les valeurs des marqueurs, aussi pour les séances de constitution de la référence ; nouveau script `scripts/export_openapi.py`.
  - Composants ajoutés à [`tech/third-party-components.md`](tech/third-party-components.md).
- **API codée** ([`specs/api.md`](specs/api.md) précisée avant le code, section 7) :
  - routes FastAPI : personnes, séances, statut, relance, validation de la synthèse, questions d'amorce, intégration ;
  - stockage SQLite exclu de git, traitement des séances en tâche de fond ;
  - client Scribe en HTTP direct (`backend/app/agents/transcription.py`) ;
  - transcription annotée pour l'écran de détail ;
  - personas chargées au démarrage, avec les textes des étapes 2 et 4 générés une fois par Mistral Medium 3.5 (`backend/data/synthetic/llm_snapshot/`).
  - **Essai de bout en bout** avec Scribe et Mistral, sur un dialogue lu par deux voix de synthèse : 71 s d'audio traitées en 7 s (13 s avec une synthèse écrite par le modèle) ; voix séparées, hésitations et pauses repérées, audio supprimé chez nous puis chez ElevenLabs. Premiers constats sur Scribe notés dans [`tech/elevenlabs-scribe.md`](tech/elevenlabs-scribe.md), section 9.
  - **Correctif de l'étape 4** trouvé pendant cet essai : le sens d'un écart n'est plus donné au modèle pour un marqueur resté dans sa zone habituelle ; il écrivait « higher than usual » pour un marqueur sans écart ([`specs/pipeline.md`](specs/pipeline.md)).
  - Nouveaux composants : FastAPI, Pydantic, Uvicorn, python-multipart, HTTPX ([`tech/third-party-components.md`](tech/third-party-components.md)).
  - **L'analyse du récit n'est plus envoyée à l'étape 4** ([`specs/pipeline.md`](specs/pipeline.md)). En relisant les textes des personas, on a vu le modèle écrire à Margaret « You also repeated a story you had told before » ; quand on le lui a interdit, il en a fait des constats sans marqueur, rejetés. L'analyse reste affichée à part, comme expérimentale.
  - **Textes figés des personas** régénérés après ces deux correctifs : 7 synthèses sur 7 écrites par le modèle pour chaque persona. Analyse du récit : les 3 reprises de Margaret et la reprise signalée de Rajesh sont retrouvées, mais 5 autres reprises gardées chez Rajesh sont des souvenirs voisins. Elles seront visibles dans la section expérimentale : à relire par Thibaut.
- **Modèle retenu par Thibaut : Mistral Medium 3.5, par réglage** (`MISTRAL_MODEL=mistral-medium-latest`), pour les essais et la démo. Le défaut du code reste Mistral Small 4, au cas où Mistral retirerait ce modèle déprécié. [`specs/pipeline.md`](specs/pipeline.md), [`specs/questions.md`](specs/questions.md) et [`tech/third-party-components.md`](tech/third-party-components.md) mis à jour.
- **Premier essai réel des étapes 2 et 4**, avec Mistral Small puis Mistral Medium, sur Margaret et Rajesh (séances fictives). Constats :
  - **Étape 4 :**
    - les garde-fous rejettent bien les brouillons fautifs, et le texte fixe prend le relais ;
    - avec Mistral Small, des erreurs passent quand même :
      - un nombre de séances faux dans l'incertitude (3 brouillons sur 6) ;
      - un titre qui contredit le niveau ;
      - une explication rassurante pour un niveau `review_recommended` ;
      - un marqueur hors zone non mentionné ;
    - Mistral Medium ne fait aucune de ces erreurs sur Margaret.
  - **Étape 2 :**
    - Mistral Small retrouve l'anecdote répétée, mais se trompe souvent de type de reprise, ce qui la fait écarter ;
    - Mistral Medium la retrouve mieux, mais garde beaucoup de simples ressemblances de thème ;
    - les citations longues sont souvent recopiées sans les « um », puis écartées ;
    - les réponses varient d'un essai à l'autre, même à température 0.
  - **Mistral Large** raisonne avant de répondre et dépasse le délai de 90 s.
  - Les corrections des garde-fous attendent la validation de Thibaut.
- **Garde-fous des étapes 2 et 4 renforcés**, après validation de Thibaut ([`specs/pipeline.md`](specs/pipeline.md) mise à jour avant le code). Trois tours d'essais réels ont guidé les corrections.
  - **Étape 4 :**
    - le code écrit le titre, la phrase sur l'incertitude et la suite proposée à la personne ; le modèle n'écrit plus que les constats et ce qui a été remarqué ;
    - un marqueur de l'indice sorti de la zone habituelle doit figurer dans un constat ;
    - le modèle désigne un passage par son numéro, et le code place le texte exact ;
    - les phrases pour la personne s'adressent à elle, sans mot qui rassure ou inquiète ;
    - le sens de chaque écart est donné au modèle.
  - **Étape 2 :**
    - une seule référence à l'épisode d'origine, dont le code déduit le type de reprise ;
    - le modèle distingue le même événement d'un thème voisin, et seul le premier est gardé ;
    - une reprise n'est notée comme signalée par la personne qu'avec les mots du signalement, retrouvés dans la transcription (nouveau champ `acknowledgement_quote` dans `schemas.py`) ;
    - les passages sont retrouvés même sans leurs hésitations, et affichés tels que la personne les a dits ;
    - le code attribue les identifiants d'épisode, et garde une seule reprise par épisode.
  - **Résultat** avec Mistral Medium 3.5 sur les 3 personas : 4 reprises attendues sur 4, 3 reprises gardées alors qu'aucune n'était prévue, 8 synthèses sur 8 acceptées au premier essai. Les réponses varient d'un essai à l'autre : c'est un ordre de grandeur.
- **Modèles Mistral** : Mistral Medium 3.5 est déprécié depuis le 2026-10-31 et Mistral Large 4 met plus d'une minute par appel. Le défaut du code reste Mistral Small 4 ; `MISTRAL_MODEL` et la nouvelle variable `MISTRAL_REASONING_EFFORT` règlent le reste. [`tech/third-party-components.md`](tech/third-party-components.md) mis à jour.
- **Correctif du client Mistral** : `top_p` à 1 envoyé avec la température à 0, sinon Mistral Large refuse la requête ([`specs/pipeline.md`](specs/pipeline.md), « Appel au modèle »).

## 2026-11-13

- **Second fournisseur de modèle : Mistral**, sur proposition de Thibaut, qui a des crédits. `backend/app/llm/` devient un paquet : `base.py` (contrat commun), `claude.py`, `mistral.py` (`mistral-small-latest` par défaut), et le choix du fournisseur par `LLM_PROVIDER` ou par la clé présente. Script d'essai réel `backend/scripts/try_llm_steps.py` et fichier `backend/.env.example`. [`specs/pipeline.md`](specs/pipeline.md) et [`specs/questions.md`](specs/questions.md) mis à jour.
- **Nouveau garde-fou de l'étape 4** : chaque constat déclare s'il parle de marqueurs sortis de la zone habituelle, et le code vérifie cette déclaration contre les tests de l'étape 3. Un texte ne peut plus annoncer un écart que les mesures ne montrent pas.
- **Étapes 2 et 4 codées (LLM)** : `backend/app/llm.py` (client Claude Opus 5.5, sortie structurée), `backend/app/agents/narrative.py` (analyste du récit), `backend/app/agents/summary.py` (synthèse clinique, validateur, texte fixe de repli) et `backend/app/agents/passages.py` (vérification des citations). [`specs/pipeline.md`](specs/pipeline.md) précisée : la liste du vocabulaire interdit s'étend à tout nom d'affection ; le profil de risque n'est pas envoyé au modèle ; `prevention_notes` reste vide tant que la liste du rapport Lancet 2024 n'a pas été relue. Aucun appel réel au modèle n'a encore été fait, faute de clé.
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
