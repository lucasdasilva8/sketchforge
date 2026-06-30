from __future__ import annotations

import sys
from pathlib import Path

from models import CADSpec
from pipelines.feedback_parser import apply_feedback
from pipelines.sketch_parser import sketch_to_cad_spec

ML_DIR = Path(__file__).resolve().parent.parent.parent / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

try:
    from inference.predictor import SketchCADPredictor

    _predictor: SketchCADPredictor | None = SketchCADPredictor.try_load()
except Exception:
    _predictor = None


def reload_predictor() -> bool:
    """Reload ML weights after auto-retrain."""
    global _predictor
    try:
        from inference.predictor import SketchCADPredictor

        loaded = SketchCADPredictor.try_load()
        if loaded is not None and loaded.is_ready():
            _predictor = loaded
            return True
    except Exception:
        pass
    return False


def convert_sketch(
    image_bytes: bytes,
    reference_dimension: float,
    reference_axis: str = "width",
    use_ml: bool = True,
) -> CADSpec:
    heuristic = sketch_to_cad_spec(image_bytes, reference_dimension, reference_axis)  # type: ignore[arg-type]

    # Prefer furniture/heuristic when it is more confident than ML box guesses
    if heuristic.template == "chair" and heuristic.confidence >= 0.55:
        return heuristic

    if use_ml and _predictor is not None and _predictor.is_ready():
        ml_spec = _predictor.predict(image_bytes, reference_dimension, reference_axis)
        if heuristic.confidence > ml_spec.confidence:
            return heuristic
        if ml_spec.confidence >= 0.4:
            return ml_spec

    return heuristic


def refine_spec(
    spec: CADSpec,
    feedback: str,
    image_bytes: bytes | None = None,
    use_ml: bool = True,
) -> tuple[CADSpec, list[str]]:
    if use_ml and _predictor is not None and _predictor.is_ready() and image_bytes:
        refined = _predictor.refine(image_bytes, spec, feedback)
        if refined is not None:
            changes = [f"ML refinement applied: {feedback[:80]}"]
            return refined, changes

    return apply_feedback(spec, feedback)
