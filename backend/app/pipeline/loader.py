"""Chargement et normalisation de l'image d'entrée."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

MAX_SIZE_DEFAULT = 1024


def load_image(data: bytes, max_size: int = MAX_SIZE_DEFAULT) -> np.ndarray:
    """Décode des octets en image RGB normalisée (uint8, HxWx3).

    - corrige l'orientation EXIF,
    - convertit en RGB,
    - redimensionne pour que le plus grand côté <= ``max_size``.
    """
    try:
        pil = Image.open(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - on remonte une erreur claire
        raise ValueError("Image illisible ou format non supporté") from exc

    pil = ImageOps.exif_transpose(pil)
    pil = pil.convert("RGB")

    longest = max(pil.size)
    if longest > max_size:
        scale = max_size / longest
        new_size = (round(pil.size[0] * scale), round(pil.size[1] * scale))
        pil = pil.resize(new_size, Image.LANCZOS)

    return np.asarray(pil, dtype=np.uint8)
