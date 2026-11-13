---
type: study-note
title: "[04] Agbavor & Liang (2022) - Embeddings LLM vs features acoustiques"
description: Des embeddings GPT-3 sur transcription automatique classent Alzheimer vs témoins à 80,3 % sur ADReSSo 2021 et prédisent le MMSE mieux que les features acoustiques eGeMAPS.
status: draft
tags: [study, cross-sectional, llm-embeddings, black-box, adresso]
resource: https://doi.org/10.1371/journal.pdig.0000168
sources:
  - id: "PMID:36812634"
    type: PubMed abstract
  - id: "PMC9931366"
    type: PLOS fulltext
verified:
  by: PubMed E-utilities API (identifiants)
  at: "2026-11-11"
---

# [04] Agbavor & Liang : prédire la démence avec des LLM

> Statut : ⏳ pas commencée · Lue le : —
> Fiche d'identité remplie d'après le texte intégral (PLOS). Les valeurs des tableaux (images) n'ont pas pu être lues : « à confirmer ».

## Fiche d'identité

| Champ | Valeur |
|-------|--------|
| Référence complète | Agbavor F, Liang H (2022). Predicting dementia from spontaneous speech using large language models. *PLOS Digital Health*, 1(12), e0000168. |
| DOI / PMID / PMCID | [10.1371/journal.pdig.0000168](https://doi.org/10.1371/journal.pdig.0000168) · PMID [36812634](https://pubmed.ncbi.nlm.nih.gov/36812634/) · [PMC9931366](https://pmc.ncbi.nlm.nih.gov/articles/PMC9931366/) |
| ⚠️ Corrections | Le PMCID fourni (PMC9937397) renvoie à un autre document. Le DOI fourni était bon. |
| Accès | open access |
| Type d'étude | transversale, apprentissage automatique |
| Population | données du challenge ADReSSo 2021 (issues de DementiaBank) : 237 enregistrements, 166 en entraînement (87 Alzheimer, 79 non-Alzheimer), 71 en test. Âge et sexe appariés. |
| Langue(s) | non précisée dans l'article (anglais, à confirmer) |
| Tâche de parole | description de l'image Cookie Theft (Boston Diagnostic Aphasia Examination) |
| Durée de suivi | aucune |
| Pipeline | transcription par wav2vec 2.0 (`wav2vec2-base-960h`) → embeddings GPT-3 (Ada, 1024 dimensions ; Babbage, 2048) → classifieurs SVC, régression logistique, forêt aléatoire. Comparaison avec 88 features acoustiques eGeMAPS (OpenSMILE) et avec un GPT-3 Babbage fine-tuné. |
| Niveau de preuve | validation interne sur un seul jeu de données, pas de validation externe |

## En une phrase

Des embeddings GPT-3 calculés sur la simple transcription automatique classent Alzheimer contre témoins avec 80,3 % de précision sur le jeu de test (contre 64,8 % pour la baseline officielle du challenge), et prédisent le score MMSE mieux que les features acoustiques.

## À guetter pendant la lecture

- **H1 : le cœur du débat.** Ici, aucune feature construite à la main : un LLM transforme le texte en vecteur, un classifieur décide. Si cette approche fait mieux que MATTR + pauses, l'Agent 1 tel que prévu est-il utile ? Contre-argument : un clinicien doit pouvoir **expliquer** une alerte, et les auteurs reconnaissent eux-mêmes le problème de « boîte noire ». Note tout ce qu'ils disent sur l'explicabilité.
- **H5 : embeddings.** Les mêmes embeddings peuvent servir à détecter la répétition d'anecdotes. Quelle dimension, quel modèle ?
- **H4 : la transcription.** wav2vec 2.0 transcrit-il les hésitations ? Quel taux d'erreur ? Effet des erreurs de transcription sur le résultat ?
- **Acoustique et texte combinés** : gain marginal selon les auteurs. Argument pour ou contre un agent acoustique séparé ?
- **#éthique : envoi de la parole à une API externe.** Les transcriptions partent chez OpenAI. Pour des données de santé en France (RGPD, hébergement HDS), ce n'est pas transposable tel quel : il faudrait un modèle local ou un hébergeur certifié.
- **Point méthodologique** : la validation croisée en 10 plis est décrite comme un découpage « 80/10/10 », ce qui est incohérent. Voir si ça change l'interprétation.

## Passages notés

_Aucun pour l'instant._

## Biomarqueurs mesurés

| Biomarqueur | Définition opérationnelle | Sens de l'effet avec le déclin | Taille d'effet / perf. | Utilisable chez nous ? |
|-------------|---------------------------|--------------------------------|------------------------|------------------------|
| Embeddings GPT-3 (Babbage) + SVC | vecteur de 2048 dimensions par transcription | — | précision 0,8028 en test | |
| Features acoustiques eGeMAPS | 88 features OpenSMILE | — | régression MMSE : RMSE 6,25 en test (Ridge) | |

## Limites et biais

- Validation sur ADReSSo seulement, validation externe nécessaire (dit par les auteurs).
- Petit échantillon : les plus gros modèles (Curie, Davinci) ont surappris et n'ont pas été retenus.
- Biais possibles d'âge, de sexe, d'origine et de langue ; confidentialité des données vocales ; boîte noire (dit par les auteurs).

## Implications pour ChronoVoice

- **Métriques :**
- **Seuils :**
- **Architecture des agents :**
- **Données mock :**
- **Dashboard / synthèse clinique :**

## Questions ouvertes

-
