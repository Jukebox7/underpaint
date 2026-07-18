"""Segmentation : masque sujet/fond (rembg) + carte de profondeur.

La profondeur utilise un vrai modèle monoculaire **Depth-Anything v2 small** au format
ONNX (exécuté sur CPU via onnxruntime, sans ``torch``), téléchargé au premier appel. Si le
modèle n'est pas disponible (pas de réseau, etc.), on retombe sur une heuristique classique
(position verticale + netteté) pour que la chaîne reste fonctionnelle.
"""

from __future__ import annotations

import os

import cv2
import numpy as np

_SESSION = None  # session rembg
_DEPTH = None  # session ONNX profondeur
_DEPTH_IO: tuple[str, str] | None = None  # (nom entrée, nom sortie)

# Candidats de modèle ONNX (repo HuggingFace, fichier).
_DEPTH_MODELS = [
    ("onnx-community/depth-anything-v2-small", "onnx/model.onnx"),
    ("onnx-community/depth-anything-v2-small", "onnx/model_quantized.onnx"),
]

# Normalisation ImageNet attendue par Depth-Anything.
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_INPUT_SIZE = 518  # multiple de 14 attendu par le ViT


def _get_session():
    """Charge (une seule fois) la session rembg ; None si indisponible."""
    global _SESSION
    if _SESSION is None:
        try:
            from rembg import new_session

            _SESSION = new_session("u2net")
        except Exception:  # noqa: BLE001
            _SESSION = False
    return _SESSION or None


def subject_mask(image: np.ndarray) -> np.ndarray:
    """Masque booléen du sujet (premier plan). Fallback : ellipse centrale."""
    session = _get_session()
    if session is not None:
        try:
            from rembg import remove

            cut = remove(image, session=session)  # RGBA
            return cut[:, :, 3] > 127
        except Exception:  # noqa: BLE001
            pass

    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(
        mask, (w // 2, h // 2), (int(w * 0.35), int(h * 0.45)), 0, 0, 360, 255, -1
    )
    return mask > 0


def depth_map(image: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Carte de proximité dans [0, 1] (1 = au plus près du spectateur).

    Essaie le modèle ONNX ; à défaut, heuristique. Le sujet détouré, s'il est fourni, est
    légèrement ramené vers l'avant pour fiabiliser le premier plan.
    """
    depth = _onnx_depth(image)
    if depth is None:
        depth = _heuristic_depth(image, mask)
    elif mask is not None:
        # Garantit que le sujet ne passe pas derrière le décor.
        subj = float(np.median(depth[mask])) if mask.any() else 0.0
        depth = np.where(mask, np.maximum(depth, max(subj, 0.6)), depth)
        depth = _normalize(depth)

    return depth


def _get_depth_session():
    global _DEPTH, _DEPTH_IO
    if os.getenv("PAINTING_NO_DEPTH_MODEL") == "1":
        return None, None
    if _DEPTH is None:
        try:
            import onnxruntime as ort
            from huggingface_hub import hf_hub_download

            path = None
            for repo, filename in _DEPTH_MODELS:
                try:
                    path = hf_hub_download(repo, filename)
                    break
                except Exception:  # noqa: BLE001 - on essaie le candidat suivant
                    continue
            if path is None:
                _DEPTH = False
            else:
                sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
                _DEPTH = sess
                _DEPTH_IO = (sess.get_inputs()[0].name, sess.get_outputs()[0].name)
        except Exception:  # noqa: BLE001
            _DEPTH = False
    return (_DEPTH or None), _DEPTH_IO


def _onnx_depth(image: np.ndarray) -> np.ndarray | None:
    sess, io = _get_depth_session()
    if sess is None or io is None:
        return None
    try:
        h, w = image.shape[:2]
        resized = cv2.resize(image, (_INPUT_SIZE, _INPUT_SIZE)).astype(np.float32) / 255.0
        norm = (resized - _MEAN) / _STD
        tensor = np.transpose(norm, (2, 0, 1))[None].astype(np.float32)
        name_in, name_out = io
        out = sess.run([name_out], {name_in: tensor})[0]
        depth = np.squeeze(out).astype(np.float32)
        depth = cv2.resize(depth, (w, h))
        # Depth-Anything : valeur élevée = proche → cohérent avec notre convention.
        return _normalize(depth)
    except Exception:  # noqa: BLE001
        return None


def _heuristic_depth(image: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)

    rows = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    vertical = np.repeat(rows, w, axis=1)

    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    sharp = _normalize(cv2.GaussianBlur(lap, (0, 0), sigmaX=7))

    depth = 0.5 * vertical + 0.5 * sharp
    if mask is not None:
        depth = np.where(mask, np.maximum(depth, 0.7), depth * 0.85)
    depth = cv2.GaussianBlur(depth.astype(np.float32), (0, 0), sigmaX=3)
    return _normalize(depth)


def _normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)
