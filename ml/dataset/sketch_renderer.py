"""Render pencil-style sketch images from CADSpec templates."""

from __future__ import annotations

import random
from typing import Callable, List, Tuple

import cv2
import numpy as np

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models import CADSpec

CANVAS = 512
MARGIN = 48

FURNITURE_STYLES = ("ladder_back", "dining", "stool", "armchair", "bench")


def _fit_points(profile: List[List[float]]) -> List[Tuple[int, int]]:
    xs = [p[0] for p in profile]
    ys = [p[1] for p in profile]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y, 1.0)
    scale = (CANVAS - 2 * MARGIN) / span
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    center = CANVAS / 2
    points: List[Tuple[int, int]] = []
    for x, y in profile:
        px = int(center + (x - cx) * scale)
        py = int(center + (y - cy) * scale)
        points.append((px, py))
    return points


def _fit_chair_layout(
    seat_d: float,
    leg_h: float,
    back_h: float,
    leg_w: float,
    style: str,
) -> Tuple[float, float, float, float, Callable[[float, float], Tuple[int, int]]]:
    """Map chair side-elevation mm coords to canvas pixels. x = depth, y = height (down)."""
    if style == "bench":
        span_w = max(seat_d * 2.2, 120)
        span_h = max(back_h, leg_h + 10)
    elif style == "stool":
        span_w = max(seat_d + leg_w * 2, 50)
        span_h = max(leg_h + leg_w, 40)
    else:
        span_w = max(seat_d + leg_w, 55)
        span_h = max(back_h, leg_h + leg_w)

    scale = (CANVAS - 2 * MARGIN) / max(span_w, span_h)
    ox = (CANVAS - seat_d * scale) / 2
    oy = (CANVAS - span_h * scale) / 2

    def to_px(x: float, y: float) -> Tuple[int, int]:
        return int(ox + x * scale), int(oy + y * scale)

    return span_w, span_h, scale, ox, to_px


def _draw_line(canvas: np.ndarray, p1: Tuple[float, float], p2: Tuple[float, float], to_px, thickness: int) -> None:
    a, b = to_px(*p1), to_px(*p2)
    cv2.line(canvas, a, b, (0, 0, 0), thickness, cv2.LINE_AA)


def _draw_chair_side_elevation(canvas: np.ndarray, params: dict, thickness: int) -> None:
    seat_d = float(params.get("depth", 60))
    leg_h = float(params.get("height", 45))
    leg_w = float(params.get("leg_width", params.get("wall_thickness", 8)))
    back_h = float(params.get("back_height", leg_h * 1.75))
    style = str(params.get("furniture_style", "dining"))
    if style not in FURNITURE_STYLES:
        style = "dining"

    if style == "bench":
        seat_d *= 2.0
        back_h = max(back_h, leg_h * 1.15)

    if style == "stool":
        back_h = leg_h

    _span_w, _span_h, _scale, _ox, to_px = _fit_chair_layout(seat_d, leg_h, back_h, leg_w, style)
    seat_y = leg_h
    floor_y = back_h
    rear_x = seat_d
    front_x = 0.0

    # Floor hint
    _draw_line(canvas, (-leg_w * 0.3, floor_y), (rear_x + leg_w * 0.5, floor_y), to_px, max(1, thickness - 1))

    # Front leg
    _draw_line(canvas, (front_x + leg_w * 0.35, seat_y), (front_x + leg_w * 0.35, floor_y), to_px, thickness)

    # Seat
    _draw_line(canvas, (front_x, seat_y), (rear_x, seat_y), to_px, thickness)

    if style == "stool":
        _draw_line(canvas, (rear_x - leg_w * 0.35, seat_y), (rear_x - leg_w * 0.35, floor_y), to_px, thickness)
        return

    # Rear leg / back post
    post_x = rear_x - leg_w * 0.35
    _draw_line(canvas, (post_x, seat_y), (post_x, floor_y), to_px, thickness)
    _draw_line(canvas, (post_x, 0), (post_x, floor_y), to_px, thickness)

    if style == "ladder_back":
        for frac in (0.32, 0.52, 0.72):
            y = seat_y + (back_h - seat_y) * frac
            _draw_line(canvas, (post_x - seat_d * 0.08, y), (rear_x, y), to_px, max(1, thickness - 1))
        # Apron under seat
        _draw_line(canvas, (front_x + leg_w, seat_y + leg_w * 0.35), (post_x, seat_y + leg_w * 0.35), to_px, max(1, thickness - 1))
    elif style == "dining":
        back_w = leg_w * 0.9
        _draw_line(canvas, (post_x, seat_y), (post_x, 0), to_px, thickness)
        _draw_line(canvas, (post_x - back_w, seat_y + leg_w * 0.15), (post_x - back_w, 0), to_px, thickness)
        _draw_line(canvas, (post_x - back_w, 0), (post_x, 0), to_px, thickness)
    elif style == "armchair":
        back_w = leg_w * 1.2
        _draw_line(canvas, (post_x - back_w, seat_y + leg_w * 0.1), (post_x - back_w, 0), to_px, thickness)
        _draw_line(canvas, (post_x - back_w, 0), (post_x, 0), to_px, thickness)
        arm_y = seat_y + leg_w * 0.2
        _draw_line(canvas, (front_x, arm_y), (front_x + seat_d * 0.42, arm_y), to_px, max(1, thickness - 1))
        _draw_line(canvas, (front_x, arm_y), (front_x, seat_y + leg_w * 0.55), to_px, max(1, thickness - 1))
    elif style == "bench":
        mid_x = seat_d * 0.5
        for x in (front_x + leg_w * 0.35, mid_x, rear_x - leg_w * 0.35):
            _draw_line(canvas, (x, seat_y), (x, floor_y), to_px, thickness)
        rail_y = seat_y - leg_w * 0.5
        _draw_line(canvas, (front_x + leg_w, rail_y), (rear_x - leg_w, rail_y), to_px, max(1, thickness - 1))


