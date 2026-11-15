---
type: spec
title: Pipeline d'analyse — spec v1
description: Étapes 0 à 4 du prototype (capture et qualité, marqueurs, analyste du récit, dérive longitudinale, synthèse clinique), définitions des marqueurs, test de l'écart, niveaux d'orientation et contrats entre étapes.
status: draft
tags: [specs, pipeline, biomarkers, longitudinal, orientation, llm]
generated: "2026-11-12"
sources:
  - name: Fiches d'études 06, 08, 09 (docs/discovery/studies)
  - name: Crawford JR, Garthwaite PH (2002). Investigation of the single case in neuropsychology. Neuropsychologia 40(8):1196-1208. DOI 10.1016/s0028-3932(01)00224-x. PMID 11931923
    url: https://doi.org/10.1016/s0028-3932(01)00224-x
  - name: Covington MA, McFall JD (2010). Cutting the Gordian Knot - The Moving-Average Type-Token Ratio (MATTR). J Quant Linguist 17(2):94-100. DOI 10.1080/09296171003643098 (vérifiée sur Crossref, non indexée par PubMed)
    url: https://doi.org/10.1080/09296171003643098
  - name: Livingston G et al. (2024). Dementia prevention, intervention, and care - 2024 report of the Lancet standing Commission. Lancet 404(10452):572-628. DOI 10.1016/S0140-6736(24)01296-0. PMID 39096926
    url: https://doi.org/10.1016/S0140-6736(24)01296-0
verified:
  by: PubMed E-utilities, et Crossref pour Covington & McFall 2010
  at: "2026-11-12"
---

# Pipeline d'analyse : spec v1

> Spec v1 du 2026-11-12. Elle précise l'architecture v0.3 ([synthesis.md](../discovery/synthesis.md), section 4) pour le prototype. Les **choix de conception non sourcés** sont signalés comme tels : la règle 2 de CLAUDE.md veut qu'ils soient étayés ou retirés avant la version finale.

```
Enregistrement + métadonnées
  → [0] Capture et qualité (Scribe + calcul)      → SessionTranscript, QualityReport
  → [1] Marqueurs (calcul pur)                    → SessionMetrics
  → [2] Analyste du récit (LLM, expérimental)     → NarrativeAnalysis
  → [3] Dérive longitudinale (statistique)        → LongitudinalComparisonResult
  → [4] Synthèse clinique (LLM contraint)         → ClinicalSummaryReport
```

## Étape 0 : capture et qualité

**Entrée** : un fichier audio et ses métadonnées (`RecordingMetadata`).

