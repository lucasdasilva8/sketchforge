from __future__ import annotations

import copy
import re

from models import CADSpec, ExtrudeOp, FilletOp


DIMENSION_ALIASES = {
    "width": ["width", "wide", "wider", "broad", "broaden"],
    "depth": ["depth", "deep", "deeper", "long", "longer", "length"],
    "height": ["height", "tall", "taller", "short", "shorter", "high", "higher", "low", "lower"],
    "radius": ["radius", "round", "rounder", "diameter", "thick", "thicker", "thin", "thinner"],
    "fillet_radius": ["fillet", "corner", "corners", "round the corners", "smooth", "smoother"],
    "wall_thickness": ["wall", "walls", "thickness"],
    "leg_width": ["leg", "legs", "leg width"],
    "seat_thickness": ["seat", "seat thickness", "cushion"],
    "back_height": ["back", "backrest", "back height", "taller back"],
}


def _detect_dimension(text: str) -> str | None:
    lower = text.lower()
    for dim, aliases in DIMENSION_ALIASES.items():
        if any(alias in lower for alias in aliases):
            return dim
    return None


def _detect_direction(text: str) -> float:
    lower = text.lower()
    increase_words = ["more", "increase", "bigger", "larger", "wider", "taller", "deeper", "thicker", "rounder", "add"]
    decrease_words = ["less", "decrease", "smaller", "narrower", "shorter", "thinner", "reduce", "lower"]
    if any(w in lower for w in decrease_words):
        return -1.0
    if any(w in lower for w in increase_words):
        return 1.0
    return 1.0


def _extract_numeric_override(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm|cm|in)?", text.lower())
    if match:
        return float(match.group(1))
    return None


def _apply_delta(params: dict[str, float], dim: str, direction: float, override: float | None) -> tuple[dict[str, float], str]:
    updated = copy.deepcopy(params)
    current = updated.get(dim, 10.0)
    if override is not None:
        updated[dim] = max(0.1, override)
        return updated, f"Set {dim} to {override:.1f} mm"
    factor = 1.2 if direction > 0 else 0.85
    updated[dim] = max(0.1, round(current * factor, 2))
    verb = "Increased" if direction > 0 else "Decreased"
    return updated, f"{verb} {dim} to {updated[dim]:.1f} mm"


def _rebuild_sketches(spec: CADSpec) -> CADSpec:
    p = spec.parameters
    template = spec.template

    if template == "box":
        w, d = p.get("width", 100), p.get("depth", 50)
        spec.sketches[0].profile = [[0, 0], [w, 0], [w, d], [0, d]]
    elif template == "cylinder":
        r = p.get("radius", p.get("width", 50) / 2)
        spec.sketches[0].profile = [
            [r, 0], [0, r], [-r, 0], [0, -r], [r, 0]
        ]
        p["width"] = r * 2
        p["depth"] = r * 2
    elif template == "bracket":
        w = p.get("width", 100)
        d = p.get("depth", 60)
        wall = p.get("wall_thickness", 10)
        spec.sketches[0].profile = [
            [0, 0], [w, 0], [w, wall], [wall, wall], [wall, d], [0, d], [0, 0]
        ]

    elif template == "chair":
        w = p.get("width", 80)
        d = p.get("depth", 60)
        spec.sketches[0].profile = [[0, 0], [w, 0], [w, d], [0, d]]

    for op in spec.operations:
        if isinstance(op, ExtrudeOp) or (isinstance(op, dict) and op.get("op") == "extrude"):
            if template == "chair":
                distance = p.get("seat_thickness", 5)
            else:
                distance = p.get("height", 30)
            if isinstance(op, ExtrudeOp):
                op.distance = distance
        if isinstance(op, FilletOp) or (isinstance(op, dict) and op.get("op") == "fillet"):
            fillet = p.get("fillet_radius", 0)
            if isinstance(op, FilletOp):
                op.radius = fillet

    spec.parameters = p
    return spec


def _wants_chair_template(text: str) -> bool:
    lower = text.lower()
    return any(
        phrase in lower
        for phrase in (
            "chair",
            "furniture",
            "stool",
            "four legs",
            "add legs",
            "make it a chair",
            "this is a chair",
        )
    )


def _promote_to_chair(spec: CADSpec) -> CADSpec:
    from pipelines.sketch_parser import _build_chair_spec

    p = spec.parameters
    seat_w = p.get("width", 80)
    seat_d = p.get("depth", 60)
    if seat_d < seat_w * 0.25:
        seat_d = max(seat_w * 0.55, 25.0)
    leg_h = p.get("height", max(seat_w * 0.42, 35.0))
    leg_w = p.get("leg_width", p.get("wall_thickness", max(seat_w * 0.065, 4.0)))
    seat_t = p.get("seat_thickness", 5.0)
    back_h = p.get("back_height", leg_h * 1.85)
    spec = _build_chair_spec(seat_w, seat_d, leg_h, leg_w, seat_t, spec.confidence or 0.7, back_h)
    return spec


def apply_feedback(spec: CADSpec, feedback: str) -> tuple[CADSpec, list[str]]:
    updated = spec.model_copy(deep=True)
    updated.source = "feedback"
    changes: list[str] = []

    if _wants_chair_template(feedback) and updated.template != "chair":
        updated = _promote_to_chair(updated)
        changes.append("Switched template to chair based on feedback")

    sentences = re.split(r"[.;!\n]+", feedback)
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        dim = _detect_dimension(sentence)
        if not dim:
            continue
        direction = _detect_direction(sentence)
        override = _extract_numeric_override(sentence)
        updated.parameters, change = _apply_delta(updated.parameters, dim, direction, override)
        changes.append(change)

        if dim == "fillet_radius":
            for op in updated.operations:
                if isinstance(op, FilletOp):
                    op.radius = updated.parameters["fillet_radius"]

    if not changes:
        dim = _detect_dimension(feedback) or "height"
        direction = _detect_direction(feedback)
        override = _extract_numeric_override(feedback)
        updated.parameters, change = _apply_delta(updated.parameters, dim, direction, override)
        changes.append(change)

    updated = _rebuild_sketches(updated)
    return updated, changes
