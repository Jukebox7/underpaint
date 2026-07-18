"""Configuration des tests : pas de téléchargement de modèle lourd (profondeur)."""

import os

# Force la profondeur heuristique et le repli régions (pas de FastSAM) :
# tests rapides et hors-ligne.
os.environ.setdefault("PAINTING_NO_DEPTH_MODEL", "1")
os.environ.setdefault("PAINTING_NO_SAM", "1")
os.environ.setdefault("PAINTING_NO_VLM", "1")
