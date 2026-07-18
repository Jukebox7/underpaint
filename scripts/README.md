# scripts — outils de maintenance

> Petits utilitaires de projet, sans dépendance applicative.

---

| Script | Rôle | Usage |
|--------|------|-------|
| `lint-mermaid.mjs` | Valide la syntaxe des blocs ` ```mermaid ` de la doc (copié du seed) | `node scripts/lint-mermaid.mjs` |

`lint-mermaid.mjs` attrape les erreurs Mermaid les plus courantes (parenthèses non
quotées, mots réservés, crochets/guillemets déséquilibrés) qui cassent le rendu. À lancer
avant de committer de la documentation. Raccourci : `npm run lint:docs`.
