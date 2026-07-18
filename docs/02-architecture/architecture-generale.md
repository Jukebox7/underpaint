# Architecture générale

> Comment le projet est organisé : un monorepo à deux services (backend Python, front
> React) lancés et arrêtés par une seule commande, avec arrêt en cascade.

---

## Vue d'ensemble

```mermaid
flowchart LR
    U["Navigateur<br/>(artiste)"]:::user
    W["web/<br/>Vite + React + TS<br/>port 5173"]
    B["backend/<br/>FastAPI + uvicorn<br/>port 8000"]
    PIPE["pipeline d'image<br/>OpenCV · scikit-learn · rembg"]
    U -->|"drag & drop"| W
    W -->|"POST /api/process<br/>(proxy Vite)"| B
    B --> PIPE
    PIPE -->|"images + métadonnées"| W

    classDef user fill:#dbeafe,stroke:#1e40af,color:#1e3a8a
```

Le front ne calcule rien : il envoie l'image et affiche ce que renvoie le backend. Tout
le traitement vit dans `backend/app/pipeline/`.

## Choix de stack

| Couche | Choix | Raison |
|--------|-------|--------|
| Front | Vite + React + TypeScript | Démarrage rapide, drag & drop natif, proxy `/api` intégré |
| API | FastAPI + uvicorn | Léger, typé (Pydantic), `--reload` en dev |
| Env Python | `uv` | Installation rapide et reproductible des dépendances |
| Vision IA | `rembg` + profondeur ONNX | Détourage et ordre des plans sans dépendre de `torch` |
| Vision classique | OpenCV, scikit-learn, Pillow, numpy | Contours, zones, quantification de couleurs |
| Orchestration | `concurrently -k` | Une commande, arrêt en cascade |

## Orchestration « une seule commande »

Le `package.json` à la racine pilote les deux services :

```bash
npm run dev
```

lance, via `concurrently` :

- `uv run --project backend uvicorn app.main:app --reload --port 8000`
- `npm --prefix web run dev`

### Arrêt en cascade

```mermaid
sequenceDiagram
    participant T as Terminal
    participant C as concurrently
    participant A as API (uvicorn)
    participant W as Web (vite)
    T->>C: npm run dev
    C->>A: démarre
    C->>W: démarre
    Note over A: crash ou kill
    A-->>C: process terminé
    C->>W: SIGTERM (option -k)
    Note over T,W: Ctrl+C → C arrête A et W
```

Le drapeau `-k` (`--kill-others`) garantit que si **l'un** des deux process s'arrête,
l'autre est tué immédiatement. `Ctrl+C` envoie `SIGINT` à `concurrently`, qui le propage
aux deux enfants.

> Le bash système de macOS est en 3.2 (pas de `wait -n`) : on s'appuie donc sur
> `concurrently` (Node) plutôt que sur un script shell pour gérer proprement la cascade.

## Arborescence

```
painting/
├── package.json          # orchestration (setup, dev, lint, test)
├── backend/
│   ├── pyproject.toml
│   └── app/
│       ├── main.py        # routes FastAPI
│       ├── schemas.py     # modèles Pydantic
│       └── pipeline/      # une étape = un module
├── web/
│   ├── vite.config.ts     # proxy /api → :8000
│   └── src/               # composants React
├── docs/
└── scripts/
```

## Flux d'une requête

```mermaid
flowchart TD
    F["web: image déposée"]:::user --> POST["POST /api/process<br/>(multipart + options)"]
    POST --> LD["pipeline: chargement"]
    LD --> RUN["étapes: trait, plans, palette, pbn"]
    RUN --> RESP["JSON: PNG base64 + métadonnées"]:::final
    RESP --> SHOW["web: galerie + palette"]

    classDef user fill:#dbeafe,stroke:#1e40af,color:#1e3a8a
    classDef final fill:#dcfce7,stroke:#15803d,color:#14532d
```

## Ressources

- [Pipeline d'image](../03-pipeline-image/pipeline.md)
- [Contrat d'API](../05-api/contrat-api.md)
- [`concurrently`](https://github.com/open-cli-tools/concurrently)
- [`uv`](https://docs.astral.sh/uv/)
