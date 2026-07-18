"""Recettes de mélange acrylique pour approcher une couleur cible.

Modèle volontairement simple et pédagogique (pas une simulation de pigments) : le mélange
de plusieurs primaires est approché par une **moyenne géométrique pondérée des
réflectances** (comportement soustractif : le mélange assombrit), et la proximité est
mesurée par la distance perceptuelle ΔE (CIE76) dans l'espace Lab.
"""

from __future__ import annotations

from itertools import combinations
from typing import TypedDict

import numpy as np

# Jeu d'acryliques de base (sRGB approximatifs).
PRIMARIES: dict[str, tuple[int, int, int]] = {
    "Blanc de titane": (245, 245, 242),
    "Jaune primaire": (250, 201, 20),
    "Magenta": (208, 26, 98),
    "Cyan": (0, 158, 200),
    "Bleu outremer": (32, 42, 132),
    "Terre d'ombre brûlée": (110, 60, 38),
    "Noir de mars": (26, 26, 30),
}
_NAMES = list(PRIMARIES)
_RGB = np.array([PRIMARIES[n] for n in _NAMES], dtype=np.float32)


class RecipePart(TypedDict):
    primary: str
    parts: int


class Recipe(TypedDict):
    parts: list[RecipePart]
    deltaE: float


def mix_recipe(target_rgb: np.ndarray, max_primaries: int = 3) -> Recipe:
    """Cherche la meilleure recette (≤ ``max_primaries``) pour la couleur cible."""
    target_lab = _srgb_to_lab(np.asarray(target_rgb, dtype=np.float32)[None, :])[0]
    refl = np.clip(_RGB / 255.0, 1e-3, 1.0)
    log_refl = np.log(refl)

    part_options = [1, 2, 3, 4]
    best: Recipe | None = None
    best_de = float("inf")

    for size in range(1, max_primaries + 1):
        for combo in combinations(range(len(_NAMES)), size):
            for parts in _weight_tuples(size, part_options):
                weights = np.array(parts, dtype=np.float32)
                weights = weights / weights.sum()
                mixed_refl = np.exp(log_refl[list(combo)].T @ weights)
                mixed_rgb = np.clip(mixed_refl * 255.0, 0, 255)
                lab = _srgb_to_lab(mixed_rgb[None, :])[0]
                de = float(np.linalg.norm(target_lab - lab))
                if de < best_de:
                    best_de = de
                    best = {
                        "parts": [
                            {"primary": _NAMES[combo[i]], "parts": int(parts[i])}
                            for i in range(size)
                        ],
                        "deltaE": round(de, 2),
                    }

    assert best is not None
    return best


def _weight_tuples(size: int, options: list[int]):
    """Combinaisons de parts entières, sans redondance d'échelle évidente."""
    if size == 1:
        yield (1,)
        return
    for combo in _product(options, size):
        if min(combo) == 1:  # au moins une part = 1 pour limiter les doublons d'échelle
            yield combo


def _product(options: list[int], size: int):
    if size == 1:
        for o in options:
            yield (o,)
        return
    for o in options:
        for rest in _product(options, size - 1):
            yield (o, *rest)


def _srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0..255) -> CIELAB (D65). Entrée (N,3), sortie (N,3)."""
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float32,
    )
    xyz = lin @ m.T
    white = np.array([0.95047, 1.0, 1.08883], dtype=np.float32)
    xyz = xyz / white
    eps = 0.008856
    f = np.where(xyz > eps, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    L = 116.0 * f[:, 1] - 16.0
    a = 500.0 * (f[:, 0] - f[:, 1])
    b = 200.0 * (f[:, 1] - f[:, 2])
    return np.stack([L, a, b], axis=1)
