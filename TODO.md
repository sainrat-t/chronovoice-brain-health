# TODO : ChronoVoice Brain, jusqu'à la remise du 20 novembre 2026

> Proposition du 2026-11-12, **à valider**. Remise le vendredi 20 novembre ; l'heure et le fuseau horaire sont à vérifier dans le dashboard hack2skill.
>
> Qui fait quoi : 👤 Thibaut · 🤖 Claude · 👥 ensemble.

## Bloquants à lever maintenant

- [ ] 👤 Vérifier dans le dashboard hack2skill :
  - l'heure et le fuseau horaire de la remise ;
  - les exigences complètes de soumission (lien de démo ? vidéo ? dépôt de code ?).
- [x] 👤 Répondre au questionnaire des specs : [`docs/specs/questions.md`](docs/specs/questions.md). Reste Q28 (MyMémoires).
- [ ] 👤 Mettre les clés dans `backend/.env` : `ELEVENLABS_API_KEY` et `ANTHROPIC_API_KEY` (Claude Opus 5.5).
- [ ] 👤 Créer un compte Render, avec l'offre payante d'entrée pendant l'évaluation (du 20 au 30 novembre).
- [ ] 👤 Fournir 1 ou 2 enregistrements en anglais pour tester Scribe : quelqu'un qui raconte un souvenir, avec son accord, sans données de vrais patients.
- [x] 👥 Faire le premier commit et créer le dépôt privé, car le jury peut demander le code (git est initialisé, sans commit).

## Jeudi 12 et vendredi 13 novembre : specs

- [x] 🤖 Questionnaire des specs.
- [x] 🤖 Rédiger les specs à partir des réponses, dans [`docs/specs/`](docs/specs/index.md) :
  - pipeline d'analyse ;
  - interface soignant ;
  - enregistrement au micro ;
  - données synthétiques ;
  - API.
- [ ] 👤 Valider les specs.
- [ ] 🤖 Tester Scribe : les 5 tests de [`docs/tech/elevenlabs-scribe.md`](docs/tech/elevenlabs-scribe.md), section 9.
- [x] 👥 Clore la discovery (close le 2026-11-12) :
  - figer la v0.3 (marqueurs, seuils, niveaux d'orientation) ;
  - limiter la lecture aux fiches 07 et 09.

## Samedi 14 et dimanche 15 novembre : pipeline d'analyse

- [x] 🤖 `backend/app/schemas.py` : le contrat d'interface entre les étapes, avec 40 tests.
- [ ] 🤖 Étape 0 :
  - [ ] client Scribe (attend la clé ElevenLabs) ;
  - [x] choix de la voix suivie ;
  - [x] contrôle qualité (seuil de confiance provisoire, à caler sur de vraies transcriptions).
- [x] 🤖 Étape 1 : les marqueurs, en fonctions pures, testés sur des cas calculés à la main (fait le 13 novembre).
  - [ ] 🤖 Ajuster la liste des hésitations et la détection des mots coupés après les tests de Scribe.
- [x] 🤖 Générateur de données synthétiques et personas (fait le 13 novembre : 3 personas, 30 séances).
  - [ ] 👤 Relire quelques récits des personas (`backend/data/synthetic/stories/`).
  - [ ] 👥 Limiter l'effet du thème du récit sur les marqueurs sémantiques.
- [x] 🤖 Étape 3 (fait le 13 novembre) :
  - référence personnelle ;
  - test de chaque marqueur ;
  - indice d'écart ;
  - niveaux d'orientation, avec une simulation des fausses alertes.
- [ ] 👤 Valider les résultats sur les personas.

## Lundi 16 novembre : LLM et API

- [ ] 🤖 Étape 2 : l'analyste du récit, dans le périmètre décidé dans les specs.
- [ ] 🤖 Étape 4 : la synthèse clinique, avec le validateur qui rejette le vocabulaire diagnostique.
- [ ] 🤖 API FastAPI :
  - personnes ;
  - séances ;
  - statut du traitement ;
  - réception d'un enregistrement venu d'une autre application (module branchable).

## Mardi 17 et mercredi 18 novembre : interface soignant et micro

- [ ] 🤖 Mise en place du frontend : Vite, React, TypeScript, Tailwind, Recharts.
- [ ] 🤖 Écrans définis dans les specs.
- [ ] 🤖 Enregistrement au micro dans le navigateur :
  - envoi ;
  - suivi du traitement ;
  - affichage du résultat.
- [ ] 🤖 Mise en ligne avec accès invité (slide 11 du template).
- [ ] 👥 Test de bout en bout.

## Jeudi 19 novembre : dossier de soumission

- [ ] 👥 Deck sur le template de 16 slides. 👤 Slides sur l'équipe : 1, 2, 3 et 14.
- [ ] 🤖 Documentation technique : hypothèses, dépendances, limites.
- [ ] 🤖 Plan de validation (exigence 6 du challenge), simulé sur les personas.
- [ ] 👥 Répétition de la démo : 7 minutes, puis 3 minutes de questions.

## Vendredi 20 novembre : remise

- [ ] 👥 Marge pour les corrections.
- [ ] 👤 Soumission.
