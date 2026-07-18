"""Gabarit paint-by-number : contours des zones + numéro de couleur par région."""

from __future__ import annotations

import cv2
import numpy as np

from .palette import Palette


def paint_by_number(palette: Palette, min_area: int = 400) -> np.ndarray:
    """Trace les frontières entre zones de couleur et numérote les régions.

    Le numéro inscrit correspond à l'index (1-based) de la couleur dans la palette.
    """
    labels = palette.labels
    h, w = labels.shape
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)

    k = palette.centers.shape[0]
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.35, min(h, w) / 1400)

    for idx in range(k):
        mask = (labels == idx).astype(np.uint8)
        if not mask.any():
            continue

        # Frontières de la zone -> trait noir.
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, contours, -1, (40, 40, 40), 1, cv2.LINE_AA)

        # Numéro au centre de chaque composante connexe assez grande.
        num, _, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for comp in range(1, num):
            if stats[comp, cv2.CC_STAT_AREA] < min_area:
                continue
            cx, cy = centroids[comp]
            cv2.putText(
                canvas,
                str(idx + 1),
                (int(cx) - 5, int(cy) + 5),
                font,
                scale,
                (90, 90, 90),
                1,
                cv2.LINE_AA,
            )

    return canvas
