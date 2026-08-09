# Conventions - CLIP VIDEO

## Regles globales

- Code et noms techniques en anglais
- UI et docs en francais
- Simplicite et lisibilite avant optimisation prematuree
- Gestion d erreurs explicite

## Python

- Type hints requis sur nouveau code
- `snake_case` pour fonctions/variables
- `PascalCase` pour classes
- `UPPER_SNAKE_CASE` pour constantes
- Imports ordonnes: stdlib -> third-party -> local

Exemple SQL parametre:

```python
conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
```

## TypeScript / React

- TypeScript strict
- Components fonctionnels
- Types explicites pour props et API responses
- `camelCase` pour variables/fonctions
- `PascalCase` pour composants/types

## API

- Prefixe commun: `/api`
- Reponses erreurs: `{ "detail": "..." }`
- Statuts coherents avec DB (`queued`, `running`, `done`, `error`)

## SQLite

- Noms tables et colonnes en `snake_case`
- Pas de SQL concatene avec input utilisateur
- Migrations legeres via `init_db()` et `_ensure_columns()`

## Git

Format commit recommande:

```text
feat: short description
fix: short description
docs: short description
refactor: short description
```

## Documentation

- Ecrire court, orientee usage
- Garder les exemples valides avec le code courant
- Supprimer les infos obsoletes au lieu de les accumuler
