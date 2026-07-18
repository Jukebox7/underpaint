# backend — pipeline d'analyse + API

> Service Python qui reçoit une image et renvoie les quatre livrables. L'API (FastAPI) est
> une fine couche au-dessus du **pipeline** : tout le traitement vit dans
> `app/pipeline/`, un module par étape.

---

## Approche

- **Séparation API / traitement** : `app/main.py` ne fait que router, valider et encoder.
  Les calculs sont dans `app/pipeline/`, en fonctions testables sans serveur.
- **Hybride IA + classique** : `rembg` (IA) isole le sujet du fond ; OpenCV et
  scikit-learn (classique) font contours, profondeur heuristique, zones et palette.
- **Robuste par défaut** : aucune étape ne dépend d'un modèle lourd obligatoire. La
  profondeur utilise une heuristique (pas de `torch`), améliorable plus tard.
- **Fonctions pures** : chaque module expose `f(image: np.ndarray, ...) -> résultat`, sans
  I/O réseau ni état global (hors cache du modèle `rembg`).

## Modules

| Fichier | Rôle |
|---------|------|
| `app/main.py` | Routes FastAPI (`/api/health`, `/api/process`) |
| `app/schemas.py` | Modèles Pydantic d'entrée/sortie |
| `app/pipeline/loader.py` | Chargement, EXIF, RGB, redimensionnement |
| `app/pipeline/segmentation.py` | Masque sujet/fond (rembg) + profondeur (Depth-Anything) |
| `app/pipeline/objects.py` | Contours objet par objet (FastSAM-x / repli régions) |
| `app/pipeline/scene.py` | Objets nommés par plan (Florence-2 + SAM 2.1 + profondeur) |
| `app/pipeline/planes.py` | Plans ordonnés fond→avant + couleur de fond |
| `app/pipeline/lineart.py` | Dessin au trait (XDoG/Canny) |
| `app/pipeline/sepia.py` | Virage sépia de l'image |
| `app/pipeline/palette.py` | Palette de couleurs (k-means) |
| `app/pipeline/mixing.py` | Recettes de mélange acrylique |
| `app/pipeline/paintbynumber.py` | Gabarit à zones numérotées |
| `app/pipeline/encoding.py` | Encodage PNG → data URL base64 |

## Lancer

Depuis la racine du projet (recommandé) :

```bash
npm run setup        # uv sync (crée backend/.venv)
npm run dev          # lance l'API + le front
npm run test:backend # tests du pipeline
```

Directement dans `backend/` :

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -q
```

## Détails

- [Pipeline d'image](../docs/03-pipeline-image/pipeline.md)
- [Couleurs & mélanges](../docs/04-peinture/couleurs-acrylique.md)
- [Contrat d'API](../docs/05-api/contrat-api.md)
