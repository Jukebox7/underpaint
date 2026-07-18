# painting

> Assistant de peinture acrylique : dépose une image, récupère des images qui te disent
> **quoi peindre, dans quel ordre, avec quelles couleurs** — et un dessin au trait à
> décalquer.

---

## Ce que ça produit

À partir d'une image déposée, l'outil génère quatre livrables :

| Livrable | À quoi ça sert |
|----------|----------------|
| **Dessin au trait** | Contours nets à décalquer au crayon avant de peindre |
| **Carte des plans** | Zones numérotées de l'arrière-plan vers l'avant + couleur de fond de chaque plan |
| **Palette + mélanges** | Couleurs dominantes avec une recette de mélange acrylique |
| **Paint-by-number** | Gabarit à zones numérotées par couleur |

## Démarrage rapide

Prérequis : Node 20+, Python 3.11+, [`uv`](https://docs.astral.sh/uv/).

```bash
npm install        # outils d'orchestration
npm run setup      # installe backend (uv) + web
npm run dev        # lance tout : API + front
```

Puis ouvrir le front (Vite affiche l'URL, par défaut `http://localhost:5173`) et déposer
une image. `Ctrl+C` arrête les deux services ; si l'un tombe, l'autre est arrêté aussi.

## Structure

```
painting/
├── backend/   # pipeline d'analyse d'image + API FastAPI
├── web/       # interface React (drag & drop + galerie)
├── docs/      # documentation (vision, archi, pipeline, peinture, API)
└── scripts/   # outils (lint Mermaid)
```

## Documentation

- [Vision produit](docs/01-vision/objectif-produit.md)
- [Architecture générale](docs/02-architecture/architecture-generale.md)
- [Pipeline d'image](docs/03-pipeline-image/pipeline.md)
- [Couleurs & mélanges acryliques](docs/04-peinture/couleurs-acrylique.md)
- [Contrat d'API](docs/05-api/contrat-api.md)

---

*Projet local, en cours de construction. Voir [`CLAUDE.md`](CLAUDE.md) pour les commandes
et conventions.*
