---
type: spec
title: Prototype ChronoVoice — vue d'ensemble
description: Périmètre du prototype à rendre le 2026-11-20, scénario de démo, décisions issues du questionnaire et critères de réussite.
status: draft
tags: [specs, prototype, scope, demo]
generated: "2026-11-12"
---

# Prototype ChronoVoice : vue d'ensemble

> Spec v1 du 2026-11-12, tirée du [questionnaire](questions.md), où toutes les propositions ont été validées. Elle s'appuie sur l'architecture v0.3 ([synthesis.md](../discovery/synthesis.md), section 4) et sur le cadre du challenge ([challenge.md](../challenge.md)).

## 1. Ce que fait le prototype

Un soignant de soins primaires enregistre au micro une personne âgée qui raconte un souvenir. ChronoVoice :

1. transcrit l'enregistrement ;
2. mesure des marqueurs de langage ;
3. compare la séance à la **référence personnelle** de la personne ;
4. propose un **niveau d'orientation** non diagnostique, avec ses preuves et son incertitude.

Le prototype a trois parties, chacune avec sa spec :

| Partie | Spec |
|---|---|
| Pipeline d'analyse (étapes 0 à 4) | [pipeline.md](pipeline.md) |
| Interface soignant et enregistrement au micro | [clinician-ui.md](clinician-ui.md) |
| API, stockage, intégration externe | [api.md](api.md) |
| Données de démonstration | [synthetic-data.md](synthetic-data.md) |

## 2. Scénario de démo (7 minutes)

Choix des questions Q1 et Q2 du questionnaire.

1. **Liste des personnes suivies** : 3 personas synthétiques, chacune avec son niveau d'orientation.
2. **Fiche de Margaret** : sa dérive a déclenché « revue par un professionnel recommandée ». Le soignant voit :
   - quels marqueurs ont bougé ;
   - sur quels passages du récit ;
   - avec quelle incertitude.
3. **Synthèse** : il la relit et la valide. Il voit aussi l'explication en langage clair destinée à la personne.
4. **Nouvelle séance en direct** : un membre de l'équipe raconte un souvenir au micro, ce qui crée une nouvelle personne suivie.
5. **Résultat**, en moins de 2 minutes : les marqueurs sont affichés, mais **aucune alerte**, car il faut 3 séances de référence. Le jury voit le garde-fou fonctionner.

## 3. Périmètre

**Dans le prototype**

- Enregistrement au micro dans le navigateur, et import d'un fichier audio.
- Transcription par ElevenLabs Scribe v3 ([référence technique](../tech/elevenlabs-scribe.md)).
- Contrôle qualité de chaque séance.
- 6 marqueurs dans l'indice d'écart, affiché « Change from baseline » ; pauses et MATTR affichés à part.
- Référence personnelle, test de l'écart, 3 niveaux d'orientation.
- Analyste du récit, réduit et marqué expérimental : épisodes et répétitions.
- Synthèse clinique et explication en langage clair, relues et validées par le soignant.
- Profil de risque en lecture seule, à côté du score et jamais mélangé avec lui.
- Endpoint d'intégration pour une application externe (MyMémoires).
- Mise en ligne avec accès invité, interface en anglais.

**Hors prototype** : à présenter dans le deck comme feuille de route.

- Adaptateurs pour d'autres langues que l'anglais.
- Incohérences de dates entre séances (H7).
- Part de détails vécus (fiche 07), sauf s'il reste du temps.
- Profondeur syntaxique (priorité 2).
- Calcul d'un risque à partir du profil.
- Enregistrement à domicile par la personne elle-même.
- Validation clinique sur la population locale.

## 4. Décisions du questionnaire

