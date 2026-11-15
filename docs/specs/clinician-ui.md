---
type: spec
title: Interface soignant et enregistrement au micro — spec v1
description: Écrans du prototype pour le personnel de soins primaires (liste, fiche personne, détail de séance, nouvelle séance au micro, synthèse imprimable), règles d'affichage de l'incertitude et parcours d'enregistrement.
status: draft
tags: [specs, frontend, dashboard, clinician, microphone, ux]
generated: "2026-11-12"
---

# Interface soignant et enregistrement au micro : spec v1

> Spec v1 du 2026-11-12, issue des questions Q6 à Q11 et Q18 à Q23 du [questionnaire](questions.md). Les calculs affichés sont définis dans [pipeline.md](pipeline.md).

## 1. Principes

- **Utilisateur** : un professionnel de soins primaires, médecin généraliste ou infirmier d'un programme de prévention, qui suit beaucoup de personnes (Q18).
- **Langue** : l'interface est en anglais (Q23). Le vocabulaire est non diagnostique : « signals to monitor », « change from personal baseline », « a memory clinic consultation may be useful ».
- **Identité visuelle** (CLAUDE.md) :
  - **ardoise** pour la structure et le texte ;
  - **sauge** pour ce qui est stable et pour la référence ;
  - **terracotta** pour les écarts significatifs ;
  - jamais de rouge alarmiste : la personne suivie peut voir l'écran.
- **Incertitude toujours visible** à côté d'un score : le nombre de séances de référence, l'intervalle et le statut de qualité de la séance (règle 5).
  - L'« intervalle » est l'étendue de l'indice d'écart sur les séances de référence, du minimum au maximum (« their changes ranged from X to Y SD »). **Ce n'est pas un intervalle de confiance.**
  - Exception dans le prototype (relevée le 2026-11-15) : l'en-tête de l'écran 3 affiche l'indice et le nombre de marqueurs hors zone, mais pas le nombre de séances de référence ; la qualité de la séance est dans un panneau à côté.
- **Des mots d'abord, les chiffres sur demande** (décision du 2026-11-12) : la fiche explique en phrases ; les valeurs, écarts-types, `t` et seuils sont dans un panneau dépliable « Details ».
- **Démo** : accès invité, sans compte (slide 11 du template). Un bandeau permanent indique « Demo workspace · synthetic data · screening support only, not a diagnosis » ; il est masqué à l'impression.
- **Cible** : ordinateur de bureau, en consultation. Un affichage correct sur tablette suffit.

## 2. Écrans

### Écran 1 : liste des personnes suivies (`/`)

- **Tableau**, avec une colonne par information :
  - nom ;
  - âge ;
  - date de la dernière séance ;
  - nombre de séances (utilisables / total) ;
  - niveau d'orientation (pastille) ;
  - état de la référence (colonne « Baseline » : « Building 2/3 » ou « 3 sessions ») ;
  - « processing… » tant qu'une séance est en cours de traitement, et le badge « Synthetic » pour les personas.
- **Pastilles**, chacune avec une icône et un libellé, jamais la couleur seule :

  | Niveau | Libellé affiché | Icône | Couleur |
  |---|---|---|---|
  | `review_recommended` | Review recommended | stéthoscope | terracotta |
  | `monitor` | Signals to monitor | œil | terracotta clair |
  | `stable` | Within usual range | coche | sauge |
  | `building_baseline` | Building baseline n/3 | cercle en pointillés | ardoise |
- **Tri** par défaut : `review_recommended` en premier, puis `monitor`, puis le reste.
- **Actions** : « New person » en haut de la page, « New session » sur chaque ligne.

### Écran 2 : fiche d'une personne (`/people/:id`)

1. **En-tête** : nom, âge, langue, badge « Synthetic », date de la première séance.
2. **Carte d'orientation** :
   - le niveau ;
   - la règle qui l'a déclenché, en une phrase ;
   - l'action proposée ;
   - l'incertitude ;
   - le contexte défavorable s'il y en a un.
3. **Courbe « Change from baseline »** dans le temps. C'est l'indice d'écart, en écarts-types de la variabilité habituelle de la personne ; 0 veut dire « comme d'habitude » :
   - une bande ombrée, « Range of the baseline sessions », couvre l'étendue de l'indice sur les séances de référence ;
   - une séance en écart est marquée, avec son nombre de marqueurs significatifs ;
   - chaque point est coloré selon la qualité de la séance (pleine pour `usable`, creuse pour `partial`) ;
   - les séances `rejected` sont marquées sur l'axe du temps.
4. **Sous-scores** sémantique et fluence, en petites courbes.
5. **Marqueurs**, en petites courbes :
   - une par marqueur ;
   - une flèche indique le sens du déclin ;
   - une info-bulle donne la définition et la fiche source.

   Les pauses et le MATTR sont dans un bloc à part, « Shown for context, not in the index ».
