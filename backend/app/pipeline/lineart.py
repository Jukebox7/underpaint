"""Dessin au trait pour le décalque : contours nets et épurés.

Stratégie pour un trait *traçable* (et non une bouillie de mouchetures) :

1. **Lissage préservant les bords** (edge-preserving filter) pour fondre les textures
   (feuillage, herbe, tissu) en masses, tout en gardant les vraies arêtes.
2. **Détection de contours en couleur** : Canny sur chaque canal Lab (par défaut) — les
   frontières *chromatiques* (rose sur violet, iso-luminantes) sont vues aussi bien que
   les frontières claires/sombres — ou XDoG (style crayon) en option.
3. **Renfort par zones de couleur** : les frontières de la quantification k-means
   (celles du paint-by-number) garantissent un contour autour de chaque masse à peindre.
4. **Nettoyage** : fermeture morphologique pour relier les traits, puis suppression des
   petites composantes (le « poivre et sel »).
5. **Hiérarchie sujet/fond** : si le masque du sujet est fourni, le fond est lissé plus
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
    zones: np.ndarray | None = None,
    zone_colors: np.ndarray | None = None,
) -> np.ndarray:
    """Renvoie un trait noir sur fond blanc (RGB uint8).

    ``detail`` (0-100) règle la finesse : bas = fond très épuré, haut = plus de détails.
    ``zones`` (labels HxW de la palette) ajoute les frontières entre zones de couleur ;
    ``zone_colors`` (centres K×3 RGB) permet de ne garder que les frontières entre
    couleurs franchement différentes (sinon toutes les frontières sont gardées).
    """
    detail = int(max(0, min(detail, 100)))
    h, w = image.shape[:2]
    area = h * w

    smooth = _smooth(image, mask, detail)

    if method == "xdog":
        ink = _xdog_ink(cv2.cvtColor(smooth, cv2.COLOR_RGB2GRAY), detail)
    else:
        ink = _color_canny_ink(smooth, detail)

    if zones is not None:
        ink |= _zone_boundaries(zones, zone_colors, detail)

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


def _color_canny_ink(image: np.ndarray, detail: int) -> np.ndarray:
    """Contours Canny par canal Lab, seuils dérivés de la distribution des gradients.

    Travailler en Lab rend visibles les frontières purement chromatiques (rose/violet de
    même luminosité) que la conversion en gris efface. Les seuils sont calés sur les
    percentiles de la magnitude de gradient *de chaque canal* : une image douce et
    lumineuse (pastel) garde des seuils adaptés à ses contours réels.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2Lab)
    percentile = float(np.interp(detail, [0, 100], [99.3, 97.5]))
    edges = np.zeros(image.shape[:2], dtype=bool)

    for chan in cv2.split(lab):
        blurred = cv2.GaussianBlur(chan, (3, 3), 0)
        gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1)
        mag = cv2.magnitude(gx, gy)
        # Percentile sur les seuls pixels à gradient actif : sur une image plate, le
        # percentile global vaut 0 et raterait le seul vrai bord.
        active = mag[mag > 2.0]
        if active.size < 50:  # canal plat (ex. chroma d'une image en gris)
            continue
        # 0,7 × un percentile haut (régime des vrais bords) : au percentile exact,
        # l'hystérésis n'aurait aucun pixel « fort » à propager sur une image plate.
        # Plancher 64 : la queue du bruit résiduel lissé (surtout en chroma, ≲ 60)
        # ne doit fournir aucun pixel fort.
        upper = max(64.0, 0.7 * float(np.percentile(active, percentile)))
        edges |= cv2.Canny(blurred, 0.4 * upper, upper) > 0

    return edges


def _zone_boundaries(
    zones: np.ndarray, zone_colors: np.ndarray | None = None, detail: int = 50
) -> np.ndarray:
    """Frontières fines (1 px) entre zones de couleur *franchement* différentes.

    Un filtre médian gomme d'abord le tramage du k-means (pixels isolés dans les
    dégradés). Puis, si les couleurs des zones sont fournies, seules les frontières
    entre couleurs éloignées en Lab sont gardées : les frontières de *banding* (bandes
    voisines d'un même dégradé de ciel/nuage) disparaissent, celles des vraies masses
    restent.

    Le renfort suit le curseur ``detail`` — sinon il imposerait une base de traits
    constante et le curseur ne changerait presque rien : à détail bas, lissage médian
    fort + seuil ΔE exigeant → seules les grandes masses contrastées gardent un contour.
    """
    kernel = int(round(np.interp(detail, [0, 100], [11, 3])))
    kernel += (kernel + 1) % 2  # taille impaire requise par medianBlur
    delta_min = float(np.interp(detail, [0, 100], [60.0, 28.0]))
    z = cv2.medianBlur(zones.astype(np.uint8), kernel)

    if zone_colors is not None:
        centers_lab = cv2.cvtColor(
            zone_colors[None].astype(np.uint8), cv2.COLOR_RGB2Lab
        )[0].astype(np.float32)
        dist = np.linalg.norm(centers_lab[:, None] - centers_lab[None, :], axis=2)
        keep = dist > delta_min  # (K, K) : paires de couleurs assez éloignées
        edges = np.zeros(z.shape, dtype=bool)
        edges[:, 1:] |= keep[z[:, 1:], z[:, :-1]]
        edges[1:, :] |= keep[z[1:, :], z[:-1, :]]
        return edges

    edges = np.zeros(z.shape, dtype=bool)
    edges[:, 1:] |= z[:, 1:] != z[:, :-1]
    edges[1:, :] |= z[1:, :] != z[:-1, :]
    return edges


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