| Champ | Contenu |
|---|---|
| `person_id` | identifiant de la personne suivie |
| `task_type` | `life_story` dans le prototype |
| `language` | `eng` dans le prototype |
| `consent` | doit valoir `true` ; sinon la séance est refusée |
| `context` | 5 champs (voir l'étape 3) |
| `prompt_id` | identifiant de la question d'amorce |
| `source` | `clinician_ui` ou `integration` |
| `recorded_at` | date et heure de l'enregistrement |

**Traitement**

1. **Transcription** par ElevenLabs Scribe v3, avec les réglages de la [référence technique](../tech/elevenlabs-scribe.md), section 3 : verbatim, horodatage par mot, diarisation, langue imposée (celle des métadonnées). `num_speakers=2` n'est envoyé que pour un enregistrement fait dans l'interface (la personne et le soignant) ; pour une intégration, Scribe compte les voix lui-même.
   - **Si Scribe échoue** (fichier illisible, panne), la transcription est essayée deux fois, puis la séance passe en `failed` avec le message de Scribe. Elle n'est pas `rejected` : l'audio est gardé pour qu'on puisse relancer le traitement. Un fichier vide est refusé dès l'envoi (`422`).
2. **Voix suivie.** C'est le locuteur qui prononce le plus de mots. En consultation, la personne parle beaucoup plus que le soignant (**choix de conception**). Une intégration peut indiquer la voix à suivre. La part de parole de la personne est affichée.
3. **Tours de parole.** Un tour est une suite de mots de la personne sans mot de l'interlocuteur entre eux.
4. **Contrôle qualité.** Il classe la séance :
   - **`rejected`** si l'une de ces conditions est vraie :
     - aucun mot de la personne ;
     - langue détectée différente de la langue attendue (les codes à 2 lettres de Scribe sont convertis en codes à 3 lettres). Comme la langue attendue est imposée à Scribe, ce cas ne devrait pas se produire : le contrôle reste comme garde-fou.
   - **`partial`** si l'une de ces conditions est vraie :
     - moins de 150 mots lexicaux de la personne (fiche 08) ;
     - moins de 2 minutes de parole de la personne (Q8, **choix de conception** validé le 2026-11-12) ;
     - confiance moyenne des mots de la personne inférieure à 50 %. Ce seuil est **provisoire** : il sera calibré lors des tests de Scribe.
   - **`usable`** sinon.
5. **Ménage.** Une fois la transcription enregistrée, on supprime l'audio et on supprime la transcription chez ElevenLabs (`DELETE`).

**Sortie**

- `SessionTranscript` : les mots de la personne avec leurs horaires, les tours de l'interlocuteur, les événements sonores.
- `QualityReport` : le statut, les raisons, le nombre de mots, le temps de parole, la confiance moyenne, la part de parole.

**Ce que les autres étapes en font**

- Seules les séances `usable` entrent dans la référence personnelle et peuvent changer un niveau d'orientation.
- Une séance `partial` est affichée avec ses marqueurs, mais signalée comme telle.
- Une séance `rejected` est affichée avec ses raisons, sans marqueurs.

## Étape 1 : marqueurs (calcul pur)

Toutes les mesures portent sur les mots de la personne suivie. Chaque marqueur est une fonction pure, testée sur un cas calculé à la main.

Tout ce qui dépend de la langue passe par un **adaptateur de langue**. Le prototype n'a que l'adaptateur anglais, qui fournit :

- l'étiquetage grammatical, avec spaCy et son modèle `en_core_web_sm` ;
- la fréquence des mots, avec le paquet `wordfreq` ;
- la liste des hésitations ;
- la liste des abréviations qui ne terminent pas une phrase.

Les licences de ces composants sont dans [third-party-components.md](../tech/third-party-components.md).

### Découpage

- **Tour de parole** : une suite de mots de la personne sans mot de l'interlocuteur entre eux.
- **Mot** : un élément `type="word"` de Scribe, pris sans sa ponctuation et en minuscules. Les `audio_event` sont exclus. Chaque mot de la personne entre dans une catégorie :
  - **hésitation** : sa forme est dans la liste de l'adaptateur (`um`, `uh`, `er`, `erm`, `hmm`, `mm` et leurs variantes d'orthographe). C'est un **choix de conception**, à ajuster selon ce que Scribe renvoie vraiment ;
  - **mot coupé** : il se termine par un tiret (« w- »). C'est la trace d'un faux départ, si Scribe les écrit bien ainsi : le premier test de Scribe le dira ;
  - **mot lexical** : tous les autres mots qui contiennent au moins une lettre ou un chiffre.
- **Les marqueurs se calculent sur les mots lexicaux.** Les hésitations et les mots coupés ne comptent que dans le `maze_index`. Sans cette règle, une personne qui hésite davantage verrait aussi baisser sa part de noms et la longueur moyenne de ses mots : la fluence contaminerait les marqueurs sémantiques. C'est un **choix de conception**.
- **Énoncé** : une suite de mots terminée par une ponctuation de fin de phrase (`.`, `?`, `!`) ou par la fin du tour.
  - Une abréviation courante (« Mr. », « Dr. ») ne termine pas un énoncé.
  - Un énoncé ne compte que s'il contient au moins un mot lexical.
  - Cela suppose que la ponctuation déduite par Scribe suit les énoncés, ce que les tests de Scribe vérifieront.
- **Temps de parole** : pour chaque tour, la durée du premier au dernier mot, hésitations et mots coupés compris ; on fait la somme des tours.

### Étiquetage grammatical et fréquence

- **Étiquettes** : les catégories universelles (Universal POS tags), les mêmes d'une langue à l'autre. En anglais, `PRON` comprend les possessifs (« my », « his »).
- **Un mot peut porter plusieurs étiquettes.** spaCy découpe certains mots de Scribe en plusieurs morceaux (« I'm » devient « I » et « 'm »). Le mot reçoit alors les étiquettes de tous ses morceaux : « I'm » compte comme pronom.
- **Nom** : un mot étiqueté `NOUN` ou `PROPN`. **Pronom** : un mot étiqueté `PRON`.
- **Mot plein** : un mot étiqueté `NOUN`, `VERB`, `ADJ` ou `ADV`. Les noms propres sont exclus, car leur fréquence dépend de la vie de la personne, pas de son vocabulaire (**choix de conception**).
- **Fréquence** : l'échelle de Zipf de `wordfreq`, qui va d'environ 1 (mot très rare) à 8 (mot très courant). Un mot absent de la liste est exclu de la moyenne.

### Marqueurs de l'indice d'écart

Ils sont orientés dans le sens du déclin décrit par la littérature, et ils ont tous le même poids (fiche 09).