def _draw_profile(canvas: np.ndarray, profile: List[List[float]], thickness: int) -> None:
    points = _fit_points(profile)
    pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
    cv2.polylines(canvas, [pts], isClosed=True, color=(0, 0, 0), thickness=thickness, lineType=cv2.LINE_AA)


def _draw_cylinder(canvas: np.ndarray, radius: float, thickness: int) -> None:
    center = CANVAS // 2
    scale = (CANVAS - 2 * MARGIN) / max(radius * 2, 1)
    r = int(radius * scale)
    cv2.ellipse(canvas, (center, center), (r, r), 0, 0, 360, (0, 0, 0), thickness, cv2.LINE_AA)


def _pencil_effect(line_art: np.ndarray) -> np.ndarray:
    gray = line_art if line_art.ndim == 2 else cv2.cvtColor(line_art, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 35, 110)
    paper = np.full_like(edges, 245, dtype=np.uint8)
    sketch = paper.copy()
    sketch[edges > 0] = 40
    noise = np.random.normal(0, 6, sketch.shape).astype(np.int16)
    sketch = np.clip(sketch.astype(np.int16) + noise, 210, 255).astype(np.uint8)
    if random.random() < 0.35:
        angle = random.uniform(-12, 12)
        matrix = cv2.getRotationMatrix2D((CANVAS / 2, CANVAS / 2), angle, 1.0)
        sketch = cv2.warpAffine(sketch, matrix, (CANVAS, CANVAS), borderValue=245)
    return sketch


def render_spec_sketch(spec: CADSpec, thickness: int | None = None) -> np.ndarray:
    thickness = thickness or random.randint(2, 4)
    canvas = np.full((CANVAS, CANVAS, 3), 255, dtype=np.uint8)
    params = spec.parameters

    if spec.template == "cylinder":
        _draw_cylinder(canvas, params.get("radius", params.get("width", 50) / 2), thickness)
    elif spec.template == "chair":
        _draw_chair_side_elevation(canvas, params, thickness)
        # Occasional top-down seat outline so the model also sees plan views.
        if random.random() < 0.12:
            seat_w = params.get("width", 80)
            seat_d = params.get("depth", 60)
            seat_profile = [[0, 0], [seat_w, 0], [seat_w, seat_d], [0, seat_d]]
            _draw_profile(canvas, seat_profile, max(1, thickness - 1))
    else:
        profile = spec.sketches[0].profile
        _draw_profile(canvas, profile, thickness)

    return _pencil_effect(canvas)
