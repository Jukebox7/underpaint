"""Orchestrateur : enchaîne les étapes et assemble la réponse."""

from __future__ import annotations

import numpy as np

from .encoding import to_data_url
from .lineart import line_art
from .loader import load_image
from .mixing import mix_recipe
from .objects import object_contours
from .paintbynumber import paint_by_number
from .palette import extract_palette, to_hex
from .planes import compute_planes
from .scene import analyze_scene
from .segmentation import depth_map, subject_mask
from .sepia import to_sepia


def run(
    data: bytes, num_colors: int = 12, num_planes: int = 4, detail: int = 50
) -> dict:
    """Exécute le pipeline complet et renvoie le dict de réponse de l'API."""
    image = load_image(data)

    mask = subject_mask(image)
    depth = depth_map(image, mask)

    lineart_img = line_art(image, mask=mask, detail=detail)
    sepia_img = to_sepia(image)
    objects_img = object_contours(image)
    scene_img, scene_caption, scene_objects = analyze_scene(image, depth, num_planes)
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
