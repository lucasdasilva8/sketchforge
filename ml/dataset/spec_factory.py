"""Generate random CADSpec examples for synthetic training data."""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models import CADSpec, ExtrudeOp, FilletOp, SketchDef

TemplateName = str


def _rand(a: float, b: float) -> float:
    return round(random.uniform(a, b), 2)


def random_box_spec() -> CADSpec:
    width, depth, height = _rand(40, 160), _rand(30, 120), _rand(20, 100)
    fillet = _rand(0, min(width, depth) * 0.08)
    return CADSpec(
        template="box",
        sketches=[SketchDef(id="base", plane="XY", profile=[[0, 0], [width, 0], [width, depth], [0, depth]])],
        operations=[ExtrudeOp(sketch="base", distance=height), FilletOp(edges=["top"], radius=fillet)],
        parameters={"width": width, "depth": depth, "height": height, "fillet_radius": fillet},
        confidence=1.0,
        source="heuristic",
    )


def random_cylinder_spec() -> CADSpec:
    radius, height = _rand(15, 70), _rand(20, 120)
    d = radius * 2
    return CADSpec(
        template="cylinder",
        sketches=[SketchDef(id="base", plane="XY", profile=[
            [radius, 0], [0, radius], [-radius, 0], [0, -radius], [radius, 0]
        ])],
        operations=[ExtrudeOp(sketch="base", distance=height)],
        parameters={"radius": radius, "width": d, "depth": d, "height": height, "fillet_radius": 0},
        confidence=1.0,
        source="heuristic",
    )


def random_bracket_spec() -> CADSpec:
    width, depth, height = _rand(60, 180), _rand(40, 140), _rand(15, 80)
    wall = _rand(6, min(width, depth) * 0.25)
    fillet = _rand(0, wall * 0.5)
    profile = [[0, 0], [width, 0], [width, wall], [wall, wall], [wall, depth], [0, depth], [0, 0]]
    return CADSpec(
        template="bracket",
        sketches=[SketchDef(id="bracket_profile", plane="XY", profile=profile)],
        operations=[ExtrudeOp(sketch="bracket_profile", distance=height), FilletOp(edges=["outer"], radius=fillet)],
        parameters={
            "width": width,
            "depth": depth,
            "height": height,
            "wall_thickness": wall,
            "fillet_radius": fillet,
            "leg_width": max(width - wall, wall),
        },
        confidence=1.0,
        source="heuristic",
    )


def random_profile_spec() -> CADSpec:
    width, depth, height = _rand(50, 150), _rand(40, 120), _rand(20, 90)
    profile = [
        [0, 0],
        [width * 0.55, 0],
        [width, depth * 0.35],
        [width * 0.75, depth],
        [width * 0.2, depth],
        [0, depth * 0.65],
    ]
    return CADSpec(
        template="profile_extrude",
        sketches=[SketchDef(id="profile", plane="XY", profile=profile)],
        operations=[ExtrudeOp(sketch="profile", distance=height)],
        parameters={"width": width, "depth": depth, "height": height, "fillet_radius": 0},
        confidence=1.0,
        source="heuristic",
    )


def random_chair_spec() -> CADSpec:
    seat_w, seat_d = _rand(50, 140), _rand(40, 100)
    leg_h, leg_w = _rand(35, 90), _rand(4, 14)
    seat_t = _rand(3, 10)
    profile = [[0, 0], [seat_w, 0], [seat_w, seat_d], [0, seat_d]]
    return CADSpec(
        template="chair",
        sketches=[SketchDef(id="seat", plane="XY", profile=profile)],
        operations=[ExtrudeOp(sketch="seat", distance=seat_t)],
        parameters={
            "width": seat_w,
            "depth": seat_d,
            "height": leg_h,
            "leg_width": leg_w,
            "seat_thickness": seat_t,
            "wall_thickness": leg_w,
            "fillet_radius": 0,
            "radius": seat_t,
        },
        confidence=1.0,
        source="heuristic",
    )


GENERATORS = {
    "box": random_box_spec,
    "cylinder": random_cylinder_spec,
    "bracket": random_bracket_spec,
    "profile_extrude": random_profile_spec,
    "chair": random_chair_spec,
}


def random_spec(template: TemplateName | None = None) -> CADSpec:
    name = template or random.choice(list(GENERATORS.keys()))
    return GENERATORS[name]()
