---
type: study-note
title: "[06] Pistono et al. (2016) - Pauses en discours autobiographique"
description: En rappel d'épisode récent, les patients MCI font plus de pauses >= 250 ms entre énoncés, corrélées positivement à la mémoire épisodique (mécanisme compensatoire).
status: draft
tags: [study, cross-sectional, mci, french, pauses, episodic-memory]
resource: https://doi.org/10.3233/JAD-150408
sources:
  - id: "PMID:26757034"
    type: PubMed abstract
  - id: "PMC4927846"
    type: Europe PMC fulltext
verified:
  by: PubMed E-utilities API & Europe PMC
  at: "2026-11-11"
---

# [06] Pistono et al. : les pauses dans le discours autobiographique

> Statut : ⏳ pas commencée · Lue le : —
> Fiche d'identité remplie d'après le texte intégral (Europe PMC). « À confirmer » = à vérifier pendant la lecture.

## Fiche d'identité

| Champ | Valeur |
|-------|--------|
| Référence complète | Pistono A, Jucla M, Barbeau EJ, Saint-Aubert L, Lemesle B, Calvet B, Köpke B, Puel M, Pariente J (2016). Pauses During Autobiographical Discourse Reflect Episodic Memory Processes in Early Alzheimer's Disease. *Journal of Alzheimer's Disease*, 50(3), 687–698. |
| DOI / PMID / PMCID | [10.3233/JAD-150408](https://doi.org/10.3233/JAD-150408) · PMID [26757034](https://pubmed.ncbi.nlm.nih.gov/26757034/) · [PMC4927846](https://pmc.ncbi.nlm.nih.gov/articles/PMC4927846/) |
| Accès | open access |
| Type d'étude | transversale cas-témoins, avec IRM |
| Population | 15 patients de plus de 65 ans avec un MCI dû à Alzheimer, 15 témoins appariés. CHU de Toulouse, comité d'éthique français. |
| Langue(s) | français (participants recrutés en France ; les exemples sont traduits dans l'article — à confirmer) |
| Tâche de parole | ⚠️ **Pas un récit de vie.** Tâche de mémoire épisodique « écologique » : environ 25 minutes de petits événements vécus avec l'examinateur (une promenade), puis, 20 minutes plus tard, rappel libre et chronologique de tout ce qui s'est passé. C'est du discours autobiographique sur un épisode **récent**. |
| Durée de suivi | aucune |
| Mesures | pauses annotées **à la main** dans Audacity, **seuil de 250 ms** (typologie de Goldman-Eisler). Classées par emplacement : entre deux énoncés, ou à l'intérieur d'un énoncé (grammaticales / non grammaticales). Fréquence pour 100 mots, durée moyenne, débit. IRM : densité de matière grise. |
| Niveau de preuve | petit échantillon (2 × 15), annotation manuelle, pas de validation externe |

## En une phrase

Les patients MCI ne font **pas plus de pauses au total** que les témoins, mais plus de pauses **entre deux énoncés** (7,49 contre 5,04 pour 100 mots, p = 0,04, d = 1,06). Ces pauses sont plus nombreuses chez les patients qui ont la **meilleure** mémoire épisodique : les auteurs y voient un mécanisme de compensation (le temps de « voyager » dans le souvenir), pas un symptôme.

## À guetter pendant la lecture

- **H4 : le seuil de 250 ms est bien celui de cette littérature** (repris de Goldman-Eisler pour séparer les pauses articulatoires des pauses d'hésitation). Note la justification exacte.
- **H4 : l'emplacement compte plus que le nombre.** Notre cahier des charges vise les pauses *intra-phrases* ; ici, c'est *entre* les énoncés que l'effet apparaît. Comment les énoncés sont-ils découpés ? (ici à l'oreille, par l'intonation). Peut-on le faire automatiquement à partir d'une transcription Whisper, dont la ponctuation ne correspond pas forcément aux énoncés ?
- **Le sens de l'alerte.** Si plus de pauses = compensation, une alerte « trop de pauses » serait fausse. Comment les auteurs recommandent-ils de les interpréter ?
- **Transposition à notre tâche.** Ici on rappelle un épisode vécu 20 minutes plus tôt (mémoire récente) ; un récit de vie mobilise des souvenirs anciens. L'effet tiendrait-il ? Voir aussi Pistono 2019 dans [`candidates.md`](../candidates.md) : chez des patients Alzheimer, plus de pauses dans le récit sur image, pas dans le récit de souvenir.
- **Moins de mots, même durée de parole** chez les patients : un indice d'« efficacité » (contenu par minute) à rapprocher de Mueller (fiche 08).

## Passages notés

_Aucun pour l'instant._

## Biomarqueurs mesurés

| Biomarqueur | Définition opérationnelle | Sens de l'effet avec le déclin | Taille d'effet / perf. | Utilisable chez nous ? |
|-------------|---------------------------|--------------------------------|------------------------|------------------------|
| Pauses entre énoncés | silence ≥ 250 ms entre deux énoncés, pour 100 mots | ↑ (compensation) | 7,49 ± 2,5 contre 5,04 ± 2,17 ; p = 0,04 corrigé ; d = 1,06 | |
| Pauses intra-énoncé grammaticales | silence ≥ 250 ms à une frontière syntaxique, pour 100 mots | pas de différence | 16,36 contre 14,63 ; p = 0,51 | |
| Pauses intra-énoncé non grammaticales | silence ≥ 250 ms hors frontière syntaxique, pour 100 mots | pas de différence | 4,05 contre 8,45 ; p = 0,54 | |
| Nombre de mots / durée de parole | — | moins de mots, durée identique | à relever | |

## Limites et biais

-

## Implications pour ChronoVoice

- **Métriques :**
- **Seuils :**
- **Architecture des agents :**
- **Données mock :**
- **Dashboard / synthèse clinique :**

## Questions ouvertes

-
