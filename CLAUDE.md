# painting — assistant de peinture par analyse d'image

> Outil web local : on **drag & drop une image**, le backend l'analyse et renvoie des
> **images dérivées** qui guident la peinture acrylique réaliste — dessin au trait à
> décalquer, carte des plans (ordre de peinture + couleur de fond), palette avec recettes
> de mélange, et gabarit paint-by-number.

---

## Objectif

Aider Paul à peindre : décalquer au crayon depuis le dessin au trait, puis peindre par
couches **de l'arrière-plan vers l'avant** en suivant la carte des plans et la palette.
Le but final à terme : un site React local où l'on dépose une image et où l'on récupère
des images adaptées à ce que l'on veut faire.

## Architecture (résumé)

Monorepo à deux services lancés par **une seule commande** :

| Dossier | Rôle | Stack |
|---------|------|-------|
| `backend/` | Traitement d'image (pipeline) + API | Python 3.11, FastAPI, OpenCV, scikit-learn, rembg |
| `web/` | Drag & drop + affichage des livrables | Vite + React + TypeScript |
| `docs/` | Documentation (vision, archi, pipeline, peinture, API) | Markdown + Mermaid |
| `scripts/` | Outils de maintenance | `lint-mermaid.mjs` |

Détails : [`docs/02-architecture/architecture-generale.md`](docs/02-architecture/architecture-generale.md).

## Commandes

```bash
npm install            # déps d'orchestration (concurrently) à la racine
npm run setup          # installe backend (uv sync) + web (npm install)
npm run dev            # lance backend + web ensemble (arrêt en cascade)
npm run lint:docs      # valide les diagrammes Mermaid de docs/
npm run test:backend   # tests du pipeline
```

- `npm run dev` démarre l'API (port 8000) et le front (port 5173) via `concurrency -k` :
  si l'un s'arrête, l'autre est tué (cascade), et `Ctrl+C` arrête les deux.
- Le front proxifie `/api` vers `http://localhost:8000`.

## Conventions de code

- **Backend** : un module par étape du pipeline dans `backend/app/pipeline/`. Fonctions
  pures `image (np.ndarray) -> résultat` autant que possible ; pas d'I/O réseau dedans.
- **Front** : composants fonctionnels TypeScript, un appel API centralisé dans
  `web/src/api.ts`.
- **Documenter l'approche dossier par dossier** : chaque dossier important porte un
  `README.md` qui explique son rôle et ses choix **avant** d'en lire le code.

## Convention de documentation

La documentation suit `docs/06-ressources/guide-redaction-documentation.md` :
- Schémas en **Mermaid** (jamais d'ASCII-art) ; valider via `node scripts/lint-mermaid.mjs`.
- Pas de frontmatter dans les `.md` de contenu ; tableaux GFM ; liens `.md` relatifs.
- H1 + blockquote d'intro, sections H2/H3, section « Ressources » finale.
- Contenu en français, termes techniques en anglais, ≤ 400 lignes/doc.