6. **Récit (expérimental)** : les anecdotes répétées, avec les séances et les passages, sous un badge « Experimental, not in the index ».
7. **Profil de risque** (Q22) :
   - en lecture seule, avec des données synthétiques ;
   - affiché à côté du score, jamais mélangé avec lui ;
   - accompagné d'une mention « Shared with consent » ;
   - avec une ligne « Genomic data: not shared », qui montre que le consentement se donne type de donnée par type de donnée ;
   - suivi des suggestions de prévention sourcées. **Pas dans le prototype** : elles viendront d'une liste fixe tirée de la Commission Lancet 2024, encore en relecture. La carte le dit, et n'en affiche aucune.
8. **Synthèse** :
   - le résumé pour le soignant (constats reliés aux marqueurs, aux passages et aux études) ;
   - la phrase sur l'incertitude ;
   - l'explication en langage clair pour la personne (Q21) ;
   - l'origine du texte : « Written by a language model (<modèle>), checked against the measurements », ou « Fixed wording built from the measurements » pour le texte fixe de repli ;
   - le statut `Draft` ou `Validated by <name> on <date>`, avec le bouton « Reviewed and validated » (Q20) ;
   - le bouton « Print », qui ouvre l'écran 5.
9. **Liste des séances** : date, thème, statut de qualité, temps de parole de la personne, statut du traitement ; elle mène à l'écran 3.

Dans le code, l'ordre est un peu différent : en-tête (avec les boutons « Report » et « New session »), carte d'orientation, courbe, puis deux colonnes (synthèse, sous-scores et marqueurs ; profil de risque et récit, titré « Life story »), et enfin la liste des séances.

### Écran 3 : détail d'une séance (`/sessions/:id`)

- **Transcription surlignée** (l'audio n'est pas conservé, Q25) :
  - hésitations ;
  - répétitions ;
  - pauses ≥ 250 ms, avec leur durée en ligne ;
  - tours de l'interlocuteur grisés ;
  - événements sonores en italique.
- **Tableau des marqueurs** : valeur de la séance, moyenne ± écart-type de la référence, `t` orienté, significatif ou non, et sens du déclin.
- **Rapport de qualité** : statut, raisons, nombre de mots, temps de parole, confiance, part de parole de la personne suivie.
- **Contexte saisi** et thème de la question d'amorce.
- **Comparaison** côte à côte avec une séance de référence au choix : mêmes surlignages, et marqueurs en regard.
- Ajouts du code : les mots coupés sont barrés ; le tableau des marqueurs donne `t` avec ses degrés de liberté, et rappelle le test (Crawford–Howell unilatéral, α = 0,05) ; la question d'amorce est dans l'en-tête ; les séances de référence sont signalées dans le choix de la comparaison.
- **Pendant le traitement**, la page se met à jour toute seule toutes les 2 secondes. **Une séance en échec** affiche l'erreur et un bouton « Try again » (`POST /api/sessions/{id}/retry`), utilisable tant que l'audio est encore sur le serveur.

### Écran 4 : nouvelle séance (`/people/:id/new-session`)

C'est un parcours en 5 temps, sur une seule page.

1. **Consentement** (Q10) : une case obligatoire « Consent obtained for this recording », avec une phrase sur l'usage des données. Sans elle, on ne peut pas enregistrer.
2. **Contexte** (Q11) : 5 champs rapides.
   - sommeil de la nuit : good, average, poor ;
   - fatigue : oui ou non ;
   - maladie aiguë : oui ou non ;
   - nouveau traitement depuis la dernière séance : oui ou non ;
   - humeur : good, neutral, low.
3. **Question d'amorce** (Q7) :
   - une carte affiche un thème de vie tiré de la banque : enfance, travail, famille, un voyage, une fête… ;
   - le thème n'a jamais servi pour cette personne ; une fois tous les thèmes utilisés, c'est celui posé il y a le plus longtemps ;
   - deux relances neutres sont proposées (« What happened next? », « Can you tell me more about that? ») ;
   - un bouton permet de tirer un autre thème.
