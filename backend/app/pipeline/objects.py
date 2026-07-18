"""Contours objet par objet.

Segmente l'image en **objets distincts** puis trace le contour de chacun, façon
livre de coloriage par objet (utile pour savoir quel élément peindre comme un tout).

Méthode principale : **FastSAM** (famille Segment Anything, mode « everything » qui
segmente tous les objets sans prompt), exécuté via ultralytics. Repli automatique sur une
**segmentation par régions** (scikit-image, felzenszwalb) si FastSAM est indisponible
(pas de modèle, variable ``PAINTING_NO_SAM=1``) — la chaîne reste fonctionnelle.
"""

from __future__ import annotations

import os

import cv2
import numpy as np

_MODEL = None
_MIN_AREA_RATIO = 0.0015  # ignore les objets < 0,15 % de l'image
_MAX_AREA_RATIO = 0.85  # ignore un masque quasi pleine image (= fond global)
_MAX_OBJECTS = 50
# Modèle FastSAM : -x plus précis (défaut), -s plus rapide. Surchargeable par env.
FASTSAM_MODEL = os.getenv("PAINTING_SAM_MODEL", "FastSAM-x.pt")


def object_contours(image: np.ndarray) -> np.ndarray:
    """Trace, sur fond blanc, le contour fin de chaque objet + son numéro."""
    masks = _segment(image)
    h, w = image.shape[:2]
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)

    masks = [_clean_mask(m) for m in masks]
    min_area = int(_MIN_AREA_RATIO * h * w)
    max_area = int(_MAX_AREA_RATIO * h * w)
    masks = [m for m in masks if min_area <= int(m.sum()) <= max_area]
    masks.sort(key=lambda m: int(m.sum()), reverse=True)
    masks = masks[:_MAX_OBJECTS]

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.4, min(h, w) / 1300)
    for idx, mask in enumerate(masks, start=1):
        # Contours fidèles : tous les contours (externes + trous internes), sans
        # simplification de polygone, pour suivre précisément la forme de l'objet.
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE
        )
        cv2.drawContours(canvas, contours, -1, (40, 40, 40), 1, cv2.LINE_AA)
        ys, xs = np.where(mask)
        cv2.putText(
            canvas,
            str(idx),
            (int(xs.mean()) - 5, int(ys.mean()) + 5),
            font,
            scale,
            (180, 60, 40),
            1,
            cv2.LINE_AA,
        )

    return canvas


def _clean_mask(mask: np.ndarray) -> np.ndarray:
    """Retire juste les fines bavures (1-2 px) sans arrondir la forme de l'objet."""
    m = mask.astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel) > 0


def _segment(image: np.ndarray) -> list[np.ndarray]:
    masks = _fastsam_masks(image)
    if masks is None:
        masks = _region_masks(image)
    return masks


def _get_model():
    global _MODEL
    if os.getenv("PAINTING_NO_SAM") == "1":
        return None
    if _MODEL is None:
        try:
            from ultralytics import FastSAM

            _MODEL = FastSAM(FASTSAM_MODEL)  # téléchargé au premier appel
        except Exception:  # noqa: BLE001
            _MODEL = False
    return _MODEL or None


def _fastsam_masks(image: np.ndarray) -> list[np.ndarray] | None:
    model = _get_model()
    if model is None:
        return None
    try:
        results = model(
            image,
            device="cpu",
            retina_masks=True,
            imgsz=1024,  # plus haute résolution → capte les structures fines (pont, rivière)
            conf=0.2,  # seuil bas → détecte plus d'objets
            iou=0.9,
            verbose=False,
        )
        r = results[0]
        if r.masks is None:
            return []
        data = r.masks.data.cpu().numpy()  # (N, H, W)
        return [data[i] > 0.5 for i in range(data.shape[0])]
    except Exception:  # noqa: BLE001
        return None


def _region_masks(image: np.ndarray) -> list[np.ndarray]:
    """Repli : régions cohérentes via felzenszwalb (scikit-image)."""
    try:
        from skimage.segmentation import felzenszwalb

        h, w = image.shape[:2]
        seg = felzenszwalb(image, scale=300, sigma=0.8, min_size=max(64, h * w // 400))
        return [seg == label for label in np.unique(seg)]
    except Exception:  # noqa: BLE001
        # Dernier repli : un seul "objet" = toute l'image.
        h, w = image.shape[:2]
        return [np.ones((h, w), dtype=bool)]
