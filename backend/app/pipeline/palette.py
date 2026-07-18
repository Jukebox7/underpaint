"""Extraction de la palette dominante par k-means."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans


@dataclass
class Palette:
    centers: np.ndarray  # (K, 3) uint8 RGB, triés par surface décroissante
    labels: np.ndarray  # (H, W) int, index de couleur par pixel
    pct: np.ndarray  # (K,) float, pourcentage de surface


def extract_palette(image: np.ndarray, num_colors: int = 12) -> Palette:
    """Quantifie l'image en ``num_colors`` couleurs dominantes.

    Le k-means tourne sur un échantillon ; les labels sont ensuite assignés à tous les
    pixels par plus proche centre. Les couleurs sont triées par surface décroissante.
    """
    h, w = image.shape[:2]
    pixels = image.reshape(-1, 3).astype(np.float32)

    sample = pixels
    max_samples = 20000
    if pixels.shape[0] > max_samples:
        idx = np.linspace(0, pixels.shape[0] - 1, max_samples).astype(int)
        sample = pixels[idx]

    k = int(max(2, min(num_colors, 24)))
    km = KMeans(n_clusters=k, n_init=4, random_state=0)
    km.fit(sample)

    centers = km.cluster_centers_
    # Assigne chaque pixel au centre le plus proche.
    dists = np.linalg.norm(pixels[:, None, :] - centers[None, :, :], axis=2)
    labels_flat = dists.argmin(axis=1)

    counts = np.bincount(labels_flat, minlength=k)
    order = np.argsort(counts)[::-1]
    remap = np.zeros(k, dtype=int)
    for new_idx, old_idx in enumerate(order):
        remap[old_idx] = new_idx

    labels_sorted = remap[labels_flat].reshape(h, w)
    centers_sorted = np.clip(centers[order], 0, 255).astype(np.uint8)
    pct_sorted = (counts[order] / counts.sum() * 100.0).astype(np.float32)

    return Palette(centers=centers_sorted, labels=labels_sorted, pct=pct_sorted)


def to_hex(rgb: np.ndarray) -> str:
    r, g, b = (int(c) for c in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"
