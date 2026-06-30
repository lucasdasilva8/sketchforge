from __future__ import annotations

from typing import Literal

import cv2
import numpy as np

FurnitureStyle = Literal["ladder_back", "dining", "stool", "armchair", "bench"]

STYLE_LABELS: dict[FurnitureStyle, str] = {
    "ladder_back": "ladder-back chair",
    "dining": "dining chair",
    "stool": "stool",
    "armchair": "armchair",
    "bench": "bench",
}

VALID_STYLES = set(STYLE_LABELS.keys())


def _count_lines(edge_img: np.ndarray) -> tuple[int, int]:
    h, w = edge_img.shape[:2]
    lines = cv2.HoughLinesP(
        edge_img,
        1,
        np.pi / 180,
        threshold=30,
        minLineLength=max(18, min(h, w) // 12),
        maxLineGap=14,
    )
    if lines is None:
        return 0, 0
    vertical = 0
    horizontal = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        if dy > dx * 1.35:
            vertical += 1
        elif dx > dy * 1.35:
            horizontal += 1
    return vertical, horizontal


def detect_furniture_style(image_bytes: bytes) -> tuple[FurnitureStyle, float]:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return "dining", 0.4

    h, w = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 45, 130)
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return "dining", 0.35

    main = max(contours, key=cv2.contourArea)
    _, _, cw, ch = cv2.boundingRect(main)
    aspect = cw / max(ch, 1)
    silhouette_tall = ch > cw * 1.08
    silhouette_short = ch <= cw * 1.12

    upper = closed[: max(h // 3, 1), :]
    mid = closed[h // 3 : 2 * h // 3, :]
    upper_v, upper_h = _count_lines(upper)
    mid_v, mid_h = _count_lines(mid)
    all_v, all_h = _count_lines(closed)

    scores: dict[FurnitureStyle, float] = {}

    # Very wide sketch → bench
    if aspect >= 1.85:
        scores["bench"] = min(0.62 + (aspect - 1.85) * 0.15, 0.88)
    elif aspect >= 1.45 and all_h >= 2:
        scores["bench"] = 0.58

    # Short silhouette, little upper structure → stool
    if silhouette_short and upper_h <= 1 and upper_v <= 2:
        scores["stool"] = 0.72
    elif silhouette_short:
        scores["stool"] = 0.55

    # Multiple horizontals in upper third + tall → ladder-back
    if silhouette_tall and upper_h >= 2 and upper_v >= 1:
        scores["ladder_back"] = 0.65 + min(upper_h * 0.06, 0.2)
    elif silhouette_tall and upper_h >= 1:
        scores["ladder_back"] = 0.52

    # Wide + mid-band horizontals (arms) → armchair
    if aspect >= 0.82 and mid_h >= 2 and silhouette_tall:
        scores["armchair"] = 0.6 + min(mid_h * 0.05, 0.2)
    elif aspect >= 0.95 and cw > w * 0.45 and mid_h >= 1:
        scores["armchair"] = 0.55

    # Default side chair with back
    if silhouette_tall and all_v >= 2:
        scores["dining"] = 0.58

    if not scores:
        return "dining", 0.45

    style = max(scores, key=scores.get)  # type: ignore[arg-type]
    return style, scores[style]


def parse_style_hint(hint: str | None) -> FurnitureStyle | None:
    if not hint or hint in {"", "auto"}:
        return None
    normalized = hint.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "ladderback": "ladder_back",
        "ladder": "ladder_back",
        "dining_chair": "dining",
        "chair": "dining",
        "arm": "armchair",
        "arm_chair": "armchair",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in VALID_STYLES:
        return normalized  # type: ignore[return-value]
    return None