| Id | Définition | Sens avec le déclin | Source |
|---|---|---|---|
| `pronoun_index` | pronoms / (noms + pronoms) | ↑ | définition : 08 ; évolution sur 18 mois : 09 |
| `noun_ratio` | noms / mots lexicaux | ↓ | 09 ; 08 |
| `mean_word_frequency` | fréquence de Zipf moyenne des mots pleins connus de `wordfreq` | ↑ (vocabulaire plus courant) | 09. Le choix de ne compter que les mots pleins est à confirmer à la lecture de 09 |
| `mean_word_length` | nombre moyen de lettres par mot lexical | ↓ | 09 |
| `maze_index` | (hésitations + répétitions immédiates + mots coupés) / nombre d'énoncés | ↑ | 08 (facteur fluence) |
| `speech_rate_wpm` | mots lexicaux / temps de parole, en minutes | ↓ | 08 |

Précisions sur le `maze_index` :

- **Répétition immédiate** : le même mot lexical, ou le même groupe de 2 ou 3 mots, dit deux fois de suite dans un énoncé (« the the », « it was, it was »). On ne tient compte ni des majuscules ni des hésitations entre les deux : « the, um, the dog » compte une répétition. La limite de 3 mots est un **choix de conception**.
- **Limite connue** : une répétition voulue (« very very good ») est comptée aussi.
- **Effet du thème** : un récit centré sur une personne contient plus de pronoms et moins de noms. Sur les données synthétiques, un tel récit a suffi à faire passer une persona stable en `monitor` ([synthetic-data.md](synthetic-data.md), section 3). La référence personnelle doit donc couvrir des thèmes variés.
- **Autre limite connue** : les révisions (« I went, we went ») font partie de l'indice de 08, mais on ne sait pas les détecter par calcul. Elles ne sont pas comptées.

### Marqueurs affichés, hors index