| Thème | Décision | Q |
|---|---|---|
| Démo | Parcours soignant ; la séance en direct crée une nouvelle personne, sans alerte | Q1, Q2 |
| Personas | 3 personas anglophones de 70 à 80 ans : stable, déclin progressif, stable avec une séance dégradée | Q3 |
| Rythme | Environ 10 séances de 5 minutes, toutes les 2 semaines | Q4 |
| Données | Récits écrits par un LLM, convertis au format Scribe | Q5 |
| Micro | Le soignant enregistre depuis l'interface. Question d'amorce, cible de 5 min, séance « partielle » sous 2 min ou 150 mots, maximum 15 min, import de fichier possible | Q6 à Q9 |
| Consentement et contexte | Case de consentement obligatoire ; 5 champs de contexte qui pondèrent la fiabilité de la séance | Q10, Q11 |
| Marqueurs | Sémantique et fluence ; MATTR en plus | Q12 |
| Outils NLP | spaCy `en_core_web_sm` ; liste de fréquences choisie selon sa licence | Q13 |
| Analyste du récit | Version réduite, expérimentale, hors index | Q14 |
| LLM | Claude Opus 5.5 pour les étapes 2 et 4 | Q15, Q36 |
| Orientation | Stable, à surveiller, revue recommandée ; rien avant 3 séances | Q16 |
| Attente | Traitement en arrière-plan avec statut ; moins de 2 min pour 5 min d'audio | Q17 |
| Utilisateur | Soins primaires (médecin généraliste, infirmier de prévention) | Q18 |
| Écrans | Liste, fiche, détail de séance, nouvelle séance, synthèse imprimable | Q19 |
| Supervision humaine | Bouton « Reviewed and validated » ; synthèse en brouillon tant qu'elle n'est pas validée | Q20 |
| Personne suivie | Explication en langage clair, relue par le soignant | Q21 |
| Profil de risque | Lecture seule, à côté du score, recommandations sourcées, pas de calcul | Q22 |
| Langue | Interface en anglais | Q23 |
| Mise en ligne | Un seul service (FastAPI sert aussi le frontend), sur Render, avec l'offre payante d'entrée pendant l'évaluation | Q24, Q41, Q43 |
| Stockage | SQLite ; audio supprimé après transcription, transcript supprimé chez ElevenLabs | Q25 |
| Code | Dépôt GitHub privé | Q26 |
| Équipe | Thibaut seul | Q27, Q42 |
| Intégration | Une slide et un endpoint documenté pour MyMémoires | Q28 |

### Arbitrages complémentaires (2026-11-12)

Ce sont les points incertains des specs, tranchés par les questions Q29 à Q43 du [questionnaire](questions.md).

| Point | Décision |
|---|---|
| Séance en écart | Au moins 2 des 6 marqueurs de l'indice sont significatifs (règle du 2026-11-13, calibrée par simulation) |
| Revue recommandée | 2 séances consécutives en écart, ou une chute rapide : au moins 4 marqueurs significatifs sur une séance |
| Référence personnelle | Démarre à 3 séances, grandit jusqu'à 5 tant que les séances sont stables, puis se fige |
| Contexte défavorable | Une telle séance déclenche au plus « à surveiller » ; elle ne confirme pas seule une revue |
| Séance partielle | Moins de 150 mots ou moins de 2 minutes de parole |
| Voix suivie | Automatique : le locuteur qui parle le plus |
| Fréquence des mots | Calculée sur les mots pleins |
| Nom du score | « Change from baseline », en écarts-types ; « Brain Health Index » est abandonné pour le score |
| Chiffres | Des mots d'abord ; valeurs, écarts et tests dans un panneau « Details » |
| Génomique | Une ligne « Genomic data: not shared » dans le profil de risque |
| Personas | Margaret, Rajesh et Grace, telles que décrites |
| Hébergeur | Render ; Vercel est écarté (limite de 4,5 Mo par requête, pas de tâche de fond longue, pas de SQLite persistant) |

## 5. Critères de réussite du prototype

1. **De bout en bout** : une séance de 5 minutes au micro donne un résultat en moins de 2 minutes, sans erreur.
2. **Marqueurs** : chaque marqueur est une fonction pure, testée sur des cas calculés à la main, et cite sa source (règle 2 de CLAUDE.md).
3. **Vocabulaire** : aucun mot diagnostique ne sort de la synthèse. Le validateur le vérifie, et un test aussi.
4. **Incertitude** : chaque score montre son incertitude, le nombre de séances de référence et la qualité de la séance (règle 5).
5. **Personas** : le scénario de démo se rejoue à l'identique à chaque fois, car les données sont générées une fois puis figées.
6. **Accès** : le jury ouvre le prototype en ligne sans créer de compte.

## 6. Points encore ouverts

- **MyMémoires** (Q28) : ce qu'il enregistre et à quel rythme, à préciser par Thibaut.
- **Tests de Scribe** ([référence technique](../tech/elevenlabs-scribe.md), section 9). Ils fixeront la détection des faux départs, le seuil de confiance du contrôle qualité et la validité des frontières d'énoncés.
- **Liste de fréquences des mots** : à choisir selon sa licence.
