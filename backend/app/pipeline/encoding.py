"""Encodage d'images numpy (RGB) en data URL PNG base64."""

from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image


def to_data_url(image: np.ndarray) -> str:
    """Encode une image RGB (uint8, HxWx3) en data URL PNG base64."""
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    if image.ndim == 2:
        pil = Image.fromarray(image, mode="L").convert("RGB")
    else:
        pil = Image.fromarray(image[:, :, :3], mode="RGB")
    buffer = io.BytesIO()
    pil.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
