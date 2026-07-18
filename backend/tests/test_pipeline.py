"""Tests du pipeline sur des images synthétiques (sans accès réseau)."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.pipeline import runner
from app.pipeline.lineart import line_art
from app.pipeline.loader import load_image
from app.pipeline.mixing import mix_recipe
from app.pipeline.objects import object_contours
from app.pipeline.paintbynumber import paint_by_number
from app.pipeline.palette import extract_palette
from app.pipeline.planes import compute_planes
from app.pipeline.scene import analyze_scene
from app.pipeline.segmentation import depth_map
from app.pipeline.sepia import to_sepia


def _synthetic_png() -> bytes:
    """Image 128x96 à deux bandes de couleur + un carré, encodée en PNG."""
    arr = np.zeros((96, 128, 3), dtype=np.uint8)
    arr[:48, :] = (40, 90, 160)  # ciel
    arr[48:, :] = (60, 140, 70)  # herbe
    arr[60:90, 40:90] = (200, 60, 50)  # objet rouge
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def test_loader_resizes_and_rgb():
    img = load_image(_synthetic_png(), max_size=64)
    assert img.ndim == 3 and img.shape[2] == 3
    assert max(img.shape[:2]) <= 64
    assert img.dtype == np.uint8


def test_lineart_is_white_dominant():
    img = load_image(_synthetic_png())
    lines = line_art(img)
    assert lines.shape == img.shape
    # Un dessin au trait est majoritairement blanc.
    assert float((lines > 200).mean()) > 0.5


def test_lineart_suppresses_texture_noise():
    # Fond texturé bruité + grande forme : le trait doit rester épuré.
    rng = np.random.default_rng(0)
    arr = rng.integers(90, 165, size=(200, 260, 3), dtype=np.uint8)  # bruit
    arr[60:150, 80:180] = (210, 210, 210)  # grande forme nette
    lines = line_art(arr, detail=30)
    ink_ratio = float((lines < 100).mean())
    # Le bruit ne doit pas couvrir l'image (sinon décalque inexploitable).
    assert ink_ratio < 0.15


def test_palette_sorted_and_covers():
    img = load_image(_synthetic_png())
    pal = extract_palette(img, num_colors=6)
    assert pal.centers.shape[1] == 3
    assert pal.labels.shape == img.shape[:2]
    # Tri par surface décroissante.
    assert np.all(np.diff(pal.pct) <= 1e-3)
    assert abs(pal.pct.sum() - 100.0) < 1.0


def test_planes_ordered_with_base_colors():
    img = load_image(_synthetic_png())
    depth = depth_map(img, mask=None)
    pal = extract_palette(img, num_colors=6)
    planes_img, meta = compute_planes(img, depth, pal, num_planes=3)
    assert planes_img.shape == img.shape
    orders = [p["order"] for p in meta]
    assert orders == sorted(orders)
    assert orders == list(range(1, len(meta) + 1))  # ordre contigu fond→avant
    for p in meta:
        assert p["baseColor"].startswith("#") and len(p["baseColor"]) == 7
        assert 1 <= p["baseColorIndex"] <= pal.centers.shape[0]


def test_paint_by_number_shape():
    img = load_image(_synthetic_png())
    pal = extract_palette(img, num_colors=6)
    pbn = paint_by_number(pal)
    assert pbn.shape == img.shape


def test_object_contours_fallback():
    # PAINTING_NO_SAM=1 (conftest) → repli régions felzenszwalb.
    img = load_image(_synthetic_png())
    out = object_contours(img)
    assert out.shape == img.shape
    # Trait foncé sur fond blanc : majoritairement blanc, mais des contours présents.
    assert float((out > 200).mean()) > 0.5
    assert float((out < 100).any())


def test_sepia_tone():
    img = load_image(_synthetic_png())
    out = to_sepia(img)
    assert out.shape == img.shape and out.dtype == np.uint8
    # Le sépia est chaud : en moyenne, canal rouge > canal bleu.
    assert out[:, :, 0].mean() > out[:, :, 2].mean()


def test_scene_fallback():
    # PAINTING_NO_VLM=1 (conftest) → repli masques + labels génériques + plans.
    img = load_image(_synthetic_png())
    depth = depth_map(img, mask=None)
    canvas, caption, objs = analyze_scene(img, depth, num_planes=3)
    assert canvas.shape == img.shape
    assert isinstance(caption, str)
    for o in objs:
        assert o["plane"] >= 1
        assert o["baseColor"].startswith("#")
        assert o["label"]


def test_mix_recipe_structure():
    recipe = mix_recipe(np.array([60, 140, 70], dtype=np.float32))
    assert recipe["parts"] and "deltaE" in recipe
    assert all("primary" in p and "parts" in p for p in recipe["parts"])
    assert recipe["deltaE"] >= 0


def _fake_mask(image):
    """Masque synthétique : évite le téléchargement du modèle rembg."""
    h, w = image.shape[:2]
    m = np.zeros((h, w), dtype=bool)
    m[h // 2 :, :] = True
    return m


def test_full_run_without_network(monkeypatch):
    monkeypatch.setattr(runner, "subject_mask", _fake_mask)
    runner._ANALYSIS_CACHE.clear()
    out = runner.run(_synthetic_png(), num_colors=6, num_planes=3)
    for key in ("lineart", "sepia", "objectContours", "objectPlanes", "planesMap", "paintByNumber"):
        assert out[key].startswith("data:image/png;base64,")
    assert "sceneObjects" in out and isinstance(out["sceneDescription"], str)
    assert len(out["palette"]) >= 2
    assert out["palette"][0]["recipe"]["parts"]
    assert out["planes"][0]["order"] == 1


def test_run_caches_costly_analysis(monkeypatch):
    # Rejouer le pipeline sur la même image avec d'autres réglages ne doit pas
    # recalculer les étapes coûteuses (détourage, profondeur, segmentation).
    calls = {"mask": 0}

    def counting_mask(image):
        calls["mask"] += 1
        return _fake_mask(image)

    monkeypatch.setattr(runner, "subject_mask", counting_mask)
    runner._ANALYSIS_CACHE.clear()
    data = _synthetic_png()
    first = runner.run(data, num_colors=4, num_planes=3, detail=30)
    second = runner.run(data, num_colors=8, num_planes=2, detail=80)
    assert calls["mask"] == 1
    assert len(first["palette"]) != len(second["palette"])
