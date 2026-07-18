"""Orchestrateur : enchaîne les étapes et assemble la réponse.

Les étapes coûteuses qui ne dépendent que de l'image (détourage, profondeur, FastSAM,
Florence-2 + SAM) sont mises en cache par empreinte de l'image : rejouer le pipeline avec
d'autres réglages (couleurs, plans, détail) ne recalcule que les étapes légères.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict

import numpy as np

from .encoding import to_data_url
from .lineart import line_art
from .loader import load_image
from .mixing import mix_recipe
from .objects import object_contours
from .paintbynumber import paint_by_number
from .palette import extract_palette, to_hex
from .planes import compute_planes
from .scene import analyze_scene, extract_objects
from .segmentation import depth_map, subject_mask
from .sepia import to_sepia

_ANALYSIS_CACHE: OrderedDict[str, dict] = OrderedDict()
_ANALYSIS_CACHE_MAX = 4  # dernières images analysées (usage local, mono-utilisateur)


def _image_analysis(data: bytes, image: np.ndarray) -> dict:
    """Étapes coûteuses indépendantes des réglages, en cache LRU par image."""
    key = hashlib.sha256(data).hexdigest()
    if key in _ANALYSIS_CACHE:
        _ANALYSIS_CACHE.move_to_end(key)
        return _ANALYSIS_CACHE[key]

    mask = subject_mask(image)
    entry = {
        "mask": mask,
        "depth": depth_map(image, mask),
        "objects_img": object_contours(image),
        "scene": extract_objects(image),
    }
    _ANALYSIS_CACHE[key] = entry
    while len(_ANALYSIS_CACHE) > _ANALYSIS_CACHE_MAX:
        _ANALYSIS_CACHE.popitem(last=False)
    return entry


def run(
    data: bytes, num_colors: int = 12, num_planes: int = 4, detail: int = 50
) -> dict:
    """Exécute le pipeline complet et renvoie le dict de réponse de l'API."""
    image = load_image(data)

    analysis = _image_analysis(data, image)
    mask, depth = analysis["mask"], analysis["depth"]

    lineart_img = line_art(image, mask=mask, detail=detail)
    sepia_img = to_sepia(image)
    objects_img = analysis["objects_img"]
    scene_img, scene_caption, scene_objects = analyze_scene(
        image, depth, num_planes, extracted=analysis["scene"]
    )
    palette = extract_palette(image, num_colors)
    planes_img, planes_meta = compute_planes(image, depth, palette, num_planes)
    pbn_img = paint_by_number(palette)

    palette_list = []
    for i in range(palette.centers.shape[0]):
        center = palette.centers[i]
        palette_list.append(
            {
                "index": i + 1,
                "hex": to_hex(center),
                "pct": round(float(palette.pct[i]), 1),
                "recipe": mix_recipe(center.astype(np.float32)),
            }
        )

    return {
        "lineart": to_data_url(lineart_img),
        "sepia": to_data_url(sepia_img),
        "objectContours": to_data_url(objects_img),
        "objectPlanes": to_data_url(scene_img),
        "sceneDescription": scene_caption,
        "sceneObjects": scene_objects,
        "planesMap": to_data_url(planes_img),
        "paintByNumber": to_data_url(pbn_img),
        "palette": palette_list,
        "planes": planes_meta,
    }
