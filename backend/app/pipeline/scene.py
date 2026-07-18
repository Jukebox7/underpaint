"""Objets nommés par plan : Florence-2 (VLM) + SAM (masques) + profondeur.

Pipeline :
1. **Florence-2** décrit la scène (`<MORE_DETAILED_CAPTION>`) puis ancre les phrases de la
   description en boîtes (`<CAPTION_TO_PHRASE_GROUNDING>`) → liste (label, boîte).
2. **SAM** (box-promptable, ``sam2.1_b`` par défaut, surchargeable par
   ``PAINTING_OBJSAM_MODEL`` — ex. un checkpoint SAM 3) transforme chaque boîte en masque.
3. **Depth-Anything** : profondeur médiane de chaque objet → plan + ordre de peinture.

Tout est dégradable : si Florence-2 ou SAM manquent (``PAINTING_NO_VLM=1``), on retombe sur
les masques de ``objects`` (FastSAM/régions) avec des labels génériques.
"""

from __future__ import annotations

import logging
import os
from typing import TypedDict

import cv2
import numpy as np

from .objects import _segment as _fallback_segment
from .palette import to_hex

_LOG = logging.getLogger(__name__)

_FLORENCE = None  # (model, processor) ou False
_SAM = None  # modèle SAM ou False

FLORENCE_MODEL = os.getenv("PAINTING_VLM_MODEL", "microsoft/Florence-2-base-ft")
OBJSAM_MODEL = os.getenv("PAINTING_OBJSAM_MODEL", "sam2.1_b.pt")

_MIN_AREA_RATIO = 0.002
_MAX_AREA_RATIO = 0.9
_MAX_OBJECTS = 40
# Teintes de plan (fond → avant) pour colorier les objets par plan.
_PLANE_TINTS = [
    (210, 224, 240), (208, 232, 212), (245, 232, 200),
    (244, 214, 200), (240, 200, 205), (224, 210, 240),
    (212, 236, 238), (236, 224, 208),
]


class SceneObject(TypedDict):
    index: int
    label: str
    plane: int  # ordre du plan (1 = fond)
    planeLabel: str
    baseColor: str


def analyze_scene(
    image: np.ndarray, depth: np.ndarray, num_planes: int = 4
) -> tuple[np.ndarray, str, list[SceneObject]]:
    """Renvoie (image objets-par-plan, description, métadonnées objets)."""
    caption, items = _describe_and_ground(image)

    masks: list[np.ndarray]
    labels: list[str]
    if items:
        boxes = [b for _, b in items]
        sam_masks = _sam_boxes(image, boxes)
        if sam_masks is not None and len(sam_masks) == len(items):
            masks, labels = sam_masks, [lbl for lbl, _ in items]
        else:
            masks, labels = _fallback_with_labels(image)
    else:
        masks, labels = _fallback_with_labels(image)

    return _compose(image, depth, num_planes, masks, labels, caption)


# --- Florence-2 -----------------------------------------------------------

def _get_florence():
    global _FLORENCE
    if os.getenv("PAINTING_NO_VLM") == "1":
        return None
    if _FLORENCE is None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor

            device = "mps" if torch.backends.mps.is_available() else "cpu"
            model = AutoModelForCausalLM.from_pretrained(
                FLORENCE_MODEL, trust_remote_code=True, torch_dtype=torch.float32
            )
            processor = AutoProcessor.from_pretrained(
                FLORENCE_MODEL, trust_remote_code=True
            )
            model.to(device).eval()
            _FLORENCE = (model, processor, device)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("Florence-2 indisponible (%s) : labels génériques", exc)
            _FLORENCE = False
    return _FLORENCE or None


def _run_florence(image: np.ndarray, task: str, text: str = "") -> dict | None:
    bundle = _get_florence()
    if bundle is None:
        return None
    try:
        import torch
        from PIL import Image

        model, processor, device = bundle
        pil = Image.fromarray(image)
        prompt = task + text
        inputs = processor(text=prompt, images=pil, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            generated = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                num_beams=3,
                do_sample=False,
            )
        decoded = processor.batch_decode(generated, skip_special_tokens=False)[0]
        h, w = image.shape[:2]
        return processor.post_process_generation(
            decoded, task=task, image_size=(w, h)
        )
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Inférence Florence-2 échouée (%s)", exc)
        return None


