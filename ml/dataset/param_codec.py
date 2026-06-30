"""Shared parameter encoding between training and inference."""

from __future__ import annotations

from typing import Dict, List

TEMPLATE_IDS = ["box", "cylinder", "profile_extrude", "bracket"]
TEMPLATE_TO_IDX = {name: idx for idx, name in enumerate(TEMPLATE_IDS)}
IDX_TO_TEMPLATE = {idx: name for name, idx in TEMPLATE_TO_IDX.items()}

PARAM_KEYS = ["width", "depth", "height", "radius", "fillet_radius", "wall_thickness"]
PARAM_SCALES = {
    "width": 100.0,
    "depth": 80.0,
    "height": 60.0,
    "radius": 40.0,
    "fillet_radius": 5.0,
    "wall_thickness": 10.0,
}


def encode_params(parameters: Dict[str, float]) -> List[float]:
    encoded: List[float] = []
    for key in PARAM_KEYS:
        scale = PARAM_SCALES[key]
        value = float(parameters.get(key, scale * 0.5))
        if key == "fillet_radius":
            encoded.append(value / scale)
        else:
            encoded.append(value / scale - 0.5)
    return encoded


def decode_params(raw: List[float]) -> Dict[str, float]:
    decoded: Dict[str, float] = {}
    for key, value in zip(PARAM_KEYS, raw):
        scale = PARAM_SCALES[key]
        if key == "fillet_radius":
            decoded[key] = max(value * scale, 0.0)
        else:
            decoded[key] = max((value + 0.5) * scale, 0.1)
    return decoded
