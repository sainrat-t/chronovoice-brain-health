---
type: protocol
title: Protocole de discovery scientifique
description: Tableau de suivi des 10 études du corpus, protocole de prise de notes et taxonomie de tags.
status: stable
tags: [discovery, protocol, pubmed, tags]
verified:
  by: PubMed E-utilities API (références)
  at: "2026-11-11"
---

# Discovery scientifique

**But :** valider (ou casser) les choix d'architecture de ChronoVoice Brain à partir de la littérature, **avant** d'écrire les agents. On sort de cette phase avec une liste figée de métriques, de seuils, et un nombre d'agents justifié.

## Corpus de lecture (10 études)

Les études 01 à 05 forment la sélection de départ. Les études 06 à 10, ajoutées le 2026-11-12, comblent ses trois manques : récit autobiographique, suivi d'une même personne dans le temps, stade MCI.

| # | Étude | Ce qu'elle apporte | Fiche | Statut |
|---|-------|--------------------|-------|--------|
| 1 | Snowdon et al. 1996, *JAMA* : The Nun Study | densité d'idées à l'écrit, prédiction à 58 ans | [01](studies/01-snowdon-1996.md) | ⏳ |
| 2 | Fraser, Meltzer & Rudzicz 2016, *J Alzheimers Dis* | features linguistiques + acoustiques, 4 facteurs d'atteinte | [02](studies/02-fraser-2016.md) | ⏳ |
| 3 | Garrard et al. 2005, *Brain* : Iris Murdoch | dérive lexicale longitudinale chez une même personne | [03](studies/03-garrard-2005.md) | ⏳ |
| 4 | Agbavor & Liang 2022, *PLOS Digit Health* | embeddings de LLM contre features construites à la main | [04](studies/04-agbavor-2022.md) | ⏳ |
| 5 | de la Fuente Garcia, Ritchie & Luz 2020, *J Alzheimers Dis* | revue systématique de 51 études | [05](studies/05-de-la-fuente-garcia-2020.md) | ⏳ |
| 6 | Pistono et al. 2016, *J Alzheimers Dis* | pauses dans le rappel d'un épisode vécu, MCI, équipe française | [06](studies/06-pistono-2016.md) | ⏳ |
| 7 | Murphy et al. 2008, *Neuropsychologia* | souvenirs de 5 périodes de vie : moins de détails vécus au stade MCI | [07](studies/07-murphy-2008.md) | ⏳ |
| 8 | Mueller et al. 2018, *Front Aging Neurosci* | 264 personnes sur 2 ans : sémantique et fluence baissent dès le MCI très précoce | [08](studies/08-mueller-2018.md) | ⏳ |
| 9 | Robin et al. 2023, *Alzheimers Dement (Amst)* | parole ouverte sur 18 mois, score composite (Winterlight) | [09](studies/09-robin-2023.md) | ⏳ |
| 10 | Kemper, Marquis & Thompson 2001, *Psychol Aging* | déclin normal du langage, le plus rapide vers 75 ans | [10](studies/10-kemper-2001.md) | ⏳ |

Autres lectures vérifiées, non retenues dans le corpus pour l'instant : [`candidates.md`](candidates.md).

Statuts : ⏳ pas commencée · 📖 en lecture · ✅ lue, implications reportées dans la synthèse.

> ⚠️ **Références vérifiées le 2026-11-11 via l'API PubMed.** La liste de départ contenait des identifiants erronés pour 4 études sur 5 (titres, DOI, PMID ou PMCID renvoyant à d'autres articles). Les fiches utilisent les identifiants corrigés ; le détail est dans la ligne « Corrections » de chaque fiche. À reprendre tels quels dans toute citation (pitch, dossier du challenge, code).

## Protocole de prise de notes

1. **Ouverture d'une étude.** Tu me donnes la référence (titre, PDF ou lien). Je crée `studies/NN-premier-auteur-annee.md` à partir de [`_template.md`](_template.md) et je remplis la fiche d'identité.
2. **Pendant la lecture.** Dès qu'un passage t'intéresse, tu me le colles ou tu me le dictes, avec ton commentaire si tu en as un. Pour chaque passage, je :
   - l'ajoute à la section « Passages notés » de la fiche, avec la page ou la section ;
   - le reformule en une phrase ;
   - lui mets un ou plusieurs tags (liste ci-dessous) ;
   - si le passage confirme ou contredit une hypothèse, je mets à jour [`synthesis.md`](synthesis.md) tout de suite.
3. **Fin d'une étude.** Je remplis les sections « Biomarqueurs », « Limites » et « Implications pour ChronoVoice », puis je te les fais valider.
4. **Fin de la discovery.** On relit `synthesis.md` ensemble et on fige l'architecture (nombre d'agents, métriques, seuils). Ensuite seulement, on écrit `schemas.py`.

### Tags

| Tag | Sens |
|-----|------|
| `#biomarqueur` | une mesure linguistique ou acoustique et son lien avec le déclin |
| `#seuil` | une valeur chiffrée exploitable (seuil, taille d'effet, AUC, fenêtre) |
| `#méthode` | comment la mesure est calculée (outil, prétraitement, fenêtre) |
| `#longitudinal` | ce qui concerne l'évolution intra-individuelle dans le temps |
| `#tâche` | le type de parole recueillie (description d'image, récit, conversation) |
| `#biais` | biais culturel, langue, niveau d'études, âge, qualité audio |
| `#contexte` | facteurs confondants (sommeil, humeur, médicaments, fatigue) |
| `#archi` | remet en cause le découpage en agents ou le pipeline |
| `#éthique` | consentement, positionnement non diagnostique, réglementation |
