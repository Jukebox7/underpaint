"""Virage sépia de l'image."""

from __future__ import annotations

import numpy as np

# Matrice sépia standard (sur canaux RGB).
_SEPIA = np.array(
    [
        [0.393, 0.769, 0.189],
        [0.349, 0.686, 0.168],
        [0.272, 0.534, 0.131],
    ],
    dtype=np.float32,
)


def to_sepia(image: np.ndarray) -> np.ndarray:
    """Applique un virage sépia à une image RGB (uint8) et renvoie du RGB uint8."""
    rgb = image[:, :, :3].astype(np.float32)
    toned = rgb @ _SEPIA.T
    return np.clip(toned, 0, 255).astype(np.uint8)
