---
type: study-note
title: "[08] Mueller et al. (2018) - MCI très précoce (cohorte WRAP)"
description: Sur 264 participants suivis 2 ans, le contenu sémantique, la fluence (maze index) et le débit de contenu par minute déclinent plus vite dès le MCI très précoce.
status: draft
tags: [study, longitudinal, early-mci, semantic, fluency, wrap-cohort]
resource: https://doi.org/10.3389/fnagi.2017.00437
sources:
  - id: "PMID:29375365"
    type: PubMed abstract
  - id: "PMC5767238"
    type: Europe PMC fulltext
verified:
  by: PubMed E-utilities API & Europe PMC
  at: "2026-11-11"
---

# [08] Mueller et al. : le langage décline dès le MCI très précoce (cohorte WRAP)

> Statut : ⏳ pas commencée · Lue le : —
> Fiche d'identité remplie d'après le texte intégral (Europe PMC). « À confirmer » = à vérifier pendant la lecture.

## Fiche d'identité

| Champ | Valeur |
|-------|--------|
| Référence complète | Mueller KD, Koscik RL, Hermann BP, Johnson SC, Turkstra LS (2018). Declines in Connected Language Are Associated with Very Early Mild Cognitive Impairment: Results from the Wisconsin Registry for Alzheimer's Prevention. *Frontiers in Aging Neuroscience*, 9, 437. |
| DOI / PMID / PMCID | [10.3389/fnagi.2017.00437](https://doi.org/10.3389/fnagi.2017.00437) · PMID [29375365](https://pubmed.ncbi.nlm.nih.gov/29375365/) · [PMC5767238](https://pmc.ncbi.nlm.nih.gov/articles/PMC5767238/) |
| Accès | open access |
| Type d'étude | cohorte longitudinale (2 temps de mesure), modèles linéaires mixtes avec intercept aléatoire par personne |
| Population | 264 participants de la cohorte WRAP (80 % ont un parent atteint d'Alzheimer) : 200 cognitivement sains, 64 MCI très précoce (« eMCI ») au suivi. 61,8 ans au premier échantillon, 16,4 années d'études, 96 % blancs. **Plus jeunes que notre cible (78 ans).** |
| Langue(s) | anglais |
| Tâche de parole | description orale de l'image Cookie Theft, environ 100 à 120 mots par description |
| Durée de suivi | 2 temps, 2,0 ans d'écart en moyenne (écart-type 1,5) |
| Mesures | transcription manuelle (format CHAT), extraction automatique (CLAN). 4 facteurs : **sémantique** (% noms, % verbes, indice pronominal = pronoms / (noms + pronoms)) ; **syntaxe** (verbes par énoncé, densité propositionnelle CPIDR, complexité grammaticale) ; **lexique** (type-token ratio brut, mots uniques, densité d'unités sémantiques) ; **fluence** (« maze index » = pauses remplies + faux départs + révisions + répétitions, par énoncé). |
| Niveau de preuve | cohorte prospective, échantillon important, mais 2 temps seulement et tâche sur image |

## En une phrase

Chez des personnes d'une soixantaine d'années, celles qui glissent vers un MCI très précoce voient leurs scores de **contenu sémantique** et de **fluence** baisser plus vite que celles qui restent stables. Elles transmettent aussi moins de contenu par minute. Le lexique et la syntaxe ne font pas la différence.

## À guetter pendant la lecture

- **H2 : à nuancer.** Le facteur « lexique » utilise le **type-token ratio brut** sur des textes d'environ 100 mots. Les auteurs écrivent eux-mêmes que ce ratio dépend de la longueur du texte, et qu'une version corrigée serait plus révélatrice. L'étude ne réfute donc pas MATTR ; elle montre que le TTR brut sur des échantillons courts ne marche pas. Ils citent aussi un minimum de 150 mots (300 à 400 recommandés en aphasie).
- **H6 : une définition prête à l'emploi.** Indice pronominal = pronoms / (noms + pronoms). Note le sens et la taille de l'effet.
- **H4 : le facteur « fluence » est exactement ce que Whisper efface** (pauses remplies, faux départs, révisions, répétitions). Si ce facteur compte dès le MCI précoce, il faut une transcription verbatim, pas une transcription nettoyée.
- **Efficacité.** Mots par minute et unités sémantiques par minute plus bas chez les eMCI au deuxième temps (p = 0,02 et 0,03). Une métrique simple à ajouter.
- **H8 : le modèle statistique de la baseline personnelle.** Modèle mixte avec intercept aléatoire par personne et « temps » mesuré par l'âge à chaque visite. Voir si c'est transposable à 6 sessions sur 6 mois.

## Passages notés

_Aucun pour l'instant._

## Biomarqueurs mesurés

| Biomarqueur | Définition opérationnelle | Sens de l'effet avec le déclin | Taille d'effet / perf. | Utilisable chez nous ? |
|-------------|---------------------------|--------------------------------|------------------------|------------------------|
| Facteur sémantique | % noms, % verbes, pronoms / (noms + pronoms) | déclin plus rapide chez les eMCI (âge × diagnostic : β = −0,04) | à relever | |
| Facteur fluence (maze index) | (pauses remplies + faux départs + révisions + répétitions) / énoncés | déclin plus rapide chez les eMCI (β = −0,03) | à relever | |
| Facteur lexique | TTR brut, mots uniques, unités sémantiques | non associé | — | |
| Facteur syntaxe | verbes / énoncé, densité propositionnelle, complexité grammaticale | non associé | — | |
| Mots par minute | — | ↓ au 2e temps | 143,3 contre 132,8 ; p = 0,02 | |
| Unités sémantiques par minute | — | ↓ au 2e temps | 20,6 contre 18,3 ; p = 0,03 | |

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
