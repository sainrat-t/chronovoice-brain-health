# AGENTS.md — ChronoVoice Brain

Instructions de référence pour tout agent intervenant sur ce dépôt.
Le guide complet du projet est dans [`CLAUDE.md`](CLAUDE.md) — le lire en priorité avant toute action.

## Règles clés pour les agents

1. **Base de connaissances OKF v0.2 (`docs/`)** :
   - Toujours démarrer la navigation par [`docs/index.md`](docs/index.md) (`okf_version: "0.2"`), puis suivre les `index.md` de sous-dossiers (*progressive disclosure*).
   - Tout document créé ou modifié dans `docs/` doit conserver un frontmatter YAML OKF v0.2 valide (`type`, `title`, `description`, `status`, `tags`, et `sources`/`verified` pour les éléments sourcés).
   - Mettre à jour l'`index.md` du dossier concerné et ajouter une entrée datée en tête de [`docs/log.md`](docs/log.md) à chaque modification structurante.
   - Vérifier la conformité avec `uv run pytest tests/test_okf.py` (depuis `backend/`).
2. **Sécurité clinique & discovery** :
   - Jamais de vocabulaire diagnostique ; toujours citer les sources PubMed/Europe PMC vérifiées pour chaque métrique ou seuil ; aucune donnée réelle de patient (données synthétiques uniquement).
   - Valider chaque étape avec l'utilisateur avant de passer à la suivante (`CLAUDE.md`).
3. **Prototype** :
   - Le code suit les specs v1 de [`docs/specs/`](docs/specs/index.md).
   - Les étapes du pipeline n'échangent que les modèles de `backend/app/schemas.py`.
