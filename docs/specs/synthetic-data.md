---
type: spec
title: Données synthétiques de démonstration — spec v1
description: Personas anglophones du prototype, rythme des séances, méthode de génération (récits écrits par LLM convertis au format Scribe), profils de risque synthétiques et règles de marquage.
status: draft
tags: [specs, synthetic-data, personas, mock, demo]
generated: "2026-11-12"
---

# Données synthétiques de démonstration : spec v1

> Spec v1 du 2026-11-12, issue des questions Q3 à Q5 du [questionnaire](questions.md). Elle remplace le mock initial (« Jeanne, 78 ans, 6 séances sur 6 mois »). Les organisateurs ne fournissent aucune donnée ([challenge.md](../challenge.md), section 5).
>
> **Tout ici est synthétique** : `synthetic: true` dans chaque fichier, et un badge dans l'interface (règle 3 de CLAUDE.md). Les ampleurs de dérive sont des **paramètres de démonstration**. Ce ne sont pas des résultats scientifiques.

## 1. Personas (Q3)

Trois personnes fictives, anglophones, de 70 à 80 ans. Elles vivent à Abu Dhabi, pour coller à la population cible du challenge.

| Persona | Âge | Profil | Trajectoire obtenue dans le pipeline |
|---|---|---|---|
| **Margaret Hale** | 78 | infirmière à la retraite, britannique | **Déclin progressif à partir de la 6e séance.** `stable` jusqu'à la 6e, `monitor` à la 7e, `review_recommended` de la 8e à la 10e. Elle raconte de nouveau la même anecdote aux séances 8, 9 et 10, sans s'en rendre compte |
| **Rajesh Menon** | 74 | ingénieur à la retraite, indien, anglophone | **Stable** sur les 10 séances. À la 7e, il revient sur une anecdote en disant lui-même qu'il l'a déjà racontée |
| **Grace Santos** | 72 | enseignante à la retraite, philippine, anglophone | **Stable.** Sa 7e séance est écourtée après une mauvaise nuit : elle est `partial` (trop courte, confiance de transcription faible), avec un contexte défavorable, et elle ne change pas le niveau |

- Les noms sont inventés et ne visent aucune personne réelle. Profils validés le 2026-11-12.
- Le déclin de Margaret commence à la 6e séance, et non à la 5e comme prévu au départ : sa référence personnelle compte ainsi 5 séances sans déclin.

## 2. Rythme (Q4)

- 10 séances par persona, une toutes les 2 semaines, du 2026-06-29 au 2026-11-02.
- Environ 600 mots et 4 à 5 minutes de parole par séance. Les échantillons de 5 minutes suivent mieux l'évolution que ceux d'1 minute (Petti 2023, [candidates](../discovery/candidates.md)).
- Un thème de vie différent à chaque séance, tiré de la banque de 12 questions `backend/data/prompts.json`, que l'interface utilisera aussi.

## 3. Méthode de génération (Q5)

On génère une fois, avec une graine fixe, et on commite les fichiers JSON. Aucun LLM n'est appelé pendant la démo.

1. **Les récits sont écrits par un LLM**, phrase par phrase, dans `stories/<persona>.json`.
   - Écrits le 2026-11-13 par Claude Sonnet 5.5, un assistant par persona, à partir d'une biographie fictive.
   - Chaque récit compte 40 à 44 phrases et 560 à 640 mots. Il ne contient ni chiffres, ni abréviations, ni hésitations : celles-ci sont ajoutées à l'étape 3.
   - **Margaret** : ses récits 5 à 10 existent aussi en version « vague », phrase pour phrase. Les noms précis y sont remplacés par des pronoms ou des mots vagues, et les mots rares par des mots courants. Elle a aussi 3 reprises de la même anecdote, formulées différemment.
   - **Limite** : un contrôle automatique a vérifié le format de chaque phrase, mais aucun humain n'a relu les 30 récits en entier.
2. **Les paramètres** sont dans `generation_params.json`.
   - Pour chaque persona : le débit, le taux d'hésitations, le taux de répétitions, la fréquence des pauses, la confiance de transcription, et leur variation normale d'une séance à l'autre.
   - Pour certaines séances : un décalage voulu (tableau ci-dessous pour Margaret).
3. **Le script** `backend/scripts/generate_synthetic_data.py` assemble chaque séance, de façon déterministe :
   - il prend chaque phrase dans sa version normale ou vague, selon la part de phrases vagues de la séance ;
   - il insère les hésitations (« um », « uh »), les répétitions (« the, the ») et les mots coupés (« w- ») ;
   - il ajoute la question de l'interlocuteur et deux relances ;
   - il donne à chaque mot un début, une fin et une confiance. La durée des mots est ajustée pour atteindre exactement le débit visé ;
   - il écrit le tout au format de réponse de Scribe.
