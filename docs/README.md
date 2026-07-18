# Documentation — painting

> Point d'entrée de la documentation du projet. Chaque dossier traite un thème ; les
> documents suivent le standard de rédaction du seed (Mermaid, tableaux GFM, français).

---

## Navigation

```mermaid
flowchart LR
    V["01 · Vision<br/>objectif produit"]:::user
    A["02 · Architecture<br/>monorepo, orchestration"]
    P["03 · Pipeline<br/>étapes de traitement"]
    PE["04 · Peinture<br/>couleurs & mélanges"]
    API["05 · API<br/>contrat backend"]
    R["06 · Ressources<br/>guide de rédaction"]:::final
    V --> A --> P --> PE --> API --> R

    classDef user fill:#dbeafe,stroke:#1e40af,color:#1e3a8a
    classDef final fill:#dcfce7,stroke:#15803d,color:#14532d
```

## Sommaire

| Dossier | Contenu |
|---------|---------|
| [`01-vision/`](01-vision/objectif-produit.md) | Pourquoi l'outil existe, but final, périmètre V1 |
| [`02-architecture/`](02-architecture/architecture-generale.md) | Monorepo, orchestration une commande, arrêt en cascade |
| [`03-pipeline-image/`](03-pipeline-image/pipeline.md) | Les étapes de l'analyse d'image et leurs livrables |
| [`04-peinture/`](04-peinture/couleurs-acrylique.md) | Théorie des couleurs et recettes de mélange acrylique |
| [`05-api/`](05-api/contrat-api.md) | Endpoints, formats d'entrée/sortie |
| [`06-ressources/`](06-ressources/guide-redaction-documentation.md) | Standard de rédaction (copié du seed) |

## Convention

Voir [`06-ressources/guide-redaction-documentation.md`](06-ressources/guide-redaction-documentation.md).
Valider les diagrammes avant de committer :

```bash
node scripts/lint-mermaid.mjs
```
