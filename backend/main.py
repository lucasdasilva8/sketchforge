from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
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
    _maybe_bootstrap_model()


def _maybe_bootstrap_model() -> None:
    """Ensure a checkpoint exists on Render/production deploys."""
    if os.getenv("SKIP_MODEL_BOOTSTRAP", "").lower() in {"1", "true", "yes"}:
        return
    ml_dir = Path(__file__).resolve().parent.parent / "ml"
    checkpoint = ml_dir / "checkpoints" / "sketch_cad.pt"
    if checkpoint.exists():
        return
    try:
        if str(ml_dir) not in sys.path:
            sys.path.insert(0, str(ml_dir))
        if str(Path(__file__).resolve().parent) not in sys.path:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
        from dataset.generate_synthetic import generate_dataset
        from train import train

        print("No ML checkpoint found — running bootstrap training...")
        generate_dataset(800, ml_dir / "data" / "synthetic")
        train(epochs=5, batch_size=16, synthetic_count=800, pretrained=True)
        from pipelines.convert import reload_predictor

        reload_predictor()
        print("Bootstrap training complete.")
    except Exception as exc:
        print(f"Bootstrap training skipped: {exc}")


@app.get("/health")
def health() -> dict:
    from pipelines.convert import _predictor

    chair_supported = True
    try:
        from pipelines.sketch_parser import chair_score as _chair_score  # noqa: F401
    except Exception:
        chair_supported = False

    return {
        "status": "ok",
        "service": "sketchforge",
        "chair_detection": chair_supported,
        "ml_ready": _predictor is not None and _predictor.is_ready(),
    }


@app.get("/ml/status")
def ml_status() -> dict:
    try:
        ml_dir = Path(__file__).resolve().parent.parent / "ml"
        if str(ml_dir) not in sys.path:
            sys.path.insert(0, str(ml_dir))
        from auto_retrain import get_status

        return get_status()
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}


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
    template_hint: str = Form("auto"),
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

    hint = None if template_hint in {"", "auto"} else template_hint
    try:
        spec = convert_sketch(content, reference_dimension, reference_axis, use_ml, hint)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    version = add_version(project_id, spec)
    message = f"Detected {spec.template} (confidence {(spec.confidence * 100):.0f}%)"
    if spec.confidence < 0.5:
        message += " — low confidence; adjust parameters or pick a shape type."
    if spec.template == "box":
        message += " For chair sketches, choose “Chair / furniture” in Shape type."

    return ConvertResponse(
        project_id=project_id,
        version=version,
        cad_spec=spec,
        message=message,
    )


@app.post("/projects/{project_id}/refine", response_model=RefineResponse)
def refine_route(project_id: str, body: RefineRequest, background_tasks: BackgroundTasks) -> RefineResponse:
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

    def _schedule_retrain() -> None:
        try:
            ml_dir = Path(__file__).resolve().parent.parent / "ml"
            if str(ml_dir) not in sys.path:
                sys.path.insert(0, str(ml_dir))
            from auto_retrain import notify_feedback_saved

            notify_feedback_saved()
        except Exception as exc:
            print(f"Auto-retrain scheduling failed: {exc}")

    background_tasks.add_task(_schedule_retrain)

    return RefineResponse(
        project_id=project_id,
        version=version,
        cad_spec=updated,
        applied_changes=changes,
    )
