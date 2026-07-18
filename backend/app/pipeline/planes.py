"""Carte des plans : couches de profondeur ordonnées fond→avant.

Chaque plan reçoit comme **couleur de base** sa couleur *dominante* (la couleur de palette
qui couvre le plus de surface dans le plan), pas la médiane : on obtient une teinte franche,
directement reliée à une recette de mélange de la palette, à poser en sous-couche.
"""

from __future__ import annotations

from typing import TypedDict

import cv2
import numpy as np

from .palette import Palette, to_hex


class PlaneInfo(TypedDict):
    order: int
    baseColor: str
    baseColorIndex: int  # index (1-based) dans la palette
    label: str


def compute_planes(
    image: np.ndarray, depth: np.ndarray, palette: Palette, num_planes: int = 4
) -> tuple[np.ndarray, list[PlaneInfo]]:
    """Découpe en ``num_planes`` plans de profondeur (quantiles équilibrés).

    Renvoie (image des plans en aplats francs + contours + numéros, métadonnées
    ordonnées fond→avant).
    """
    n = int(max(2, min(num_planes, 8)))
    qs = np.quantile(depth, np.linspace(0, 1, n + 1))
    thresholds = qs[1:-1]
    plane_idx = np.digitize(depth, thresholds).astype(np.int32)  # 0 = fond

    h, w = image.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)
    info: list[PlaneInfo] = []
    num_centers = palette.centers.shape[0]

    present = [i for i in range(n) if (plane_idx == i).any()]
    for new_order, i in enumerate(present, start=1):
        region = plane_idx == i
        # Couleur dominante = couleur de palette la plus fréquente dans le plan.
        labels_here = palette.labels[region]
        dom = int(np.bincount(labels_here, minlength=num_centers).argmax())
        base = palette.centers[dom]
        out[region] = base

        info.append(
            {
                "order": new_order,
                "baseColor": to_hex(base),
                "baseColorIndex": dom + 1,
                "label": _label(new_order, len(present)),
            }
        )

    _draw_boundaries(out, plane_idx)
    for new_order, i in enumerate(present, start=1):
        _annotate(out, plane_idx == i, new_order, palette.centers, info[new_order - 1])

    return out, info


def _label(order: int, n: int) -> str:
    if order == 1:
        return "arrière-plan"
    if order == n:
        return "premier plan"
    return f"plan {order}"


def _draw_boundaries(canvas: np.ndarray, plane_idx: np.ndarray) -> None:
    """Trace un fin liseré sombre entre plans pour la lisibilité."""
    grad = cv2.morphologyEx(
        plane_idx.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)
    )
    canvas[grad > 0] = (50, 50, 50)


def _annotate(
    canvas: np.ndarray,
    region: np.ndarray,
    order: int,
    centers: np.ndarray,
    plane: PlaneInfo,
) -> None:
    ys, xs = np.where(region)
    cx, cy = int(xs.mean()), int(ys.mean())
    base = centers[plane["baseColorIndex"] - 1]
    lum = 0.299 * base[0] + 0.587 * base[1] + 0.114 * base[2]
    color = (0, 0, 0) if lum > 128 else (255, 255, 255)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.8, min(canvas.shape[:2]) / 600)
    cv2.putText(canvas, str(order), (cx - 8, cy + 8), font, scale, color, 2, cv2.LINE_AA)