4. **Passage dans le vrai pipeline**, à partir du contrôle qualité de l'étape 0 : on saute seulement l'appel à Scribe. Les marqueurs affichés sont donc **mesurés** par le code, pas recopiés des cibles.
5. **Vérification** : `backend/tests/test_synthetic_data.py` vérifie que chaque persona suit exactement la trajectoire du tableau de la section 1, et que les fichiers commités sont bien ceux que le script produit. Le rapport `backend/scripts/report_synthetic_trajectories.py` affiche les mesures séance par séance.

### Le déclin de Margaret

| Séance | Phrases vagues | Débit | Hésitations pour 100 mots | Répétitions pour 100 mots | Reprise de l'anecdote |
|---|---|---|---|---|---|
| 1 à 5 | 0 % | 138 mots/min | 2,0 | 0,5 | non |
| 6 | 15 % | −2 | +0,5 | +0,2 | non |
| 7 | 30 % | −5 | +1,6 | +0,7 | non |
| 8 | 50 % | −8 | +1,8 | +0,9 | oui |
| 9 | 70 % | −11 | +2,6 | +1,3 | oui |
| 10 | 85 % | −14 | +3,5 | +1,8 | oui |

- Ce sont des **paramètres de démonstration**. En 10 semaines, Margaret perd 14 mots par minute ; chez les personnes au stade MCI très précoce de la fiche 08, le débit passe de 143 à 133 mots par minute en deux ans.
- La 7e séance a été réglée pour que deux marqueurs seulement sortent de la zone habituelle. Sans ce réglage, Margaret passait directement de `stable` à `review_recommended`.

### Ce que les réglages ont montré : l'effet du thème

Le thème du récit pèse sur les marqueurs sémantiques. Un récit centré sur une personne contient plus de pronoms et moins de noms.

- Chez Rajesh, le récit sur son mentor, placé en 9e séance, déclenchait à lui seul un niveau `monitor` : part de pronoms de 0,50 contre 0,33 à 0,44 d'habitude.
- On a déplacé ce récit en 3e séance, pour qu'il entre dans sa référence personnelle (`story_order` dans les paramètres). Rajesh reste alors stable.
- **C'est une limite réelle du produit**, pas seulement des données : la référence doit couvrir des thèmes variés, ou la comparaison doit tenir compte du thème.

## 4. Profils de risque synthétiques (Q22)

Chaque persona a un profil en lecture seule, marqué « shared with consent » :

- antécédents ;
- tension artérielle ;
- diabète ;
- cholestérol ;
- sommeil ;
- activité physique ;
- audition et vision ;
- humeur ;
- isolement social ;
- tabac et alcool ;
- antécédents familiaux ;
- une ligne « Genomic data: not shared » (décision du 2026-11-12).

Les 13 rubriques de `personas.json` sont des champs de profil courants. Elles ne reprennent pas encore la liste des facteurs modifiables de la Commission Lancet 2024 (Livingston et al., PMID 39096926) : cette liste sera tirée du rapport avant d'écrire les recommandations de prévention de l'étape 4.

## 5. Fichiers

```
backend/data/
  prompts.json                        # banque de 12 questions et 2 relances, partagée avec l'interface
  synthetic/
    personas.json                     # identité, résumé, profil de risque
    stories/<persona>.json            # récits écrits par LLM, phrase par phrase
    generation_params.json            # graine, niveaux de base, décalages par séance
    sessions/<persona>/<NN>.json      # séance générée : métadonnées, paramètres, réponse au format Scribe
    llm_snapshot/<persona>.json       # textes des étapes 2 et 4, générés une fois par le modèle retenu
```

- Le code qui lit ces fichiers est dans `backend/app/demo_data.py`.
- Les scripts sont dans `backend/scripts/` et ne sont pas importés par l'application :

```bash
uv run python -m scripts.generate_synthetic_data          # régénère les 30 séances
uv run python -m scripts.report_synthetic_trajectories    # affiche les mesures et les niveaux
uv run --env-file .env python -m scripts.build_demo_snapshot  # régénère les textes figés des étapes 2 et 4
```

- **Textes figés** (`llm_snapshot/`, ajouté le 2026-11-14) : les analyses du récit et les synthèses des personas sont générées une fois, puis chargées avec les personas. Raisons et règles de chargement : [api.md](api.md), section 7.
