---
type: architecture-synthesis
title: Synthèse de la discovery et architecture v0.3
description: Hypothèses H1-H10, matrice des preuves, nouveaux biomarqueurs candidats et proposition d'architecture v0.3 en 5 étapes.
status: draft
tags: [synthesis, biomarkers, hypotheses, architecture-v0.3]
generated:
  by: Synthèse de discovery ChronoVoice
  at: "2026-11-12"
stale_after: "2026-11-16"
---

# Synthèse de la discovery

Ce fichier sert de tableau de bord à la phase de discovery. Il est mis à jour au fil de la lecture, à chaque passage qui change quelque chose. C'est lui qu'on relit pour figer l'architecture.

## 1. Hypothèses d'architecture à valider

Ces hypothèses viennent du cahier des charges initial. Aucune n'est validée pour l'instant : la colonne « Pistes » liste ce que disent déjà les abstracts ou le texte intégral, **à vérifier pendant la lecture**. Une réponse provisoire à chacune est proposée en section 4 (architecture v0.3).

Statuts : 🔲 à tester · ✅ confirmée · ✏️ à modifier · ❌ rejetée

| # | Hypothèse | Ce qu'on doit vérifier | Statut | Pistes (fiche) |
|---|-----------|------------------------|--------|----------------|
| H1 | **3 agents** : extraction → dérive longitudinale → synthèse clinique | Le découpage suit-il des familles de signaux distinctes ? Faut-il séparer l'acoustique (audio) du linguistique (texte) ? Faut-il une étape de contrôle qualité (audio, confiance de la transcription) en amont ? | 🔲 | 02 et 08 trouvent 4 facteurs proches (sémantique, syntaxe, lexique, fluence/acoustique) · 09 : 16 % d'enregistrements inexploitables → contrôle qualité · 07 : un marqueur propre au récit de vie qu'aucun agent ne calcule · 04 : embeddings LLM sans features explicites |
| H2 | **MATTR, fenêtre de 50 tokens**, comme marqueur de richesse lexicale | Sensibilité au type de tâche et à la longueur de l'échantillon ; tokenisation du français (élisions `l'`, `qu'`) ; taille de fenêtre utilisée dans les études | 🔲 | 08 : TTR **brut** non associé au MCI précoce, mais sur ~100 mots et les auteurs suggèrent une version corrigée de la longueur · 09 : diversité lexicale absente des 9 mesures qui évoluent sur 18 mois · 03 : diversité lexicale en baisse |
| H3 | **Densité propositionnelle** (idea density, Nun Study) | La Nun Study mesurait des autobiographies **écrites** au début de l'âge adulte, pas de l'oral tardif : le marqueur se transpose-t-il à l'oral ? Les outils automatiques existent-ils en français ? | 🔲 | 01 : prédictive, mesurée une fois · 10 : baisse aussi chez les sains · 08 : non associée au MCI précoce (à l'oral, sur image) |
| H4 | **Pauses silencieuses intra-phrases > 250 ms**, mesurées avec les timestamps de Whisper | Le seuil de 250 ms est-il celui de la littérature ? Les timestamps de Whisper au niveau du mot sont-ils assez précis, ou faut-il un alignement forcé / une détection d'activité vocale ? Whisper efface les hésitations (« euh ») et les faux départs : perd-on des marqueurs ? | 🔲 | 06 : seuil de 250 ms confirmé, mais l'effet porte sur les pauses **entre énoncés** (pas intra) et serait de la compensation · 08 : le facteur fluence = pauses remplies, faux départs, révisions, répétitions, ce que Whisper efface |
| H5 | **Répétition d'anecdotes** détectée par similarité cosinus d'embeddings | Comment distinguer une répétition liée à un oubli (« je l'ai déjà raconté ») d'une histoire favorite racontée volontiers ? Quelle granularité : phrase, épisode, session ? | 🔲 | aucune étude du corpus · Cook 2009 ([candidates](candidates.md)) : les répétitions surviennent surtout à moins de 2 heures d'intervalle |
| H6 | **Appauvrissement sémantique** : les noms précis sont remplacés par des pronoms ou des mots vides (« truc », « ça ») | Mesures utilisées dans la littérature (ratio pronoms/noms, mots vides, spécificité lexicale) et sens de l'effet | 🔲 | 08 : indice pronominal = pronoms / (noms + pronoms), facteur sémantique en baisse dès le MCI précoce · 09 : pronoms/noms ↑, noms ↓, fréquence des mots ↑ sur 18 mois |
| H7 | **Anachronismes temporels** | Peut-on les détecter sans connaître la biographie réelle ? Une incohérence entre sessions (même événement daté différemment) est-elle un signal plus fiable ? | 🔲 | aucune étude du corpus |
| H8 | **Baseline = sessions 1 à N-1** | Si le déclin a déjà commencé, une baseline glissante absorbe la dérive : faut-il une baseline fixe (premières sessions) ? Combien de sessions minimum ? Quelle variabilité normale d'une session à l'autre ? | 🔲 | 09 : fiabilité test-retest de 0,20 à 0,70 en parole ouverte · 10 : déclin normal le plus rapide vers 75 ans · 08 et 09 : modèle mixte avec intercept par personne · 03 : comparaison à soi-même |
| H9 | **Facteurs contextuels** (sommeil, métabolisme, antécédents) intégrés à la synthèse | Faut-il plutôt s'en servir comme **facteurs confondants** pour corriger ou pondérer une session (mauvaise nuit → session moins fiable), et non comme facteurs de risque ? | 🔲 | aucune étude du corpus |
| H10 | Le récit de vie est **moins biaisé culturellement** que les tests cliniques | Qu'est-ce qui le montre ? Les mesures lexicales dépendent du niveau d'études et de la langue : la baseline intra-individuelle suffit-elle à compenser ? | 🔲 | 06 : équipe et patients français · 07 : souvenirs de vie · Lindsay 2021 ([candidates](candidates.md)) : features sémantiques transférables de l'anglais au français, pas les features paralinguistiques |

## 2. Matrice des preuves

Une ligne par biomarqueur, une colonne par étude. Légende : ✅ soutient · ⚠️ nuancé · ❌ contredit · (vide) non étudié ou pas encore lu. `abs.` = d'après l'abstract · `txt` = d'après le texte intégral. Tout est à confirmer à la lecture.

| Biomarqueur | [01](studies/01-snowdon-1996.md) | [02](studies/02-fraser-2016.md) | [03](studies/03-garrard-2005.md) | [04](studies/04-agbavor-2022.md) | [05](studies/05-de-la-fuente-garcia-2020.md) | [06](studies/06-pistono-2016.md) | [07](studies/07-murphy-2008.md) | [08](studies/08-mueller-2018.md) | [09](studies/09-robin-2023.md) | [10](studies/10-kemper-2001.md) | Verdict provisoire |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Diversité lexicale (MATTR, TTR…) | | | ✅ abs. | | | | | ⚠️ txt (TTR brut, textes courts) | ⚠️ txt (pas parmi les 9) | | |
| Densité propositionnelle / d'idées | ✅ abs. (écrit) | | | | | | | ⚠️ txt (non associée) | | ✅ abs. | |
| Complexité syntaxique | ⚠️ abs. | | ⚠️ abs. | | | | | ⚠️ txt (non associée) | ✅ txt (profondeur ↓) | ✅ abs. | |
| Pauses silencieuses | | | | | | ✅ txt (entre énoncés seulement) | | | ⚠️ txt (pas parmi les 9) | | |
| Hésitations, faux départs, répétitions de mots | | | | | | | | ✅ txt (facteur fluence) | | | |
| Débit, contenu par minute | | | | | | ⚠️ txt (moins de mots, même durée) | | ✅ txt | | | |
| Ratio pronoms / noms, mots vides | | | | | | | | ✅ txt | ✅ txt | | |
| Fréquence et longueur des mots | | | ✅ abs. (« caractéristiques lexicales ») | | | | | | ✅ txt | | |
| Détails épisodiques / sémantiques | | | | | | | ✅ abs. | | | | |
| Répétition d'anecdotes | | | | | | | | | | | |
| Cohérence temporelle | | | | | | | | | | | |
| Embeddings de LLM (sans features explicites) | | | | ✅ txt (80,3 % en test) | | | | | | | |

### Premiers constats (avant lecture)

1. **Toujours aucune étude sur un récit de vie oral en français.** Les plus proches : 07 (souvenirs de 5 périodes de la vie, anglais), 06 (rappel d'un épisode vécu 20 minutes plus tôt, France), 09 (récit de la semaine écoulée, anglais).
2. **Le suivi d'une même personne est maintenant couvert par 4 études** (03, 08, 09, 10). Deux mises en garde pour la baseline (H8) : la parole ouverte varie beaucoup d'une session à l'autre (09), et le déclin **normal** est le plus rapide vers 75 ans (10). Sans en tenir compte, ChronoVoice prendrait le vieillissement normal et le bruit pour des signaux.
3. **Au stade précoce, ce qui bouge le plus, c'est le contenu sémantique** (pronoms à la place des noms, vocabulaire plus courant) **et la fluence** (08, 09). La diversité lexicale et les pauses intra-phrases, piliers de l'Agent 1, ont pour l'instant un soutien plus faible (06, 08, 09) : à défendre pendant la lecture.
4. **Deux pistes d'architecture se dessinent** (H1) : un contrôle qualité audio en amont (09 : 16 % d'enregistrements inexploitables), et un marqueur propre au récit de vie, la part de détails vécus (07), qu'aucun agent prévu ne calcule.
5. **La transcription doit être verbatim.** Les hésitations, faux départs et répétitions (08) et l'emplacement des pauses (06) portent du signal. Whisper, par défaut, nettoie tout ça.

## 3. Nouveaux candidats

Biomarqueurs, méthodes ou garde-fous rencontrés dans les études et absents du cahier des charges initial.

| Candidat | Source | Intérêt | Coût d'implémentation |
|----------|--------|---------|-----------------------|
| Part de détails épisodiques et sémantiques dans un souvenir | 07 ; outil : van Genugten 2024 ([candidates](candidates.md)) | propre au récit de vie, ne dépend pas de la longueur du récit | élevé : l'outil existant est en anglais, il faudrait un modèle français |
| Indice pronominal : pronoms / (noms + pronoms) | 08, 09 | simple, explicable, confirmé sur 18 mois | faible (étiquetage grammatical) |
| Fréquence moyenne des mots | 09 | capte le passage à un vocabulaire plus courant | faible (base de fréquences du français) |
| Contenu par minute (mots, unités sémantiques) | 08, 06 | mesure l'efficacité du discours, sensible au MCI précoce | faible pour les mots ; plus élevé pour les unités sémantiques |
| Contrôle qualité audio et transcription en amont | 09 | évite d'interpréter un mauvais enregistrement comme un déclin | faible à modéré |
| Score composite : z-scores signés, poids égaux | 09 | précédent direct pour le Brain Health Index, entièrement explicable | faible |
| Embeddings de LLM sur la transcription, en complément des features explicites | 04 | meilleure performance brute que les features acoustiques | modéré, mais **boîte noire**, et les transcriptions ne peuvent pas partir chez une API externe (données de santé : RGPD, hébergement HDS) → modèle local requis. *Contrainte levée le 2026-11-12 pour le prototype, qui ne traite que des données synthétiques : les enregistrements et transcriptions partent chez ElevenLabs et Mistral par API (section 4). Elle reviendra en déploiement.* |
| Les 4 facteurs (sémantique, syntaxe, lexique, fluence/acoustique) comme structure des indicateurs | 02, 08 | découpage retrouvé dans deux cohortes, lisible pour un clinicien | faible (organisation, pas de calcul nouveau) |

## 4. Architecture proposée v0.3 (hypothèse de travail)

> La v0.2 a été proposée le 2026-11-12. Elle est devenue v0.3 le même jour, après lecture du cadre du challenge ([challenge.md](../challenge.md)) et les décisions de Thibaut. **Non validée** : elle s'appuie sur les abstracts et les textes intégraux des fiches, pas encore sur la lecture des études. Elle remplace, à titre provisoire, le schéma à 3 agents du cahier des charges (H1).

> **Mise à jour du 2026-11-15 : cette section est antérieure au code.** La v0.3 a été précisée par les specs v1, puis codée du 13 au 15 novembre. **Pour décrire ce que fait le prototype, la référence est [pipeline.md](../specs/pipeline.md)** ; cette section garde la justification scientifique de chaque choix. Ce qui a changé en codant :
>
> - **Étape 0.** Le contrôle qualité porte sur trois critères : au moins 150 mots, au moins 120 s de parole de la personne suivie, et une confiance moyenne d'au moins 50 % (provisoire). La part de parole de la personne est affichée, pas contrôlée, et il n'y a pas de mesure de qualité audio à part. La voix suivie est celle qu'indique l'application d'origine, sinon celle qui dit le plus de mots.
> - **Pauses.** Elles ne sont mesurées qu'à l'intérieur d'un tour de parole : un silence au changement de locuteur ne compte pas. Elles sont affichées, mais hors de l'indice, car le sens de leur effet est incertain.
> - **Étape 1.** Six marqueurs forment l'indice : indice pronominal, part des noms, fréquence et longueur moyennes des mots, indice de labyrinthe, mots par minute. Le MATTR (fenêtre de 50) n'est calculé qu'à partir de 150 mots, et il est affiché hors de l'indice. L'indice de labyrinthe compte les hésitations, les mots coupés et les répétitions, pas les révisions. **La profondeur syntaxique n'est pas mesurée**, et le contenu par minute se réduit aux mots par minute.
> - **Étape 2.** Elle découpe le récit en épisodes et repère les anecdotes reprises d'une séance à l'autre. La part de détails vécus et la cohérence des dates ne sont pas faites. **Ses résultats n'entrent ni dans l'étape 3 ni dans l'étape 4** : ils sont seulement affichés, comme expérimentaux.
> - **Étape 3.** La référence personnelle démarre à 3 séances et grandit jusqu'à 5 tant que les séances restent stables, puis se fige. Le modèle du bruit n'utilise pas les fiabilités publiées ni l'indice de changement fiable de Jacobson & Truax : chaque marqueur est testé contre la référence de la personne (test de Crawford-Howell, unilatéral dans le sens du déclin). Une séance est « en écart » à partir de 2 marqueurs significatifs, « chute rapide » à partir de 4 (décision du 2026-11-13, section 5). Le « Brain Health Index » s'appelle « Change from baseline » ; il est affiché, mais ne décide plus du niveau.
> - **Étape 4.** Elle reçoit les étapes 0, 1 et 3, mais pas l'étape 2. Chaque constat doit citer au moins un marqueur ; les passages et les études sont facultatifs. Le titre, la phrase sur l'incertitude et la suite proposée à la personne sont écrits par le code, pas par le LLM.
> - **Points de la section 4.4 tranchés** : la voix suivie (ci-dessus), le LLM (Mistral ou Claude par API, Mistral Medium pour la démo), la longueur minimale du MATTR (150 mots) et le rythme des séances du jeu synthétique ([synthetic-data.md](../specs/synthetic-data.md)).

**Ce qui change dans la v0.3** (décisions du 2026-11-12) :

- **Module branchable.** ChronoVoice s'accroche à n'importe quelle action qui produit un enregistrement de parole. Premier cas d'intégration : MyMémoires.
- **Multilingue par conception, prototype en anglais.** La démo vise une population anglophone. Tout ce qui dépend de la langue passe par un adaptateur.
- **Transcription par ElevenLabs Scribe v3**, qui remplace Mistral Voxtral (Voxtral n'horodate pas chaque mot). Scribe transcrit mot pour mot, horodate chaque mot et sépare les voix. Référence technique : [elevenlabs-scribe.md](../tech/elevenlabs-scribe.md).
- **Pas de contrainte RGPD sur les choix techniques.** Les LLM peuvent être appelés par API. Le prototype ne traite que des données synthétiques.

**Principe.** Tout ce qui est une mesure doit donner le même résultat à chaque passage, se tester sur des cas calculés à la main et s'expliquer à un clinicien : c'est du calcul classique, pas un agent. Le LLM ne sert qu'à deux endroits : comprendre le récit (étape 2) et rédiger la synthèse (étape 4).

```
 Tout enregistrement de parole (MyMémoires, téléconsultation, appel…)
   + métadonnées : personne, type de tâche, langue, consentement
        │
 [0] Capture et qualité ....... Scribe + calcul  ── séance rejetée si inexploitable
        │  transcription verbatim horodatée par mot, voix de la personne seule
        ├───────────────────────────────┐
 [1] Extracteur de marqueurs ... calcul   [2] Analyste du récit ............... LLM
     4 familles, adaptateur de langue        épisodes, détails vécus, répétitions,
                                             cohérence des dates entre séances
        └───────────────┬───────────────┘
 [3] Moteur de dérive .............. statistique  ◄── contexte = fiabilité de la séance
        │  écart à la référence personnelle, bruit, Brain Health Index
 [4] Synthèse clinique ............. LLM contraint
        │  rapport non diagnostique, chaque phrase reliée à une mesure et un passage
 Dashboard clinicien
```

### 4.1 Les cinq étapes

**[0] Capture et qualité (nouvelle) · Scribe + calcul**

- **Point d'entrée unique du module.** Il reçoit un enregistrement venu de n'importe quelle application, avec ses métadonnées : identifiant de la personne, type de tâche, langue, consentement.
- **Transcription par ElevenLabs Scribe v3**. Réglages et format de réponse détaillés dans [elevenlabs-scribe.md](../tech/elevenlabs-scribe.md).
  - 90+ langues, dont l'anglais, l'arabe et le hindi ; la langue est détectée ou fixée.
  - Transcription mot pour mot par défaut : les « um », « uh » et faux départs sont conservés. Ils forment l'indice de fluence (08). Leur forme exacte dans le texte reste **à relever sur un échantillon**.
  - Horodatage de chaque mot et séparation des voix. Reste à désigner quelle voix est celle de la personne suivie.
- **Pauses.** Une pause est l'écart entre la fin d'un mot et le début du mot suivant, chez la même personne. On compte celles ≥ 250 ms (06).
  - Elle compte comme pause **entre énoncés** si le mot précédent porte une ponctuation de fin de phrase ou s'il y a changement de locuteur ; sinon, comme pause **dans l'énoncé**.
  - Cela suppose que la ponctuation déduite par Scribe suit les énoncés, ce qui reste à vérifier.
- **Contrôle qualité.** Durée de parole, nombre de mots (au moins 150, minimum cité par 08), qualité audio, part de parole de la personne suivie, et confiance de la transcription (`logprob` de chaque mot).
- Sortie : séance **utilisable**, **partielle** ou **rejetée**. Une séance rejetée n'entre jamais dans la référence personnelle.
- Appui : 09 (16 % d'enregistrements inexploitables), 08, 06.

**[1] Extracteur de marqueurs (ancien Agent 1, recentré) · calcul pur**

Organisé selon les 4 familles retrouvées chez 02 et 08.

Chaque mesure qui dépend de la langue (découpage en mots, étiquetage grammatical, liste des pronoms, fréquence des mots) passe par un **adaptateur de langue**. Le prototype n'en a qu'un : l'anglais. Les mesures sémantiques sont celles qui se transposent le mieux d'une langue à l'autre (Lindsay 2021, [candidates](candidates.md)).

| Famille | Mesures | Priorité | Appui |
|---|---|---|---|
| Sémantique | indice pronominal = pronoms / (noms + pronoms) ; part des noms ; fréquence et longueur moyennes des mots | 1 | 08, 09 |
| Fluence et temps | « maze index » (pauses remplies, faux départs, révisions, répétitions, par énoncé), à partir des hésitations conservées par Scribe ; pauses ≥ 250 ms **entre** et **dans** les énoncés, comptées séparément ; mots et contenu par minute | 1 | 08, 06 |
| Lexique | MATTR (fenêtre de 50), seulement au-delà d'une longueur minimale à fixer | 2 | 03 ; soutien faible en 08 et 09 |
| Syntaxe | profondeur syntaxique moyenne | 2 | 09 |

Retiré, reporté ou à interpréter avec prudence :

- **MFCC (descripteurs acoustiques bruts) : retirés.** Inexplicables pour un clinicien, et les features paralinguistiques ne se recoupent pas entre l'anglais et le français (Lindsay 2021, [candidates](candidates.md)).
- **Densité propositionnelle : reportée.** Marqueur de risque mesuré une seule fois (01), pas d'outil français identifié, non associée au MCI précoce (08).
- **Pauses : sens de l'effet incertain.** Chez 06, les pauses entre énoncés augmentent mais sont corrélées positivement à la mémoire épisodique (compensation). Chez Pistono 2019 ([candidates](candidates.md)), pas d'excès de pauses dans le récit de souvenir.

**[2] Analyste du récit (nouveau) · LLM**

Ce que le récit de vie permet et qu'une description d'image ne permet pas. L'étape ne tourne que sur les enregistrements narratifs (récit de vie, souvenirs) ; pour les autres types de tâche, on la saute.

- Découpe le récit en épisodes (quoi, quand, qui, où, période de vie) et tient une **mémoire des anecdotes** de la personne, d'une séance à l'autre.
- **Part de détails vécus (épisodiques) et de généralités (sémantiques)** (07). L'outil automatique existant est en anglais seulement (van Genugten 2024, [candidates](candidates.md)).
- **Répétitions** dans une même séance (Cook 2009, [candidates](candidates.md) : la plupart surviennent à moins de 2 heures d'intervalle) et d'une séance à l'autre, en notant si la personne le signale elle-même (« je vous l'ai déjà raconté »). L'appariement se fait au niveau de l'épisode, pas de la phrase (H5).
- **Incohérences de dates entre séances** (reformulation de H7). Aucune étude ne l'appuie : mode expérimental, hors index.
- Chaque résultat pointe vers les passages de la transcription, ce qui alimente le comparateur de séances du dashboard.
- **Modèle** : appelé par API, sans contrainte d'hébergement pour le prototype, qui ne traite que des données synthétiques. Le modèle reste à choisir.

**[3] Moteur de dérive (ancien Agent 2, refondu) · statistique**

- **Référence personnelle fixe** : les 3 premières séances valides (règle produit de CLAUDE.md : pas d'alerte sous 3 séances de baseline). Pas de baseline glissante 1..N-1, qui absorberait le déclin qu'elle doit détecter (H8).
- **Une référence par type de tâche.** Les mesures changent selon la tâche : chez les mêmes patients, les pauses sont en excès dans la description d'image mais pas dans le récit de souvenir (Pistono 2019, [candidates](candidates.md)). Une séance n'est donc comparée qu'à la référence du même type de tâche. C'est la condition pour brancher le module sur des enregistrements de nature différente.
- **Modèle du bruit** : en parole libre, la fiabilité test-retest va de 0,20 à 0,70 selon la mesure (09). Un écart ne compte que s'il dépasse ce bruit, au sens de l'indice de changement fiable (Jacobson & Truax 1991, *J Consult Clin Psychol* 59(1):12–19, DOI [10.1037//0022-006x.59.1.12](https://doi.org/10.1037//0022-006x.59.1.12) · PMID 2002127), **et** s'il se maintient sur 2 séances consécutives (proposition sans source, à étayer). Tant que la personne n'a pas assez de séances pour estimer son propre bruit, on part des fiabilités publiées (09).
- **Contexte** (sommeil, fatigue, maladie, nouveau traitement) : pondère la fiabilité de la séance, ce n'est pas un facteur de risque (H9, aucune étude).
- **Brain Health Index** : méthode de 09 (z-scores signés, poids égaux), calculés ici par rapport à la référence personnelle. Un index global et un sous-score par famille. Référence exacte des z-scores chez 09 : à confirmer.
- **Vieillissement normal** : déclin le plus rapide vers 75 ans (10), mais de l'ordre de −0,03 proposition pour 10 mots par an chez les non-démentes (Kemper et al. 2001, Nun Study, [candidates](candidates.md)). À modéliser sur plusieurs années ; négligeable sur 6 mois au regard du bruit.

**[4] Synthèse clinique (ancien Agent 3) · LLM contraint**

- Reçoit seulement les sorties structurées des étapes 0 à 3 et les passages cités, jamais l'audio.
- Chaque phrase du rapport est reliée à une mesure, un passage et une fiche d'étude.
- Un validateur rejette le vocabulaire diagnostique (règle 1 de CLAUDE.md).
- Les antécédents sont affichés comme contexte, jamais mélangés au score.

### 4.2 Ce qui n'est pas retenu

- **Un classifieur malade / témoin à la manière de 04.** Il donne une bonne performance (80,3 % en test), mais c'est une boîte noire, il compare la personne à une population (ce qui glisse vers le diagnostic) et il n'a jamais été validé en français. ChronoVoice ne classe pas les gens : il mesure l'écart de chacun à lui-même.

### 4.3 Réponse provisoire de v0.3 à chaque hypothèse

Les statuts de la section 1 restent 🔲 : c'est la lecture qui les fera passer à ✅, ✏️ ou ❌.

| # | Hypothèse initiale | Proposition v0.3 |
|---|---|---|
| H1 | 3 agents | module branchable sur tout enregistrement ; 5 étapes, dont 2 LLM (2 et 4) ; l'extraction et la dérive deviennent du calcul |
| H2 | MATTR, fenêtre de 50 | gardé en priorité 2, seulement au-delà d'une longueur minimale |
| H3 | Densité propositionnelle | reportée |
| H4 | Pauses intra-phrases > 250 ms via Whisper | seuil de 250 ms gardé ; pauses entre et dans les énoncés comptées séparément, à partir des horodatages par mot de Scribe ; hésitations conservées par Scribe |
| H5 | Répétitions par similarité cosinus | mémoire des anecdotes (étape 2), au niveau de l'épisode, dans et entre les séances |
| H6 | Appauvrissement sémantique | priorité 1 de l'étape 1 |
| H7 | Anachronismes | incohérences de dates entre séances, expérimental, hors index |
| H8 | Baseline = sessions 1 à N-1 | référence fixe (3 premières séances valides) par type de tâche, modèle du bruit, persistance sur 2 séances |
| H9 | Contexte intégré à la synthèse | pondère la fiabilité de la séance ; antécédents en contexte seulement |
| H10 | Moins de biais culturel | comparaison à soi-même ; marqueurs sémantiques plutôt que paralinguistiques ; adaptateurs de langue (prototype en anglais) |

### 4.4 Ce que la lecture doit trancher

- **07 (Murphy)** : la cotation des détails vécus peut-elle être automatisée de façon fiable en français ? Sinon, l'étape 2 se réduit aux répétitions et peut fusionner avec l'étape 1.
- **09 (Robin)** : comment les z-scores sont calculés ; la diversité lexicale et les pauses ont-elles été testées puis écartées, ou jamais testées ?
- **Rythme des séances** : avec ce bruit, 6 séances mensuelles (scénario de Jeanne) risquent de ne pas suffire. Des séances d'au moins 5 minutes (Petti 2023, [candidates](candidates.md)), plus fréquentes, donneraient un meilleur signal. **À trancher avant d'écrire le mock.**
- **Seuils sans source**, à étayer ou à retirer : longueur minimale pour MATTR, persistance sur 2 séances.
- **Scribe, à tester sur 2 ou 3 enregistrements en anglais** (liste dans [elevenlabs-scribe.md](../tech/elevenlabs-scribe.md), section 9) :
  - forme des hésitations et des faux départs ;
  - précision des pauses par rapport à un repérage manuel ;
  - ponctuation et énoncés ;
  - diarisation à deux voix ;
  - stabilité d'une transcription à l'autre.
- **Voix suivie** : comment désigner la personne suivie parmi les locuteurs.
- **LLM des étapes 2 et 4** : modèle à choisir.

## 5. Journal des décisions

| Date | Décision | Justification (fiche · passage) |
|------|----------|---------------------------------|
| 2026-11-12 | Corpus élargi de 5 à 10 études (06 à 10) | Le corpus de départ ne couvrait ni le récit autobiographique, ni le suivi longitudinal, ni le stade MCI |
| 2026-11-12 | Architecture v0.2 (5 étapes, dont 2 LLM) enregistrée comme **hypothèse de travail**, non validée (section 4) | Abstracts et textes intégraux, avant lecture : 09 (bruit test-retest, 16 % d'enregistrements inexploitables, score composite), 08 (4 facteurs, fluence qui exige une transcription verbatim), 06 (pauses entre énoncés), 07 (détails vécus) |
| 2026-11-12 | Décisions de Thibaut : prototype **en anglais**, conception **multilingue** ; module **branchable** sur toute action qui produit un enregistrement (premier cas : MyMémoires) ; **pas de contrainte RGPD** sur les choix techniques ; transcription par **Mistral Voxtral**. Architecture révisée en **v0.3** (section 4) | Cadre du challenge ([challenge.md](../challenge.md)) : organisateur indien, aucune donnée fournie. Doc Mistral : Voxtral Transcribe 3 couvre 50 langues mais horodate par segment seulement → pauses par VAD |
| 2026-11-12 | Transcription : **ElevenLabs Scribe v3** remplace Mistral Voxtral. Les pauses se calculent sur les horodatages par mot ; le détecteur de voix (VAD) est abandonné | Comparaison de 8 outils (Voxtral, Scribe, AssemblyAI, Deepgram, OpenAI, WhisperX, CrisperWhisper, Gradium) dans leur doc officielle. Scribe est le seul à documenter, dans un même appel, la transcription verbatim par défaut, l'horodatage par mot et la séparation des voix. Prix équivalent (0,20 $/h). Référence : [elevenlabs-scribe.md](../tech/elevenlabs-scribe.md) |
| 2026-11-12 | **Specs v1 du prototype** ([pipeline.md](../specs/pipeline.md)). Elles précisent la v0.3 sur quatre points. **(1)** Le test de l'écart passe de l'indice de changement fiable au test t modifié pour petits échantillons. **(2)** Le Brain Health Index compte 6 marqueurs (`pronoun_index`, `noun_ratio`, `mean_word_frequency`, `mean_word_length`, `maze_index`, `speech_rate_wpm`), à poids égaux ; les pauses et le MATTR sont affichés hors index. **(3)** La référence est fixée aux 3 premières séances utilisables, une par type de tâche. **(4)** H7 (dates) et la part de détails vécus (07) sortent de la v1 | **(1)** La référence est un petit échantillon de séances de la même personne : le test de Crawford & Howell, étendu par Crawford & Garthwaite 2002 (PMID 11931923), est fait pour comparer un individu à un petit échantillon ; l'indice de changement fiable demande une fiabilité de population qu'on n'a pas pour nos marqueurs. **(2)** Le sens de l'effet des pauses est incertain (06 contre Pistono 2019), et le MATTR a un soutien faible (08, 09). Les autres choix sont des décisions de conception signalées dans la spec |
| 2026-11-12 | **Arbitrages des specs** ([questions.md](../specs/questions.md), Q29 à Q43). La référence personnelle démarre à 3 séances et grandit jusqu'à 5 tant que les séances sont stables, puis se fige : cela précise H8. Le score composite est renommé « Change from baseline » | Avec 3 séances, le seuil du test est élevé (t = 2,92 à 2 ddl) ; avec 5, il descend à 2,13. On ne fige la référence qu'après des séances jugées stables, pour limiter le risque d'absorber un déclin. Le nom « Brain Health Index » laissait croire que plus haut voulait dire en meilleure santé. Décisions de conception, non sourcées |
| 2026-11-12 | **Discovery close.** Les hypothèses H1 à H10 sont tranchées à titre provisoire par la v0.3 et les specs v1 ([specs](../specs/index.md)). Leurs statuts restent 🔲 tant que les études ne sont pas lues ; la lecture continue sur 07 et 09 | Remise du prototype le 2026-11-20 ([challenge.md](../challenge.md)). Un passage d'étude qui contredit une spec sera noté ici, puis répercuté dans la spec avant le code |
| 2026-11-13 | **Règle de décision de l'étape 3 corrigée** ([pipeline.md](../specs/pipeline.md)). Une séance est « en écart » quand au moins 2 des 6 marqueurs de l'indice sont significatifs (test de Crawford & Garthwaite par marqueur) ; c'est une « chute rapide » à partir de 4. L'indice d'écart reste affiché, mais il ne sert plus à décider | Une simulation a montré que le test prévu sur l'indice donnait 9 à 14 % de fausses alertes au lieu de 5 % : l'écart-type de chaque marqueur est estimé sur 3 à 5 séances seulement. Avec la règle du comptage, une personne stable est « en écart » dans 3 à 7 % des séances, et la revue est recommandée à tort dans 0,3 à 2,1 % des séances. Seuils de 2 et de 4 : choix de conception calibrés par simulation (`backend/scripts/simulate_orientation_rules.py`) |