4. **Enregistrement** (Q8, Q9) :
   - **Démarrage** : bouton « Start recording », demande d'accès au micro, indicateur de niveau sonore.
   - **Pendant l'enregistrement** : chronomètre avec la cible de 5 minutes ; avant 2 minutes, un message prévient que la séance sera « partial ». Ce message suit le chronomètre : c'est une approximation. Le serveur classe la séance `partial` d'après la parole de la personne elle-même : moins de 120 s de parole, moins de 150 mots, ou une confiance moyenne sous 50 % ([pipeline.md](pipeline.md), étape 0).
   - **Arrêt** : bouton « Stop » ; l'enregistrement s'arrête automatiquement à 15 minutes. Le soignant choisit ensuite « Send for analysis » (avec la progression de l'envoi en %) ou « Record again ».
   - **Autre entrée** : le lien « Upload an audio file » remplace le micro (fichiers audio, et vidéo en MP4 ou WebM ; 100 Mo au plus).
5. **Traitement** (Q17) : un suivi par étapes (« Transcribing → Analysing → Writing summary → Done »), mis à jour toutes les 2 secondes. À la fin, on passe à l'écran 3.

**Erreurs à prévoir**

| Situation | Message et action |
|---|---|
| Accès au micro refusé | explication, et proposition d'importer un fichier |
| Aucun son détecté au bout de 10 secondes | avertissement |
| Échec réseau à l'envoi | nouvel essai (« Send again »), sans perdre l'enregistrement |
| Séance `rejected` | affichage des raisons |
| Traitement en échec (`failed`) | message, et lien vers l'écran 3 pour relancer le traitement |

**Nouvelle personne** (`/people/new`) : un formulaire minimal (nom ou pseudonyme, année de naissance, langue, fixée à « English » dans le prototype), puis directement l'écran 4. C'est le parcours de la démo en direct (Q2).

### Écran 5 : synthèse imprimable (`/people/:id/report`)

- Une page A4 propre, faite avec une feuille de style d'impression.
- Contenu : le niveau, la règle qui l'a déclenché, les constats, l'incertitude, l'action proposée, l'explication pour la personne et le statut de validation.
- En pied de page, une mention : « Screening support only, not a diagnosis ».

## 3. Enregistrement : aspects techniques

- **Capture** : API `MediaRecorder` du navigateur. Le format est `audio/webm;codecs=opus` (Chrome, Firefox) ou `audio/mp4` (Safari). Scribe accepte les deux.
- **Envoi** : un seul `POST` en multipart, quand le soignant choisit « Send for analysis » après l'arrêt, avec l'audio et les métadonnées ([api.md](api.md)). Pas de streaming dans le prototype.
- **Taille** : l'API refuse un fichier de plus de 100 Mo (`413`). 15 minutes en opus restent bien en dessous, comme de la limite de 5 Go de Scribe.
- **Contexte sécurisé** : le micro n'est accessible qu'en HTTPS (ou en `localhost`). La mise en ligne doit donc être en HTTPS.

## 4. Stack frontend

- Vite, React, TypeScript strict, Tailwind, Lucide, Recharts (CLAUDE.md), et React Router pour les adresses des écrans.
- Les types reflètent `schemas.py`, avec les mêmes noms de champs en snake_case.
- Le frontend construit est servi par FastAPI : un seul service à mettre en ligne (Q24).

## 5. Précisions du 2026-11-14, en codant le frontend

- **Code** : `frontend/src/` ; pages dans `pages/`, sections dans `components/`, appels à l'API dans `api/client.ts`.
- **Types** : générés à partir de la description OpenAPI du backend (`npm run gen:api`), pour refléter exactement les modèles Python. Seuls sont écrits à la main le JSON `metadata` d'un envoi de séance, car il voyage dans un champ de formulaire, et deux constantes recopiées du backend (`MIN_SIGNIFICANT_MARKERS`, `MIN_BASELINE_SESSIONS`).
- **Couleurs** : sauge `#5e9384` et terracotta `#b9522c`, contrôlés avec le validateur de palettes de la compétence dataviz : écart de 10,9 pour les daltoniens (cible 8). Le sauge est peu saturé, comme le veut la charte : un niveau s'affiche donc toujours avec une icône et un libellé, jamais par la couleur seule. Pas de mode sombre dans le prototype.
- **Courbe « Change from baseline »** : graduations en écarts-types entiers ; le point d'une séance en écart est terracotta et porte son nombre de marqueurs ; un clic sur un point ouvre la séance ; info-bulle avec réticule au survol ; tableau des valeurs dans « Details ».
- **Petits graphiques des marqueurs** : la bande ombrée est la moyenne de la référence ± 1 écart-type. Ce n'est pas le seuil du test : un point est marqué quand le test de la séance le trouve hors de la zone. Pour les pauses, dont le sens lié au déclin n'est pas établi, l'écran l'indique au lieu d'une flèche.
- **Comparaison de deux séances** : un tableau compact (marqueur, cette séance, référence), puis les deux transcriptions côte à côte.
- **Micro** : la réduction de bruit du navigateur est coupée, car elle pourrait effacer les hésitations que compte l'indice de fluence. L'enregistrement reste en mémoire jusqu'à l'envoi : un échec réseau permet de renvoyer sans réenregistrer.
- **Validation de la synthèse** : le nom du soignant est demandé à côté du bouton, puis gardé dans le navigateur pour la fois suivante.
- **Service** : FastAPI sert le frontend construit (`frontend/dist`) pour toute adresse hors de `/api`. En développement, Vite renvoie `/api` vers le backend.