def _describe_and_ground(
    image: np.ndarray,
) -> tuple[str, list[tuple[str, list[float]]]]:
    cap = _run_florence(image, "<MORE_DETAILED_CAPTION>")
    if cap is None:
        return "", []
    caption = cap.get("<MORE_DETAILED_CAPTION>", "").strip()
    grounded = _run_florence(image, "<CAPTION_TO_PHRASE_GROUNDING>", caption)
    items: list[tuple[str, list[float]]] = []
    if grounded:
        data = grounded.get("<CAPTION_TO_PHRASE_GROUNDING>", {})
        for label, box in zip(data.get("labels", []), data.get("bboxes", [])):
            items.append((str(label), [float(c) for c in box]))
    return caption, _dedup(items)


def _dedup(
    items: list[tuple[str, list[float]]], iou_thr: float = 0.8
) -> list[tuple[str, list[float]]]:
    """Retire les boîtes quasi identiques (Florence ancre parfois en double)."""
    kept: list[tuple[str, list[float]]] = []
    for label, box in items:
        if all(_iou(box, kb) < iou_thr for _, kb in kept):
            kept.append((label, box))
    return kept


def _iou(a: list[float], b: list[float]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


# --- SAM (box-promptable) -------------------------------------------------

def _get_sam():
    global _SAM
    if os.getenv("PAINTING_NO_VLM") == "1":
        return None
    if _SAM is None:
        try:
            from ultralytics import SAM

            _SAM = SAM(OBJSAM_MODEL)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("SAM indisponible (%s) : masques de repli", exc)
            _SAM = False
    return _SAM or None


def _sam_boxes(image: np.ndarray, boxes: list[list[float]]) -> list[np.ndarray] | None:
    model = _get_sam()
    if model is None or not boxes:
        return None
    try:
        import torch

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        res = model(image, bboxes=boxes, device=device, verbose=False)
        r = res[0]
        if r.masks is None:
            return []
        data = r.masks.data.cpu().numpy()
        return [data[i] > 0.5 for i in range(data.shape[0])]
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Inférence SAM échouée (%s) : masques de repli", exc)
        return None


def _fallback_with_labels(image: np.ndarray) -> tuple[list[np.ndarray], list[str]]:
    masks = _fallback_segment(image)
    return masks, [f"objet {i + 1}" for i in range(len(masks))]


# --- Composition ----------------------------------------------------------

def _compose(
    image: np.ndarray,
    depth: np.ndarray,
    num_planes: int,
    masks: list[np.ndarray],
    labels: list[str],
    caption: str,
) -> tuple[np.ndarray, str, list[SceneObject]]:
    h, w = image.shape[:2]
    area = h * w
    min_area, max_area = _MIN_AREA_RATIO * area, _MAX_AREA_RATIO * area

    pairs = []
    for mask, label in zip(masks, labels):
        m = _clean(mask)
        a = int(m.sum())
        if min_area <= a <= max_area:
            pairs.append((m, label, a))
    pairs.sort(key=lambda p: p[2], reverse=True)
    pairs = pairs[:_MAX_OBJECTS]

    n = int(max(2, min(num_planes, 8)))
    qs = np.quantile(depth, np.linspace(0, 1, n + 1))
    thresholds = qs[1:-1]

    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    objects: list[SceneObject] = []
    for idx, (mask, label, _) in enumerate(pairs, start=1):
        plane = int(np.digitize(float(np.median(depth[mask])), thresholds)) + 1
        tint = _PLANE_TINTS[(plane - 1) % len(_PLANE_TINTS)]
        canvas[mask] = tint
        base = np.median(image[mask], axis=0)
        objects.append(
            {
                "index": idx,
                "label": label,
                "plane": plane,
                "planeLabel": _plane_label(plane, n),
                "baseColor": to_hex(np.clip(base, 0, 255).astype(np.uint8)),
            }
        )

    # Contours + numéros par-dessus les aplats de plan.
    for idx, (mask, _, _) in enumerate(pairs, start=1):
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )
        cv2.drawContours(canvas, contours, -1, (40, 40, 40), 1, cv2.LINE_AA)
        ys, xs = np.where(mask)
        cv2.putText(
            canvas, str(idx), (int(xs.mean()) - 5, int(ys.mean()) + 5),
            cv2.FONT_HERSHEY_SIMPLEX, max(0.4, min(h, w) / 1300), (140, 40, 30), 1,
            cv2.LINE_AA,
        )

    objects.sort(key=lambda o: o["plane"])
    return canvas, caption, objects


def _clean(mask: np.ndarray) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel) > 0


def _plane_label(order: int, n: int) -> str:
    if order == 1:
        return "arrière-plan"
    if order >= n:
        return "premier plan"
    return f"plan {order}"
