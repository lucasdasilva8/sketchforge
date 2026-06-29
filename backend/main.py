from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from models import (
    ConvertRequest,
    ConvertResponse,
    ProjectCreate,
    ProjectResponse,
    RefineRequest,
    RefineResponse,
)
from pipelines.convert import convert_sketch, refine_spec
from store import (
    add_version,
    create_project,
    get_project,
    get_sketch_path,
    init_db,
    save_sketch,
)

app = FastAPI(
    title="SketchForge API",
    description="Convert hand sketches into editable parametric CAD models.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sketchforge"}


@app.post("/projects", response_model=ProjectResponse)
def create_project_route(body: ProjectCreate) -> ProjectResponse:
    project_id = create_project(body.name)
    return get_project(project_id)


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project_route(project_id: str) -> ProjectResponse:
    try:
        return get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/projects/{project_id}/versions")
def list_versions(project_id: str) -> dict:
    try:
        project = get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"project_id": project_id, "versions": project.versions}


@app.post("/projects/{project_id}/convert", response_model=ConvertResponse)
async def convert_route(
    project_id: str,
    file: UploadFile = File(...),
    reference_dimension: float = Form(...),
    reference_axis: str = Form("width"),
    use_ml: bool = Form(True),
) -> ConvertResponse:
    try:
        get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    ext = Path(file.filename or "sketch.png").suffix or ".png"
    save_sketch(project_id, content, ext)

    try:
        spec = convert_sketch(content, reference_dimension, reference_axis, use_ml)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    version = add_version(project_id, spec)
    message = None
    if spec.confidence < 0.5:
        message = "Low confidence — adjust parameters manually or add a reference dimension."

    return ConvertResponse(
        project_id=project_id,
        version=version,
        cad_spec=spec,
        message=message,
    )


@app.post("/projects/{project_id}/refine", response_model=RefineResponse)
def refine_route(project_id: str, body: RefineRequest) -> RefineResponse:
    try:
        project = get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not project.cad_spec:
        raise HTTPException(status_code=400, detail="Convert a sketch before refining.")

    sketch_path = get_sketch_path(project_id)
    image_bytes = Path(sketch_path).read_bytes() if sketch_path and Path(sketch_path).exists() else None

    try:
        updated, changes = refine_spec(
            project.cad_spec,
            body.feedback,
            image_bytes,
            body.use_ml,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    version = add_version(project_id, updated, feedback=body.feedback)
    return RefineResponse(
        project_id=project_id,
        version=version,
        cad_spec=updated,
        applied_changes=changes,
    )
