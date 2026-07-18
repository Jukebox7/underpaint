"""Dessin au trait pour le décalque : contours nets et épurés.

Stratégie pour un trait *traçable* (et non une bouillie de mouchetures) :

1. **Lissage préservant les bords** (edge-preserving filter) pour fondre les textures
   (feuillage, herbe, tissu) en masses, tout en gardant les vraies arêtes.
2. **Détection de contours** (Canny auto-réglé) ou XDoG (style crayon) en option.
3. **Nettoyage** : fermeture morphologique pour relier les traits, puis suppression des
   petites composantes (le « poivre et sel »).
4. **Hiérarchie sujet/fond** : si le masque du sujet est fourni, le fond est lissé plus
   fort et ses petites composantes filtrées plus sévèrement → trait net sur le sujet,
   fond épuré.
"""

from __future__ import annotations

import cv2
import numpy as np


def line_art(
    image: np.ndarray,
    mask: np.ndarray | None = None,
    detail: int = 50,
    method: str = "contour",
) -> np.ndarray:
    """Renvoie un trait noir sur fond blanc (RGB uint8).

    ``detail`` (0-100) règle la finesse : bas = fond très épuré, haut = plus de détails.
    """
    detail = int(max(0, min(detail, 100)))
    h, w = image.shape[:2]
    area = h * w

    smooth = _smooth(image, mask, detail)
    gray = cv2.cvtColor(smooth, cv2.COLOR_RGB2GRAY)

    if method == "xdog":
        ink = _xdog_ink(gray, detail)
    else:
        ink = _canny_ink(gray, detail)

    # Relie les traits proches puis enlève les mouchetures.
    ink = cv2.morphologyEx(
        ink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8)
    ).astype(bool)

    base_area = area / 200_000
    min_area_subject = max(6, int(base_area * np.interp(detail, [0, 100], [14, 2])))
    min_area_bg = max(min_area_subject, int(min_area_subject * 3))

    if mask is not None and not mask.all():
        kept_subj = _remove_small(ink & mask, min_area_subject)
        kept_bg = _remove_small(ink & ~mask, min_area_bg)
        ink = kept_subj | kept_bg
    else:
        ink = _remove_small(ink, min_area_subject)

    out = np.full((h, w, 3), 255, dtype=np.uint8)
    out[ink] = (25, 25, 25)
    return out


def _smooth(image: np.ndarray, mask: np.ndarray | None, detail: int) -> np.ndarray:
    """Lissage préservant les bords ; plus fort sur le fond si un masque est donné.

    À ``detail`` = 100, le lissage tombe à zéro : on garde l'image brute (contours non
    lissés, plus de détails mais aussi plus de bruit).
    """
    sigma_s = float(np.interp(detail, [0, 100], [150, 0]))
    sigma_r = float(np.interp(detail, [0, 100], [0.55, 0.20]))
    if sigma_s < 5:  # lissage négligeable → on n'applique aucun filtre
        return image
    img = np.ascontiguousarray(image)
    fg = cv2.edgePreservingFilter(
        img, flags=cv2.RECURS_FILTER, sigma_s=sigma_s, sigma_r=sigma_r
    )
    if mask is None or mask.all():
        return fg
    bg = cv2.edgePreservingFilter(
        img,
        flags=cv2.RECURS_FILTER,
        sigma_s=min(200.0, sigma_s * 1.8),
        sigma_r=min(0.9, sigma_r * 1.5),
    )
    return np.where(mask[:, :, None], fg, bg)


def _canny_ink(gray: np.ndarray, detail: int) -> np.ndarray:
    """Contours via Canny auto-réglé (seuils dérivés de la médiane)."""
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    v = float(np.median(blurred))
    sigma = float(np.interp(detail, [0, 100], [0.50, 0.20]))
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edges = cv2.Canny(blurred, lower, max(lower + 1, upper))
    return edges > 0


def _xdog_ink(gray: np.ndarray, detail: int) -> np.ndarray:
    """Trait type crayon (Extended Difference of Gaussians), réglage propre."""
    g = gray.astype(np.float32) / 255.0
    sigma = 1.2
    g1 = cv2.GaussianBlur(g, (0, 0), sigmaX=sigma)
    g2 = cv2.GaussianBlur(g, (0, 0), sigmaX=sigma * 1.6)  # ratio classique k=1.6
    dog = g1 - 0.98 * g2
    thr = float(np.interp(detail, [0, 100], [0.010, -0.002]))
    return dog < thr


def _remove_small(ink: np.ndarray, min_area: int) -> np.ndarray:
    """Supprime les composantes connexes de surface < ``min_area``."""
    ink_u8 = ink.astype(np.uint8)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(ink_u8, connectivity=8)
    keep = np.zeros_like(ink, dtype=bool)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            keep[labels == i] = True
    return keep
