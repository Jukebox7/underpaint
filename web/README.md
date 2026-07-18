# web — interface React

> Front Vite + React + TypeScript. Rôle unique : déposer une image, l'envoyer au backend,
> et afficher les quatre livrables + la palette. Aucun calcul d'image côté navigateur.

---

## Approche

- **Front « mince »** : tout le traitement est au backend. Le front gère le drag & drop,
  l'appel API et l'affichage/téléchargement.
- **Appel API centralisé** : un seul point d'accès dans `src/api.ts` (POST
  `/api/process`), proxifié par Vite vers `http://localhost:8000`.
- **Composants par responsabilité** :

| Composant | Rôle |
|-----------|------|
| `components/Dropzone.tsx` | Zone de drag & drop + sélection de fichier + options |
| `components/ResultGallery.tsx` | Onglets des livrables image + téléchargement |
| `components/PalettePanel.tsx` | Pastilles de couleur, recettes, ordre des plans |
| `App.tsx` | État (image, options, résultat, chargement, erreur) |
| `api.ts` | Appel `POST /api/process` |

## Lancer

Depuis la racine : `npm run dev` (lance aussi le backend). Seul :

```bash
npm install
npm run dev   # Vite, port 5173, proxy /api -> :8000
```

## Détails

- [Contrat d'API](../docs/05-api/contrat-api.md)
- [Architecture générale](../docs/02-architecture/architecture-generale.md)
