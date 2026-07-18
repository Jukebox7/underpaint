"""API FastAPI : santé + traitement d'image."""

from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .pipeline.runner import run
from .schemas import HealthResponse, ProcessResponse

app = FastAPI(title="painting", version="0.1.0")

# Le front (Vite) appelle en local ; on autorise localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/process", response_model=ProcessResponse)
def process(
    image: UploadFile = File(...),
    num_colors: int = Form(12),
    num_planes: int = Form(4),
    detail: int = Form(50),
) -> ProcessResponse:
    if not 2 <= num_colors <= 24:
        raise HTTPException(422, "num_colors doit être entre 2 et 24")
    if not 2 <= num_planes <= 8:
        raise HTTPException(422, "num_planes doit être entre 2 et 8")
    if not 0 <= detail <= 100:
        raise HTTPException(422, "detail doit être entre 0 et 100")

    data = image.file.read()
    if not data:
        raise HTTPException(400, "Fichier image manquant ou vide")

    try:
        result = run(
            data, num_colors=num_colors, num_planes=num_planes, detail=detail
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Erreur du pipeline : {exc}") from exc

    return ProcessResponse(**result)
