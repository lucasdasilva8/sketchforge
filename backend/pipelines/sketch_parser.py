from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

from models import CADSpec, ExtrudeOp, FilletOp, SketchDef

TemplateType = Literal["box", "cylinder", "profile_extrude", "bracket", "chair"]
AxisType = Literal["width", "depth", "height", "radius"]


@dataclass
class SketchAnalysis:
    template: TemplateType
    confidence: float
    aspect_ratio: float
    circularity: float
    contour_area_ratio: float
    bbox_width_px: float
    bbox_height_px: float
    profile_points: list[list[float]]


def _load_grayscale(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Could not decode image. Upload a JPG or PNG sketch.")
    return img


def _preprocess(img: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed


def _normalize_profile(points: np.ndarray, size: float = 100.0) -> list[list[float]]:
    pts = points.reshape(-1, 2).astype(float)
    min_xy = pts.min(axis=0)
    max_xy = pts.max(axis=0)
    span = max(max_xy - min_xy)
    if span <= 0:
        return [[0, 0], [size, 0], [size, size], [0, size]]
    scale = size / span
    normalized = (pts - min_xy) * scale
    simplified: list[list[float]] = []
    step = max(1, len(normalized) // 12)
    for i in range(0, len(normalized), step):
        x, y = normalized[i]
        simplified.append([round(float(x), 2), round(float(y), 2)])
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    return simplified


def _chair_likelihood(gray: np.ndarray, processed: np.ndarray) -> float:
    h, w = gray.shape[:2]
    contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    significant = [c for c in contours if cv2.contourArea(c) > 0.008 * h * w]
    if len(significant) >= 3:
        return 0.72

    lines = cv2.HoughLinesP(processed, 1, np.pi / 180, threshold=45, minLineLength=max(25, w // 12), maxLineGap=12)
    if lines is None:
        return 0.0

    vertical = 0
    horizontal = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        if dy > dx * 1.8:
            vertical += 1
        elif dx > dy * 1.8:
            horizontal += 1

    tall = h >= w * 0.85
    if vertical >= 2 and horizontal >= 1 and tall:
        return 0.78
    if vertical >= 3 and tall:
        return 0.68
    return 0.0


def analyze_sketch(image_bytes: bytes) -> SketchAnalysis:
    gray = _load_grayscale(image_bytes)
    processed = _preprocess(gray)
    contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return SketchAnalysis(
            template="box",
            confidence=0.25,
            aspect_ratio=1.0,
            circularity=0.0,
            contour_area_ratio=0.0,
            bbox_width_px=float(gray.shape[1]),
            bbox_height_px=float(gray.shape[0]),
            profile_points=[[0, 0], [100, 0], [100, 60], [0, 60]],
        )

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    circularity = 4 * np.pi * area / (perimeter * perimeter + 1e-6)
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = w / max(h, 1)
    image_area = gray.shape[0] * gray.shape[1]
    contour_area_ratio = area / max(image_area, 1)

    approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
    vertex_count = len(approx)
    profile_points = _normalize_profile(approx)

    chair_score = _chair_likelihood(gray, processed)

    template: TemplateType = "box"
    confidence = 0.55

    if chair_score >= 0.65:
        template = "chair"
        confidence = chair_score
    elif circularity > 0.72:
        template = "cylinder"
        confidence = min(0.92, 0.55 + circularity * 0.4)
    elif vertex_count >= 6 and aspect_ratio > 1.2 and contour_area_ratio < 0.35:
        template = "bracket"
        confidence = 0.62
    elif vertex_count >= 5 and circularity < 0.55:
        template = "profile_extrude"
        confidence = 0.58
    else:
        template = "box"
        confidence = min(0.85, 0.45 + (1 - abs(aspect_ratio - 1.0)) * 0.25 + contour_area_ratio)

    return SketchAnalysis(
        template=template,
        confidence=confidence,
        aspect_ratio=float(aspect_ratio),
        circularity=float(circularity),
        contour_area_ratio=float(contour_area_ratio),
        bbox_width_px=float(w),
        bbox_height_px=float(h),
        profile_points=profile_points,
    )


def _scale_from_reference(
    analysis: SketchAnalysis,
    reference_dimension: float,
    reference_axis: AxisType,
) -> float:
    if reference_axis == "width":
        px = analysis.bbox_width_px
    elif reference_axis == "depth":
        px = analysis.bbox_height_px
    elif reference_axis == "height":
        px = analysis.bbox_height_px
    else:
        px = min(analysis.bbox_width_px, analysis.bbox_height_px)
    return reference_dimension / max(px, 1.0)


def _build_box_spec(width: float, depth: float, height: float, fillet: float, confidence: float) -> CADSpec:
    return CADSpec(
        template="box",
        sketches=[
            SketchDef(
                id="base",
                plane="XY",
                profile=[[0, 0], [width, 0], [width, depth], [0, depth]],
            )
        ],
        operations=[
            ExtrudeOp(sketch="base", distance=height),
            FilletOp(edges=["top"], radius=fillet),
        ],
        parameters={
            "width": round(width, 2),
            "depth": round(depth, 2),
            "height": round(height, 2),
            "fillet_radius": round(fillet, 2),
        },
        confidence=confidence,
        source="heuristic",
    )


def _build_cylinder_spec(radius: float, height: float, confidence: float) -> CADSpec:
    d = radius * 2
    return CADSpec(
        template="cylinder",
        sketches=[
            SketchDef(
                id="base",
                plane="XY",
                profile=[
                    [radius, 0],
                    [0, radius],
                    [-radius, 0],
                    [0, -radius],
                    [radius, 0],
                ],
            )
        ],
        operations=[ExtrudeOp(sketch="base", distance=height)],
        parameters={
            "radius": round(radius, 2),
            "width": round(d, 2),
            "depth": round(d, 2),
            "height": round(height, 2),
            "fillet_radius": 0,
        },
        confidence=confidence,
        source="heuristic",
    )


def _build_profile_spec(
    profile: list[list[float]],
    height: float,
    confidence: float,
) -> CADSpec:
    return CADSpec(
        template="profile_extrude",
        sketches=[SketchDef(id="profile", plane="XY", profile=profile)],
        operations=[ExtrudeOp(sketch="profile", distance=height)],
        parameters={
            "height": round(height, 2),
            "fillet_radius": 0,
        },
        confidence=confidence,
        source="heuristic",
    )


def _build_bracket_spec(
    width: float,
    depth: float,
    height: float,
    wall: float,
    confidence: float,
) -> CADSpec:
    inner_w = max(width - wall, wall)
    inner_d = max(depth - wall, wall)
    profile = [
        [0, 0],
        [width, 0],
        [width, wall],
        [wall, wall],
        [wall, depth],
        [0, depth],
        [0, 0],
    ]
    return CADSpec(
        template="bracket",
        sketches=[SketchDef(id="bracket_profile", plane="XY", profile=profile)],
        operations=[
            ExtrudeOp(sketch="bracket_profile", distance=height),
            FilletOp(edges=["outer"], radius=min(wall * 0.4, 3)),
        ],
        parameters={
            "width": round(width, 2),
            "depth": round(depth, 2),
            "height": round(height, 2),
            "wall_thickness": round(wall, 2),
            "leg_width": round(inner_w, 2),
            "fillet_radius": round(min(wall * 0.4, 3), 2),
        },
        confidence=confidence,
        source="heuristic",
    )


def _build_chair_spec(
    seat_width: float,
    seat_depth: float,
    leg_height: float,
    leg_width: float,
    seat_thickness: float,
    confidence: float,
) -> CADSpec:
    profile = [
        [0, 0],
        [seat_width, 0],
        [seat_width, seat_depth],
        [0, seat_depth],
    ]
    return CADSpec(
        template="chair",
        sketches=[SketchDef(id="seat", plane="XY", profile=profile)],
        operations=[
            ExtrudeOp(sketch="seat", distance=seat_thickness),
        ],
        parameters={
            "width": round(seat_width, 2),
            "depth": round(seat_depth, 2),
            "height": round(leg_height, 2),
            "leg_width": round(leg_width, 2),
            "seat_thickness": round(seat_thickness, 2),
            "fillet_radius": 0,
            "wall_thickness": round(leg_width, 2),
        },
        confidence=confidence,
        source="heuristic",
    )


def sketch_to_cad_spec(
    image_bytes: bytes,
    reference_dimension: float,
    reference_axis: AxisType = "width",
) -> CADSpec:
    analysis = analyze_sketch(image_bytes)
    scale = _scale_from_reference(analysis, reference_dimension, reference_axis)

    width = analysis.bbox_width_px * scale
    depth = analysis.bbox_height_px * scale
    height = min(width, depth) * 0.6
    fillet = min(width, depth) * 0.05
    radius = min(analysis.bbox_width_px, analysis.bbox_height_px) * scale / 2
    wall = max(min(width, depth) * 0.15, 2.0)

    seat_thickness = max(min(width, depth) * 0.08, 3.0)
    leg_width = max(min(width, depth) * 0.12, 4.0)
    leg_height = max(height * 1.4, seat_thickness * 2)

    if analysis.template == "chair":
        return _build_chair_spec(width, depth, leg_height, leg_width, seat_thickness, analysis.confidence)
    if analysis.template == "cylinder":
        return _build_cylinder_spec(radius, height, analysis.confidence)
    if analysis.template == "profile_extrude":
        scaled_profile = [
            [round(p[0] * scale / 100.0 * analysis.bbox_width_px, 2), round(p[1] * scale / 100.0 * analysis.bbox_height_px, 2)]
            for p in analysis.profile_points[:-1]
        ]
        return _build_profile_spec(scaled_profile, height, analysis.confidence)
    if analysis.template == "bracket":
        return _build_bracket_spec(width, depth, height, wall, analysis.confidence)
    return _build_box_spec(width, depth, height, fillet, analysis.confidence)
