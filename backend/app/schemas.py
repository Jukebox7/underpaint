"""Modèles Pydantic d'entrée/sortie de l'API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecipePart(BaseModel):
    primary: str
    parts: int


class Recipe(BaseModel):
    parts: list[RecipePart]
    deltaE: float


class PaletteColor(BaseModel):
    index: int
    hex: str
    pct: float
    recipe: Recipe


class PlaneInfo(BaseModel):
    order: int
    baseColor: str
    baseColorIndex: int
    label: str


class SceneObject(BaseModel):
    index: int
    label: str
    plane: int
    planeLabel: str
    baseColor: str


class ProcessResponse(BaseModel):
    lineart: str = Field(description="Dessin au trait (data URL PNG)")
    sepia: str = Field(description="Image virée en sépia")
    objectContours: str = Field(description="Contours objet par objet")
    objectPlanes: str = Field(description="Objets nommés coloriés par plan")
    sceneDescription: str = Field(description="Description de la scène (VLM)")
    sceneObjects: list[SceneObject] = Field(default_factory=list)
    planesMap: str = Field(description="Carte des plans coloriés + numéros")
    paintByNumber: str = Field(description="Gabarit à zones numérotées")
    palette: list[PaletteColor]
    planes: list[PlaneInfo]


class HealthResponse(BaseModel):
    status: str
