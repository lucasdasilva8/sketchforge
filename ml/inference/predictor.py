from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import io

import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models import CADSpec, ExtrudeOp, FilletOp, SketchDef
from pipelines.sketch_parser import sketch_to_cad_spec
from pipelines.feedback_parser import apply_feedback

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "checkpoints"
CHECKPOINT_PATH = CHECKPOINT_DIR / "sketch_cad.pt"

TEMPLATE_IDS = ["box", "cylinder", "profile_extrude", "bracket"]
TEMPLATE_TO_IDX = {t: i for i, t in enumerate(TEMPLATE_IDS)}


class SketchEncoder(nn.Module):
    def __init__(self, embed_dim: int = 256) -> None:
        super().__init__()
        backbone = models.resnet18(weights=None)
        backbone.fc = nn.Linear(backbone.fc.in_features, embed_dim)
        self.backbone = backbone

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)


class CADParamHead(nn.Module):
    def __init__(self, embed_dim: int = 256) -> None:
        super().__init__()
        self.template_head = nn.Linear(embed_dim, len(TEMPLATE_IDS))
        self.param_head = nn.Linear(embed_dim, 6)
        self.confidence_head = nn.Linear(embed_dim, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.template_head(x), self.param_head(x), torch.sigmoid(self.confidence_head(x))


class SketchCADModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = SketchEncoder()
        self.head = CADParamHead()

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        emb = self.encoder(x)
        return self.head(emb)


PREPROCESS = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def params_to_spec(template: str, raw_params: list[float], confidence: float) -> CADSpec:
    width = max(abs(raw_params[0]) * 100 + 50, 10)
    depth = max(abs(raw_params[1]) * 80 + 40, 10)
    height = max(abs(raw_params[2]) * 60 + 30, 10)
    radius = max(abs(raw_params[3]) * 40 + 20, 5)
    fillet = max(abs(raw_params[4]) * 5, 0)
    wall = max(abs(raw_params[5]) * 10 + 5, 2)

    if template == "cylinder":
        return CADSpec(
            template="cylinder",
            sketches=[SketchDef(id="base", plane="XY", profile=[
                [radius, 0], [0, radius], [-radius, 0], [0, -radius], [radius, 0]
            ])],
            operations=[ExtrudeOp(sketch="base", distance=height)],
            parameters={"radius": radius, "width": radius * 2, "depth": radius * 2, "height": height, "fillet_radius": 0},
            confidence=confidence,
            source="ml",
        )
    if template == "bracket":
        profile = [[0, 0], [width, 0], [width, wall], [wall, wall], [wall, depth], [0, depth], [0, 0]]
        return CADSpec(
            template="bracket",
            sketches=[SketchDef(id="bracket_profile", plane="XY", profile=profile)],
            operations=[ExtrudeOp(sketch="bracket_profile", distance=height), FilletOp(edges=["outer"], radius=fillet)],
            parameters={"width": width, "depth": depth, "height": height, "wall_thickness": wall, "fillet_radius": fillet},
            confidence=confidence,
            source="ml",
        )
    if template == "profile_extrude":
        profile = [[0, 0], [width * 0.6, 0], [width, depth * 0.4], [width * 0.7, depth], [0, depth]]
        return CADSpec(
            template="profile_extrude",
            sketches=[SketchDef(id="profile", plane="XY", profile=profile)],
            operations=[ExtrudeOp(sketch="profile", distance=height)],
            parameters={"width": width, "depth": depth, "height": height, "fillet_radius": 0},
            confidence=confidence,
            source="ml",
        )
    return CADSpec(
        template="box",
        sketches=[SketchDef(id="base", plane="XY", profile=[[0, 0], [width, 0], [width, depth], [0, depth]])],
        operations=[ExtrudeOp(sketch="base", distance=height), FilletOp(edges=["top"], radius=fillet)],
        parameters={"width": width, "depth": depth, "height": height, "fillet_radius": fillet},
        confidence=confidence,
        source="ml",
    )


class SketchCADPredictor:
    def __init__(self, model: SketchCADModel | None = None) -> None:
        self.model = model
        self.device = torch.device("cpu")

    @classmethod
    def try_load(cls) -> SketchCADPredictor | None:
        if not CHECKPOINT_PATH.exists():
            return cls(None)
        model = SketchCADModel()
        state = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()
        return cls(model)

    def is_ready(self) -> bool:
        return self.model is not None

    def _encode(self, image_bytes: bytes) -> tuple[str, list[float], float]:
        assert self.model is not None
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = PREPROCESS(img).unsqueeze(0)
        with torch.no_grad():
            tmpl_logits, params, conf = self.model(tensor)
        template_idx = int(tmpl_logits.argmax(dim=1).item())
        template = TEMPLATE_IDS[template_idx]
        raw_params = params.squeeze(0).tolist()
        confidence = float(conf.item())
        return template, raw_params, confidence

    def predict(
        self,
        image_bytes: bytes,
        reference_dimension: float,
        reference_axis: str = "width",
    ) -> CADSpec:
        if not self.is_ready():
            return sketch_to_cad_spec(image_bytes, reference_dimension, reference_axis)  # type: ignore[arg-type]

        template, raw_params, confidence = self._encode(image_bytes)
        spec = params_to_spec(template, raw_params, confidence)

        heuristic = sketch_to_cad_spec(image_bytes, reference_dimension, reference_axis)  # type: ignore[arg-type]
        scale = reference_dimension / max(heuristic.parameters.get(reference_axis, reference_dimension), 1)
        for key in ("width", "depth", "height", "radius", "wall_thickness", "fillet_radius"):
            if key in spec.parameters and key in heuristic.parameters:
                spec.parameters[key] = round(heuristic.parameters[key], 2)

        spec = params_to_spec(spec.template, [
            spec.parameters.get("width", 50) / 100 - 0.5,
            spec.parameters.get("depth", 40) / 80 - 0.5,
            spec.parameters.get("height", 30) / 60 - 0.5,
            spec.parameters.get("radius", 20) / 40 - 0.5,
            spec.parameters.get("fillet_radius", 2) / 5,
            spec.parameters.get("wall_thickness", 8) / 10 - 0.5,
        ], confidence)
        spec.source = "ml"
        return spec

    def refine(self, image_bytes: bytes, spec: CADSpec, feedback: str) -> CADSpec | None:
        if not self.is_ready():
            return None
        refined, _ = apply_feedback(spec, feedback)
        refined.source = "ml"
        refined.confidence = min(spec.confidence + 0.05, 0.95)
        return refined