| Id | Définition | Pourquoi hors index | Source |
|---|---|---|---|
| `pauses_between_per100w` | silences ≥ 250 ms entre deux énoncés, pour 100 mots lexicaux | Le sens de l'effet est incertain : il augmente chez 06 par compensation, mais Pistono 2019 ne trouve pas d'excès dans le récit de souvenir | seuil et définition : 06 |
| `pauses_within_per100w` | silences ≥ 250 ms à l'intérieur d'un énoncé, pour 100 mots lexicaux | aucune différence chez 06 | 06 |
| `mattr_50` | MATTR, fenêtre de 50 mots lexicaux, calculé seulement si la personne en a dit au moins 150 | soutien faible (08, 09) | fiches citées par le code : 03, 08 ; méthode : Covington & McFall 2010, *J Quant Linguist* 17(2):94–100, DOI [10.1080/09296171003643098](https://doi.org/10.1080/09296171003643098). Référence vérifiée sur Crossref : la revue n'est indexée ni par PubMed ni par Europe PMC. La fenêtre de 50 vient du cahier des charges initial |

**Calcul d'une pause.**

- C'est le début d'un mot moins la fin du mot précédent, pour deux mots consécutifs de la personne dans le même tour. Les hésitations et les mots coupés comptent comme de la parole.
- Si un événement sonore (rire, toux) se trouve entre les deux mots, l'écart n'est pas un silence : on ne le compte pas.
- La pause est « entre deux énoncés » si le mot qui la précède termine un énoncé ; sinon elle est « dans l'énoncé ».
- On n'utilise pas les éléments `spacing` ([référence technique](../tech/elevenlabs-scribe.md), section 5).

**Sortie** : `SessionMetrics`. Pour chaque marqueur : sa valeur, ou rien si elle n'est pas calculable, et le nombre d'éléments sur lequel elle est calculée. La définition, le sens et les sources de chaque marqueur sont dans un catalogue (`MARKER_SPECS`).

## Étape 2 : analyste du récit (LLM, expérimental)

- **Quand** : seulement pour `task_type = life_story` et une séance `usable` ou `partial`.
- **Modèle** : Mistral ou Claude, selon la configuration, avec une sortie structurée (voir « Appel au modèle » à l'étape 4).
- **Entrée** :
  - les énoncés de la personne, numérotés, hésitations comprises. Les paroles de l'interlocuteur ne sont pas envoyées ;
  - la mémoire des épisodes déjà racontés lors des séances précédentes (identifiants et résumés).
- **Sortie validée** (`NarrativeAnalysis`) :
  - `episodes` : pour chaque épisode, un id, un résumé, la période de vie, les personnes, les lieux, les repères de temps et les numéros des énoncés concernés ;
  - `repetitions` : pour chaque reprise d'anecdote (Cook 2009, [candidates](../discovery/candidates.md)) :
    - l'épisode qui la raconte de nouveau, la séance et l'épisode d'origine ;
    - si elle a lieu dans la même séance ou d'une séance à l'autre ;
    - si la personne la signale elle-même (« I've told you this before »), avec les mots exacts de ce signalement ;
    - la justification et les passages cités.
- **Ce qu'on demande au modèle pour une reprise** (révisé le 2026-11-14, après le premier essai réel) :
  - `retold_from` : une seule référence à l'épisode d'origine, recopiée de la liste fournie. C'est `séance/épisode` pour une séance précédente, ou l'id d'un épisode antérieur de la même séance. Le code en déduit le type de reprise ; le modèle ne le déclare plus ;
  - `relation` : `same_event` si c'est le même événement précis, `related_theme` si les deux épisodes partagent seulement un thème, une personne, un lieu ou une habitude ;
  - `acknowledgement_quote` : les mots exacts par lesquels la personne dit l'avoir déjà raconté, ou rien ;
  - `quoted_passages` : un ou deux passages courts de la séance.
- **Garde-fous.** La réponse du modèle est traitée comme une donnée non fiable. On ne garde que ce qu'on peut vérifier :
  - un épisode doit renvoyer à au moins un énoncé qui existe ; les numéros inventés sont retirés ;
  - **les identifiants d'épisode sont attribués par le code** (`e1`, `e2`, … dans l'ordre du modèle). Les modèles inventent parfois d'autres formes d'identifiant ; les références du modèle sont traduites ;
  - une reprise notée `related_theme` est écartée. Une habitude ou un lieu décrit de nouveau n'est pas le même événement ;
  - la référence d'origine doit désigner un épisode de la mémoire, ou un autre épisode de la séance. Une reprise qui renvoie à elle-même est écartée ;
  - un passage cité doit reprendre les mots de la personne, dans l'ordre. On ne tient pas compte des majuscules, de la ponctuation, ni des hésitations que le modèle aurait omises (« um », mots coupés) : les modèles ont tendance à les retirer. Le numéro d'énoncé recopié en tête d'un passage est retiré. **On garde et on affiche le passage exact de la transcription**, pas le texte du modèle. Une reprise sans aucun passage retrouvé est écartée ;
  - la personne n'est notée comme ayant signalé la reprise que si les mots du signalement se retrouvent dans la transcription. Limite : le code vérifie que ces mots ont été dits, pas qu'ils signalent bien une reprise ;
  - **une seule reprise par épisode** : la première qui passe les contrôles.
- **Si le modèle est indisponible**, l'étape est sautée : la séance garde ses marqueurs et son niveau.
- Le résultat est affiché comme **expérimental** et n'entre **pas** dans l'indice d'écart.
- **Hors v1** : incohérences de dates (H7), part de détails vécus (07).

## Étape 3 : dérive longitudinale (statistique)

### Référence personnelle

- C'est la moyenne et l'écart-type de chaque marqueur sur les premières séances `usable` de la personne, pour le même `task_type`.
- **Elle démarre à 3 séances et peut grandir jusqu'à 5** (choix validé le 2026-11-12) :
  - les séances 4 et 5 sont d'abord testées contre la référence du moment ;
  - si elles sont `stable`, elles la rejoignent ;
  - dès qu'une séance n'est pas `stable`, ou une fois 5 séances atteintes, la référence se fige.

  Plus de séances de référence rendent le test plus sensible : le seuil unilatéral de `t` à α = 0,05 passe de 2,92 (2 ddl) à 2,13 (4 ddl). C'est un **choix de conception non sourcé**.
- Une fois figée, elle ne bouge plus : une référence glissante absorberait le déclin qu'elle doit détecter (H8).
- **Pas de niveau d'orientation avant 3 séances de référence** (règle 5 de CLAUDE.md). L'interface affiche « Building baseline (k/3) ».

### Test de l'écart

**Par marqueur.** On compare la valeur de la séance à la référence avec le **test t modifié pour petits échantillons**, développé en neuropsychologie pour comparer un individu à un petit groupe de comparaison : Crawford & Howell 1998, repris et étendu par Crawford & Garthwaite 2002 (PMID 11931923). Ici, le petit groupe est formé des séances de référence de la personne elle-même, ce qui est une adaptation de la méthode.

```
t = (x_N − moyenne_ref) / (sd_ref × √((n+1)/n))      ddl = n − 1, avec n de 3 à 5
```

- Le `t` est orienté dans le sens du déclin : positif quand le marqueur bouge dans le sens décrit par la littérature.
- Un marqueur est **significatif** quand son `t` atteint le seuil unilatéral à α = 0,05 de la loi de Student : 2,92 avec 3 séances de référence, 2,35 avec 4, 2,13 avec 5.
- Le test est **unilatéral**, dans le sens du déclin : un marqueur qui bouge beaucoup dans l'autre sens n'est pas significatif, et il est décrit comme resté dans la zone habituelle.
- Un marqueur n'est pas testé :
  - s'il manque sa valeur pour la séance, ou pour l'une des séances de référence ;
  - si la référence n'a aucune variation pour lui ;
  - si le sens de son effet est incertain : c'est le cas des deux marqueurs de pauses, jamais testés ;
  - s'il a moins de 2 valeurs de référence : il est alors laissé de côté.
- Le MATTR est testé et peut être signalé hors de la zone, mais il ne compte pas dans la règle : il est hors de l'indice.

**Par séance.** On compte les marqueurs significatifs parmi les marqueurs de l'indice qui ont pu être testés (6 au plus).

- Une séance est **en écart** quand **au moins 2 marqueurs** de l'indice sont significatifs.
- C'est une **chute rapide** quand **au moins 4 marqueurs** de l'indice le sont.

**L'indice d'écart**, affiché « Change from baseline », est la moyenne des z-scores orientés des marqueurs de l'indice testés.

- Chaque z-score est calculé par rapport à la référence, et tous les marqueurs ont le même poids (méthode du score composite de 09).
- Il s'exprime en écarts-types de la variabilité habituelle de la personne : 0 veut dire « comme d'habitude », une valeur positive va vers le déclin.
- **Il sert à l'affichage** (la courbe dans le temps). La décision, elle, se prend sur le nombre de marqueurs significatifs.
- **Sous-scores** : la même moyenne, restreinte à chaque famille. Sémantique : 4 marqueurs. Fluence : 2 marqueurs.
- Le nom « Brain Health Index » est abandonné pour ce score (décision du 2026-11-12) : il laissait croire que plus haut voulait dire en meilleure santé.

**Incertitude affichée** avec chaque score :

- le nombre de séances de référence ;
- l'intervalle de l'indice sur les séances de référence ;
- le statut de qualité de la séance ;
- le contexte.

#### Pourquoi compter les marqueurs plutôt que tester l'indice

La première version de cette spec testait l'indice lui-même contre ses valeurs sur les séances de référence. Une simulation a montré le 2026-11-13 que ce test donne **9 à 14 % de fausses alertes** au lieu des 5 % visés. La cause : l'écart-type de chaque marqueur est estimé sur 3 à 5 séances seulement, ce qui rend l'indice d'une nouvelle séance bien plus variable que celui des séances de référence.

La règle du comptage a été retenue après simulation d'une personne stable, avec des marqueurs suivant une loi normale et plus ou moins corrélés entre eux (script `backend/scripts/simulate_orientation_rules.py`) :

| Séances de référence | Séance en écart | Chute rapide | Revue recommandée | Ancienne règle (test sur l'indice) |
|---|---|---|---|---|
| 3 | 3,3 à 6,6 % | 0,01 à 0,75 % | 0,5 à 2,1 % | 10 à 13 % |
| 4 | 3,2 à 6,8 % | 0,01 à 1,1 % | 0,4 à 2,1 % | 8 à 11 % |
| 5 | 3,3 à 6,9 % | 0,01 à 1,2 % | 0,3 à 2,1 % | 7 à 9 % |

- **Lecture du tableau** : c'est la part des séances d'une personne **stable** qui déclenchent chaque signal, donc le taux de fausses alertes par séance. Le premier chiffre vaut pour des marqueurs indépendants, le second pour des marqueurs fortement corrélés (corrélation de 0,6).
- **Revue recommandée** : deux séances de suite en écart, ou une chute rapide. Les deux séances sont comparées à la même référence, ce qui explique que ce taux dépasse le simple produit des deux probabilités.
- **Détection d'un vrai changement** (corrélation de 0,3) :
  - si tous les marqueurs se décalent de 2 écarts-types vers le déclin, 58 à 74 % des séances sont en écart, et la revue est recommandée dans 44 à 63 % des cas dès la deuxième séance ;
  - pour un décalage de 3 écarts-types, ces parts montent à 85–96 % et à 79–95 %.

  Les valeurs basses correspondent à 3 séances de référence, les hautes à 5.

- Ce sont des **choix de conception**, calibrés par simulation et non tirés d'une étude : les seuils de 2 et de 4 marqueurs. Règle validée par Thibaut le 2026-11-13.
- **Limite** : la simulation suppose des marqueurs de loi normale. Ce n'est qu'une approximation pour l'indice de fluence, qui est un rapport de petits nombres.
- Avec 3 séances de référence, le test reste peu sensible. C'est assumé, et dit au soignant. C'est aussi pour cela que la référence peut grandir jusqu'à 5 séances.

### Niveaux d'orientation

Seules les séances `usable` comptent.

| Niveau | Règle | Action proposée |
|---|---|---|
| `building_baseline` | moins de 3 séances de référence | continuer les séances ; aucune alerte |
| `stable` | séance sans écart : moins de 2 marqueurs significatifs | séance suivante au rythme habituel |
| `monitor` | une séance en écart, isolée | refaire une séance dans les 2 semaines (Q16) |
| `review_recommended` | 2 séances `usable` consécutives en écart, **ou** une chute rapide sur une seule séance | revue par un professionnel qualifié ; une consultation mémoire peut être utile |

- **Choix de conception non sourcés**, validés par Thibaut le 2026-11-12 et à étayer :
  - la persistance sur 2 séances ;
  - la règle de chute rapide ;
  - le délai de 2 semaines ;
  - la règle sur le contexte.
- **Contexte** (5 champs saisis par le soignant : sommeil de la nuit, fatigue, maladie aiguë, nouveau traitement depuis la dernière séance, humeur).
  - Si le contexte est défavorable, une séance en écart déclenche au plus `monitor`, même en cas de chute rapide : elle ne peut pas confirmer une revue.
  - Elle compte tout de même comme un premier signal : si la séance suivante est aussi en écart, avec un contexte normal, la revue est recommandée.
  - Le contexte pondère la fiabilité de la séance ; ce n'est pas un facteur de risque (H9). C'est un **choix de conception** : aucune étude ne l'appuie.
- **Séance `partial`.** Elle est comparée à la référence pour l'affichage, mais elle ne change pas le niveau, ne rejoint pas la référence et n'interrompt pas une suite de séances en écart. Une fois la référence constituée, elle reçoit la règle `carried_over` : le niveau précédent est gardé, et sa synthèse est rédigée sous le titre de ce niveau.
- **Vieillissement normal.** Sur les quelques mois du prototype, on n'en corrige pas l'effet : il est négligeable devant le bruit d'une séance à l'autre ([synthesis.md](../discovery/synthesis.md), section 4).

**Sortie** : `LongitudinalComparisonResult`. Elle contient la référence (séances, moyennes, écarts-types), les `t` par marqueur, l'index, les sous-scores, le niveau, la règle appliquée et l'incertitude.

## Étape 4 : synthèse clinique (LLM contraint)

- **Modèle** : Mistral ou Claude, selon la configuration (voir « Appel au modèle » plus bas).
- **Pas de décision par le LLM.** Le niveau et l'action proposée viennent de l'étape 3. Le LLM rédige ; il ne décide pas.
- **Entrée**, structurée uniquement :
  - le niveau, la règle qui l'a déclenché et l'action proposée ;
  - le nombre de séances de référence, la qualité de la séance et le contexte ;
  - pour chaque marqueur : sa valeur, la zone habituelle de la personne, s'il sort de la zone et, s'il en sort, dans quel sens (plus haut ou plus bas que d'habitude ; pour un marqueur resté dans la zone, le sens n'est pas donné, pour que le texte n'annonce pas un écart que les mesures ne montrent pas), et les fiches d'étude qu'on peut citer pour lui. « Sortir de la zone » veut dire « significatif dans le sens du déclin » (test unilatéral de l'étape 3) ; un marqueur non testé, comme les pauses, est donné comme « not tested » ;
  - quelques passages de la transcription **choisis par calcul** et numérotés : les énoncés qui contiennent le plus d'hésitations et de répétitions (au moins 2), et ceux où les pronoms dépassent le plus les noms (au moins 3 pronoms, et plus de pronoms que de noms), 2 passages au plus pour chaque raison. Ces seuils sont des **choix de conception**. Le modèle rattache un passage à un constat **par son numéro** ; il ne recopie pas de texte, et c'est le code qui place le passage exact (révisé le 2026-11-14 : les modèles recopiaient le passage avec son étiquette).
- **Le profil de risque n'est pas envoyé au modèle** dans la v1 : il reste affiché à côté, sans être mêlé à la synthèse.
- **L'analyse du récit (étape 2) n'est pas envoyée au modèle** non plus (révisé le 2026-11-14). Elle est expérimentale et hors de l'indice : elle reste affichée dans sa propre section, « Experimental, not in the index ». Raison : le modèle l'avait reprise dans les phrases destinées à la personne (« You also repeated a story you had told before »), puis, quand on le lui a interdit, dans des constats sans marqueur, rejetés par le validateur.
- **Qui écrit quoi** (révisé le 2026-11-14, après le premier essai réel). Le modèle n'écrit que ce qui demande une mise en mots ; ce qui est déjà décidé ou chiffré est écrit par le code.

  | Texte | Écrit par |
  |---|---|
  | Titre | le code : un texte fixe par niveau |
  | Constats | le modèle |
  | Phrase sur l'incertitude | le code : nombre de séances de référence, qualité de la séance et contexte, tirés de l'étape 3 |
  | Explication pour la personne : ce qui a été remarqué | le modèle, en une ou deux phrases |
  | Explication pour la personne : la suite | le code : un texte fixe par niveau, ajouté après les phrases du modèle |

  Raison : avec Mistral Small, le modèle a donné un nombre de séances faux, un titre qui contredisait le niveau, et une explication rassurante sans mention de la consultation pour un niveau `review_recommended`.
- **Sortie** (`ClinicalSummaryReport`) :
  - `clinician_summary` : le titre ; des constats, chacun avec son texte, les ids des marqueurs, les passages et les fiches d'étude qui l'appuient ; l'incertitude ; l'action proposée ;
  - `person_explanation` : quelques phrases en langage clair, sans chiffres ni jargon, destinées à la personne ;
  - `prevention_notes` : **vide dans la v1**. Les suggestions de prévention doivent venir d'une liste fixe et sourcée, tirée de la Commission Lancet 2024 (Livingston et al., PMID 39096926). Cette liste n'a pas encore pu être relue dans le rapport : le site du Lancet bloque la lecture automatique. On n'écrit pas de liste de mémoire ;
  - `review` : `draft`, puis `validated` après le clic du soignant (exigence 5 du challenge) ;
  - `generation_mode` et `model_id` : comment le texte a été produit, et par quel modèle.
- **Validateur.** Il rejette un brouillon :
  - qui ne respecte pas le schéma attendu, qui laisse un texte vide, ou qui n'a aucun constat ;
  - qui nomme une affection, même pour l'écarter : « diagnosis », « diagnostic », « Alzheimer's », « dementia », « cognitive impairment », « MCI » (règle 1 de CLAUDE.md). Le contrat `schemas.py` applique la même liste ;
  - dont un constat ne cite aucun marqueur, ou cite un marqueur qui n'a pas été comparé pour cette séance ;
  - dont un constat annonce un écart pour un marqueur resté dans la zone habituelle, ou l'inverse. Chaque constat déclare s'il parle de marqueurs sortis de la zone habituelle (`beyond_usual_range`), et le code compare cette déclaration aux tests de l'étape 3 ;
  - **qui passe sous silence un marqueur de l'indice sorti de la zone habituelle** : chacun doit figurer dans un constat ;
  - dont un constat cite une fiche d'étude qui n'est pas une source des marqueurs sur lesquels il s'appuie ;
  - dont un constat renvoie à un passage qui ne lui a pas été fourni, ou mentionne un numéro de passage dans son texte ;
  - dont les phrases destinées à la personne contiennent un chiffre, ou parlent d'elle à la troisième personne (« the person », « the patient ») au lieu de s'adresser à elle ;
  - dont les phrases destinées à la personne rassurent ou inquiètent : les mots de la famille de « worry » et de « concern » sont refusés. C'est un **choix de conception** : l'outil ne sait pas dire si un écart est grave ou bénin.
- **En cas de rejet**, on fait un seul nouvel essai, en donnant au modèle la liste des problèmes. Si le second brouillon est rejeté, ou si le modèle est indisponible, on écrit un **texte fixe** construit à partir des seules mesures.
- **Pendant la constitution de la référence**, on n'appelle pas le modèle : le texte fixe suffit.

### Appel au modèle (étapes 2 et 4)

Les étapes ne dépendent pas d'un fournisseur : elles passent par un petit contrat commun (`LLMClient`, dans `backend/app/llm/`). Deux fournisseurs sont branchés.

| Fournisseur | Modèle par défaut | Clé | Usage |
|---|---|---|---|
| **Mistral** | `mistral-small-latest` (Mistral Small 4), modifiable par `MISTRAL_MODEL` | `MISTRAL_API_KEY` | essais réels : Thibaut a des crédits Mistral (proposition du 2026-11-13). Modèle retenu le 2026-11-14 : `MISTRAL_MODEL=mistral-medium-latest`, réglé dans `backend/.env` et sur l'hébergeur |
| **Anthropic** | `claude-opus-5-5`, choisi le 2026-11-12 (Q36) | `ANTHROPIC_API_KEY` | prévu au départ ; pas encore de clé |

- **Choix du fournisseur** : la variable `LLM_PROVIDER` (`mistral` ou `anthropic`). Sans elle, on prend le fournisseur dont la clé est présente ; si les deux le sont, Anthropic. Sans aucune clé, il n'y a pas de modèle : l'étape 2 est sautée et l'étape 4 écrit le texte fixe.
- **Modèle retenu (choix de Thibaut, 2026-11-14) : Mistral Medium 3.5, par réglage.** Ce que les essais du 2026-11-14 ont montré, sur les trois modèles de Mistral :

  | Modèle | Statut chez Mistral | Durée d'un appel | Constat |
  |---|---|---|---|
  | Mistral Small 4 (`mistral-small-latest`) | disponible | 3 à 7 s | correct, mais moins régulier : des reprises manquées, et des brouillons de synthèse rejetés puis remplacés par le texte fixe |
  | Mistral Medium 3.5 (`mistral-medium-latest`) | **déprécié depuis le 2026-10-31**, encore servi le 2026-11-14 ; remplaçant annoncé : Mistral Large 4 | 4 à 9 s | le plus juste des trois sur les deux étapes |
  | Mistral Large 4 (`mistral-large-latest`) | disponible depuis le 2026-11-05 | plus de 60 s | raisonne toujours avant de répondre ; trop lent pour une démo en direct, et proche du délai de 90 s |

  Mistral Medium 3.5 est donc réglé par `MISTRAL_MODEL`, en local comme sur l'hébergeur. Le défaut du code reste Mistral Small 4, parce qu'un modèle déprécié peut être retiré sans préavis. **S'il l'est**, aucun plantage : l'étape 2 est sautée et l'étape 4 écrit le texte fixe ; il suffit alors de retirer le réglage pour revenir à Mistral Small 4. Mistral Small 4 avec raisonnement (`high`) a fait moins bien que sans, pour 4 fois la durée. Claude Opus 5.5 n'a pas encore été essayé, faute de clé.
- **Sortie structurée** : le modèle répond dans un schéma JSON, validé par Pydantic, chez les deux fournisseurs.
- **Garde-fous identiques** : les vérifications des étapes 2 et 4 ne dépendent pas du modèle. Un petit modèle qui se trompe davantage produit plus de brouillons rejetés, pas des erreurs affichées.
- **Erreurs** : une panne, un refus ou une réponse tronquée ne cassent jamais le pipeline. L'étape 2 est sautée, l'étape 4 passe au texte fixe.
- **Propre à Anthropic** : niveau d'effort `medium` fixé explicitement ; si le modèle décline une requête, l'API la rejoue sur un modèle de repli dans le même appel (`fallbacks`, en bêta).
- **Propre à Mistral** : température à 0 et `top_p` à 1, envoyés tous les deux. Avec la température à 0 seule, Mistral Large refuse la requête (erreur 400, `top_p` doit valoir 1 ; constaté le 2026-11-14). Même ainsi, les réponses varient d'un essai à l'autre.
- **Raisonnement, propre à Mistral** : la variable `MISTRAL_REASONING_EFFORT` règle l'effort de raisonnement du modèle. Sans elle, on ne l'envoie pas. Les valeurs acceptées dépendent du modèle (constaté le 2026-11-14) : `none` ou `high` pour Mistral Small 4 ; `low`, `medium` ou `high` pour Mistral Large 4, qui raisonne toujours.
- **Limites d'un appel** : délai de 90 s ; réponse limitée à 16 000 jetons chez Claude et 8 000 chez Mistral ; le SDK d'Anthropic refait une fois une requête échouée.
- **Configuration incohérente** : si `LLM_PROVIDER` nomme un fournisseur sans sa clé, ou un fournisseur inconnu, l'API refuse de démarrer, avec un message clair.
- **Le modèle qui a réellement répondu** est enregistré avec chaque texte.
- **Personas de la démo** : leurs textes des étapes 2 et 4 ne sont pas générés à chaque démarrage. Ils ont été produits une fois par Mistral Medium 3.5 le 2026-11-14, puis figés dans `backend/data/synthetic/llm_snapshot/` ([api.md](api.md), section 7).
- **Cache de prompts** : non utilisé. Les consignes sont trop courtes pour être mises en cache.
- **Essai réel** : `backend/scripts/try_llm_steps.py` rejoue les étapes 2 et 4 sur une persona et affiche ce qui a été gardé, écarté ou rejeté. Pour l'étape 2, il compare le résultat à ce que les personas contiennent par construction : les reprises d'anecdote de Margaret (séances 8, 9, 10) et de Rajesh (séance 7). Résultat du 2026-11-14 avec le code corrigé et Mistral Medium 3.5, sur les 3 personas : les 4 reprises attendues sont retrouvées ; 3 autres sont gardées chez Rajesh alors qu'aucune n'était prévue (rappels ou souvenirs voisins) ; les 8 synthèses demandées au modèle passent les contrôles au premier essai. Les réponses varient d'un essai à l'autre : ces chiffres sont un ordre de grandeur. Détail dans [`../log.md`](../log.md).

## Contrats entre étapes (`backend/app/schemas.py`)

Ce sont des modèles Pydantic v2, et les étapes ne s'échangent rien d'autre. Ils remplacent les 4 modèles prévus au départ.

| Modèle | Produit par | Remplace |
|---|---|---|
| `RecordingMetadata` | API | — |
| `SessionTranscript`, `QualityReport` | étape 0 | `AudioTranscriptSegment` |
| `SessionMetrics` | étape 1 | `SessionMetrics` |
| `NarrativeAnalysis` | étape 2 | — |
| `AnalysedSession` | API (entrée de l'étape 3 : métadonnées et sorties des étapes 0 et 1) | — |
| `LongitudinalComparisonResult` | étape 3 | `LongitudinalComparisonResult` |
| `RiskProfile` | données de la personne (affiché à part, hors du pipeline) | — |
| `ClinicalSummaryReport` | étape 4 | `ClinicalSummaryReport` |

Tout objet tiré de données de démonstration porte `synthetic: true` (règle 3).
