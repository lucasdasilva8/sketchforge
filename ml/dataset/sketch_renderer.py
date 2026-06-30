"""Render pencil-style sketch images from CADSpec templates."""

from __future__ import annotations

import random
from typing import List, Tuple

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
    else:
        profile = spec.sketches[0].profile
        _draw_profile(canvas, profile, thickness)

    return _pencil_effect(canvas)
