---
type: spec-questionnaire
title: Questionnaire des specs du prototype
description: Questions à trancher avant de rédiger les specs du prototype (pipeline d'analyse, interface soignant, enregistrement au micro), avec une proposition par défaut pour chacune.
status: stable
tags: [specs, prototype, questionnaire, pipeline, dashboard, microphone]
generated: "2026-11-12"
---

# Questionnaire des specs du prototype

Le prototype doit avoir trois choses :

- une **pipeline d'analyse solide** ;
- une **interface pour le personnel soignant** ;
- en entrée, l'**enregistrement au micro**.

Chaque question vient avec une proposition. **Toutes les propositions ont été validées le 2026-11-12.** Reste à préciser : MyMémoires (Q28). Les points incertains des specs ont été tranchés par les questions complémentaires Q29 à Q43. Les specs qui en découlent sont listées dans [index.md](index.md).

## A. La démo et son histoire

Le jury voit environ 7 minutes de démonstration, puis 3 minutes de questions ([challenge.md](../challenge.md), section 3).

**Q1. Quel parcours montre-t-on ?**
Proposition :

1. Le soignant ouvre la liste des personnes qu'il suit.
2. Il ouvre une persona synthétique qui a une dizaine de séances. Sa dérive déclenche « revue par un professionnel recommandée ».
3. Il lit pourquoi : quels marqueurs ont bougé, sur quels passages du récit, avec quelle incertitude.
4. Il lance une nouvelle séance au micro, en direct.
5. Le résultat arrive en moins de 2 minutes.

Réponse : ok, proposition validée le 2026-11-12.

**Q2. Qui parle au micro pendant la démo, et à qui compare-t-on cette séance ?**
Une voix réelle ne peut pas être comparée à la référence d'une persona synthétique : ce n'est pas la même personne.
Proposition :

- La séance en direct crée une **nouvelle personne suivie**.
- Avec une seule séance, l'interface affiche les marqueurs mais **aucune alerte**, à cause de la règle des 3 séances de référence. Le jury voit ainsi le garde-fou fonctionner.
- La dérive se montre sur les personas synthétiques.

Réponse : ok, proposition validée le 2026-11-12.

**Q3. Combien de personas, avec quels profils ?**
Proposition : 3 personas anglophones de 70 à 80 ans.

- **Stable.**
- **Déclin progressif.**
- **Stable, sauf une séance dégradée** (mauvaise nuit ou audio de mauvaise qualité), pour montrer le contrôle qualité et la prise en compte du contexte.

Réponse : ok, proposition validée le 2026-11-12.

**Q4. À quel rythme ont lieu leurs séances ?**
Proposition : environ 5 minutes de récit toutes les 2 semaines pendant 5 mois, soit à peu près 10 séances par persona. Les échantillons de 5 minutes suivent mieux l'évolution que ceux d'1 minute (Petti 2023, [candidates](../discovery/candidates.md)), et la parole libre varie beaucoup d'une séance à l'autre (fiche 09).

Réponse : ok, proposition validée le 2026-11-12.

**Q5. Comment fabrique-t-on les séances des personas ?**
Trois options :

- **(a)** Des récits écrits par un LLM, avec des hésitations, des pauses et une dérive contrôlées, convertis au format de réponse de Scribe : des mots horodatés, mais pas d'audio.
- **(b)** Des récits lus par une voix de synthèse, puis passés dans la vraie chaîne.
- **(c)** Des enregistrements humains.

Proposition : **(a)**. On contrôle exactement la dérive, et tout ce qui suit la transcription est identique à la vraie chaîne. La séance au micro prouve, elle, que la chaîne complète fonctionne.

Réponse : ok, proposition validée le 2026-11-12.

## B. L'enregistrement au micro

**Q6. Qui enregistre en usage réel : le soignant pendant une consultation, ou la personne seule chez elle ?**
Proposition : pour le prototype, le soignant, depuis l'interface (bouton « Nouvelle séance »). L'usage à domicile passera par une intégration, MyMémoires par exemple.

Réponse : ok, proposition validée le 2026-11-12.

**Q7. Comment lance-t-on le récit ?**
Proposition :

- L'interface affiche au soignant une question d'amorce, tirée d'une banque de thèmes de vie : enfance, travail, famille, un voyage…
- Le thème change à chaque séance.
- Une ou deux relances neutres sont proposées.

Réponse : ok, proposition validée le 2026-11-12.

**Q8. Quelle durée ?**
Proposition :

- un chronomètre visible ;
- une cible de 5 minutes ;
- la séance est marquée « partielle » sous 2 minutes ou sous 150 mots (minimum cité par la fiche 08) ;
- le soignant arrête l'enregistrement lui-même, avec un maximum de 15 minutes.

Réponse : ok, proposition validée le 2026-11-12.

**Q9. Ajoute-t-on l'import d'un fichier audio, en plus du micro ?**
Proposition : oui. C'est utile pour les tests et pour simuler une intégration.

Réponse : ok, proposition validée le 2026-11-12.

**Q10. Que montre-t-on pour le consentement ?**
Proposition : une case « consentement recueilli », obligatoire avant d'enregistrer, avec une phrase sur l'usage des données.

Réponse : ok, proposition validée le 2026-11-12.

**Q11. Qui saisit le contexte de la séance (sommeil, fatigue, maladie, nouveau traitement, humeur), et quand ?**
Proposition : le soignant, en 5 champs rapides, juste avant ou juste après l'enregistrement. Ce contexte pondère la fiabilité de la séance ; ce n'est pas un facteur de risque ([synthesis.md](../discovery/synthesis.md), H9).

Réponse : ok, proposition validée le 2026-11-12.

## C. La pipeline d'analyse

**Q12. Quels marqueurs dans le prototype ?**
Proposition :

- **Sémantique** : indice pronominal, part des noms, fréquence et longueur des mots.
- **Fluence et temps** : hésitations, faux départs, répétitions, pauses entre et dans les énoncés, mots par minute.
- **En plus** : MATTR, et la profondeur syntaxique si le temps le permet.

Réponse : ok, proposition validée le 2026-11-12.

**Q13. Accepte-t-on spaCy (analyse grammaticale de l'anglais) et une liste de fréquences des mots anglais ?**
Proposition : oui, avec le modèle `en_core_web_sm` de spaCy. La liste de fréquences sera choisie selon sa licence, qu'il faudra déclarer dans la slide 13.

Réponse : ok, proposition validée le 2026-11-12.

**Q14. Met-on l'analyste du récit (étape 2, LLM) dans le prototype ?**
Proposition : une version réduite.

- Découpage du récit en épisodes, et repérage des répétitions d'une séance à l'autre.
- Affiché à part, marqué « expérimental », hors du Brain Health Index.
- La part de détails vécus (fiche 07) seulement s'il reste du temps.

Réponse : ok, proposition validée le 2026-11-12.

**Q15. Quel LLM pour les étapes 2 et 4 ?**
Proposition : Claude, le modèle le plus récent, par l'API Anthropic. L'alternative serait Mistral.

Réponse : ok, proposition validée le 2026-11-12.

**Q16. Quels niveaux d'orientation ?**
Proposition : trois niveaux, et aucun avant 3 séances de référence valides. Les seuils exacts suivent la v0.3 : un écart compte s'il dépasse le bruit, selon l'indice de changement fiable ([synthesis.md](../discovery/synthesis.md), section 4).

- **Stable.**
- **À surveiller** : un écart significatif isolé. On propose de refaire une séance sous 2 semaines.
- **Revue par un professionnel recommandée** : un écart significatif sur 2 séances consécutives, ou une chute rapide.

Réponse : ok, proposition validée le 2026-11-12.

**Q17. Combien de temps le soignant peut-il attendre le résultat ?**
Proposition : le traitement tourne en arrière-plan, avec un statut visible (transcription, analyse, synthèse). Cible : moins de 2 minutes pour 5 minutes d'audio.

Réponse : ok, proposition validée le 2026-11-12.

## D. L'interface soignant

**Q18. Qui est l'utilisateur principal ?**
Proposition : un professionnel de soins primaires, médecin généraliste ou infirmier d'un programme de prévention, qui suit beaucoup de personnes. Le gériatre ou le neurologue intervient ensuite.

Réponse : ok, proposition validée le 2026-11-12.

**Q19. Quels écrans ?**
Proposition : 4 écrans indispensables et 1 souhaitable.

1. **Liste des personnes suivies**, avec le niveau d'orientation et la date de la dernière séance.
2. **Fiche d'une personne** : Brain Health Index, sous-scores par famille de marqueurs, courbes dans le temps avec la bande du bruit normal, incertitude.
3. **Détail d'une séance** : transcription surlignée (pauses, hésitations, répétitions), et comparaison avec une séance de référence.
4. **Nouvelle séance**, au micro.
5. *Souhaitable* : une synthèse imprimable.

Réponse : ok, proposition validée le 2026-11-12.

**Q20. Le soignant doit-il valider la synthèse ?**
Proposition : oui, avec un bouton « Relu et validé ». Tant qu'elle n'est pas validée, la synthèse reste marquée « brouillon ». C'est la supervision humaine demandée par l'exigence 5 du challenge.

Réponse : ok, proposition validée le 2026-11-12.

**Q21. Ajoute-t-on une explication en langage clair pour la personne (exigence 4 du challenge) ?**
Proposition : oui. Un second encadré, rédigé par l'étape 4 et relu par le soignant avant d'être partagé.

Réponse : ok, proposition validée le 2026-11-12.

**Q22. Jusqu'où va le profil de risque (exigence 3 : sommeil, santé métabolique, antécédents familiaux, génomique…) ?**
Proposition :

- Un volet en lecture seule dans la fiche, avec des données synthétiques.
- Affiché à côté du score, sans jamais s'y mélanger.
- Accompagné de recommandations de prévention sourcées.
- Pas de calcul de risque.

Réponse : ok, proposition validée le 2026-11-12.

**Q23. En quelle langue est l'interface ?**
Proposition : en anglais, comme le prototype.

Réponse : ok, proposition validée le 2026-11-12.

## E. Technique et mise en ligne

**Q24. Où héberge-t-on la démo ?**
Proposition : un seul service, le backend FastAPI qui sert aussi le frontend, sur une plateforme simple comme Render, Railway ou Fly.io. As-tu déjà un compte quelque part ?

Réponse : un seul service, sur **Render** (voir Q41 et Q43).

**Q25. Que stocke-t-on ?**
Proposition :

- une base SQLite ;
- l'audio est supprimé après la transcription, et la transcription est supprimée chez ElevenLabs ;
- on ne garde que la transcription et les mesures.

Réponse : ok, proposition validée le 2026-11-12.

**Q26. Met-on le code sur un dépôt GitHub privé ?**
Le jury peut demander le code.
Proposition : oui, privé, partagé sur demande.

Réponse : ok, proposition validée le 2026-11-12.

## F. Équipe et MyMémoires

**Q27. Qui est dans l'équipe, et qui fait quoi** (deck, démo, slides sur l'équipe) ?

Réponse : **Thibaut seul** (Q42).

**Q28. Qu'est-ce que MyMémoires ?** Qu'enregistre-t-il, à quel rythme, et comment veux-tu le montrer ?
Proposition : une slide, et un endpoint d'API documenté qui reçoit un enregistrement et ses métadonnées (personne, type de tâche, langue, consentement).

Réponse : proposition validée le 2026-11-12 (une slide et un endpoint d'intégration). Reste à préciser : ce qu'est MyMémoires, ce qu'il enregistre et à quel rythme.

## G. Questions complémentaires : points incertains des specs (2026-11-12)

Elles ont été posées après la rédaction des specs v1, et les réponses sont reportées dans les specs.

| # | Question | Réponse |
|---|---|---|
| Q29 | Combien de séances significatives consécutives pour « revue recommandée » ? | **2 séances** |
| Q30 | Garder une exception « chute rapide » (une séance très anormale, α = 0,01) ? | **Oui** |
| Q31 | Référence fixe sur 3 séances, ou qui grandit jusqu'à 5 tant que tout est stable ? | **Grandit jusqu'à 5**, puis se fige |
| Q32 | Une séance au contexte défavorable peut-elle confirmer seule une revue ? | **Non**, au plus « à surveiller » |
| Q33 | Seuil d'une séance partielle ? | **Moins de 150 mots ou moins de 2 minutes** de parole |
| Q34 | Comment choisir la voix suivie ? | **Automatique** : le locuteur qui parle le plus |
| Q35 | Fréquence des mots : sur quels mots ? | **Mots pleins** (noms, verbes, adjectifs, adverbes) |
| Q36 | Quel modèle Claude pour les étapes 2 et 4 ? | **Claude Opus 5.5** |
| Q37 | Nom et sens du score composite ? | **« Change from baseline »**, en écarts-types (0 = comme d'habitude) ; « Brain Health Index » n'est plus utilisé pour ce score |
| Q38 | Quels chiffres montrer au soignant ? | **Des mots d'abord**, les chiffres dans un panneau « Details » |
| Q39 | Une ligne génomique dans le profil de risque ? | **Oui**, « Genomic data: not shared » |
| Q40 | Les 3 personas (Margaret, Rajesh, Grace) ? | **Gardées telles quelles** |
| Q41 | Quelle plateforme de mise en ligne ? | Thibaut demande si **Vercel** est possible : voir Q43 |
| Q42 | Taille de l'équipe ? | **Thibaut seul** |
| Q43 | Vercel (avec Blob, découpage en 3 appels et Postgres) ou Render (spec inchangée) ? | **Render**, spec inchangée |

**Mise à jour du 2026-11-13 (Q30).** La chute rapide n'est plus définie par un seuil à α = 0,01 sur l'indice. Elle correspond à au moins 4 marqueurs significatifs sur 6 dans une même séance. L'idée validée reste la même : une seule séance très anormale suffit à recommander la revue. Le détail et la simulation sont dans [pipeline.md](pipeline.md), étape 3.
