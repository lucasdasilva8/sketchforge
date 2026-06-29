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


def convert_sketch(
    image_bytes: bytes,
    reference_dimension: float,
    reference_axis: str = "width",
    use_ml: bool = True,
) -> CADSpec:
    if use_ml and _predictor is not None and _predictor.is_ready():
        spec = _predictor.predict(image_bytes, reference_dimension, reference_axis)
        if spec.confidence >= 0.4:
            return spec

    return sketch_to_cad_spec(image_bytes, reference_dimension, reference_axis)  # type: ignore[arg-type]


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
