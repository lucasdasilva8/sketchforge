from __future__ import annotations

import io
import sys
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
ML_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from dataset.param_codec import (
    IDX_TO_TEMPLATE,
    TEMPLATE_IDS,
    TEMPLATE_TO_IDX,
    decode_params,
    encode_params,
)
from models import CADSpec, ExtrudeOp, FilletOp, SketchDef
from pipelines.feedback_parser import apply_feedback
from pipelines.sketch_parser import sketch_to_cad_spec

CHECKPOINT_DIR = ML_DIR / "checkpoints"
CHECKPOINT_PATH = CHECKPOINT_DIR / "sketch_cad.pt"


class SketchEncoder(nn.Module):
    def __init__(self, embed_dim: int = 256, pretrained: bool = True) -> None:
        super().__init__()
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        backbone = models.resnet18(weights=weights)
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
    def __init__(self, pretrained: bool = True) -> None:
        super().__init__()
        self.encoder = SketchEncoder(pretrained=pretrained)
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


def params_to_spec(template: str, parameters: dict[str, float], confidence: float) -> CADSpec:
    width = parameters.get("width", 100)
    depth = parameters.get("depth", 50)
    height = parameters.get("height", 30)
    radius = parameters.get("radius", 25)
    fillet = parameters.get("fillet_radius", 0)
    wall = parameters.get("wall_thickness", 8)

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
    if template == "chair":
        seat_t = parameters.get("seat_thickness", parameters.get("radius", 5))
        leg_w = parameters.get("leg_width", parameters.get("wall_thickness", 8))
        leg_h = parameters.get("height", 40)
        profile = [[0, 0], [width, 0], [width, depth], [0, depth]]
        return CADSpec(
            template="chair",
            sketches=[SketchDef(id="seat", plane="XY", profile=profile)],
            operations=[ExtrudeOp(sketch="seat", distance=seat_t)],
            parameters={
                "width": width,
                "depth": depth,
                "height": leg_h,
                "leg_width": leg_w,
                "seat_thickness": seat_t,
                "wall_thickness": leg_w,
                "fillet_radius": 0,
            },
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
    def try_load(cls) -> "SketchCADPredictor | None":
        if not CHECKPOINT_PATH.exists():
            return cls(None)
        model = SketchCADModel(pretrained=False)
        state = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=False)
        model.eval()
        return cls(model)

    def is_ready(self) -> bool:
        return self.model is not None

    def _encode(self, image_bytes: bytes) -> tuple[str, dict[str, float], float]:
        assert self.model is not None
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = PREPROCESS(img).unsqueeze(0)
        with torch.no_grad():
            tmpl_logits, params, conf = self.model(tensor)
        template_idx = int(tmpl_logits.argmax(dim=1).item())
        template = IDX_TO_TEMPLATE.get(template_idx, "box")
        parameters = decode_params(params.squeeze(0).tolist())
        confidence = float(conf.item())
        return template, parameters, confidence

    def predict(
        self,
        image_bytes: bytes,
        reference_dimension: float,
        reference_axis: str = "width",
    ) -> CADSpec:
        if not self.is_ready():
            return sketch_to_cad_spec(image_bytes, reference_dimension, reference_axis)  # type: ignore[arg-type]

        template, ml_params, confidence = self._encode(image_bytes)
        heuristic = sketch_to_cad_spec(image_bytes, reference_dimension, reference_axis)  # type: ignore[arg-type]

        # Blend ML template with heuristic dimensions scaled from reference
        merged = dict(ml_params)
        for key in ("width", "depth", "height", "radius", "wall_thickness", "fillet_radius"):
            if key in heuristic.parameters:
                merged[key] = heuristic.parameters[key]

        spec = params_to_spec(template, merged, confidence)
        if heuristic.confidence > confidence:
            spec.template = heuristic.template
            spec.parameters = heuristic.parameters
            spec.sketches = heuristic.sketches
            spec.operations = heuristic.operations
            spec.confidence = heuristic.confidence * 0.7 + confidence * 0.3
        spec.source = "ml"
        return spec

    def refine(self, image_bytes: bytes, spec: CADSpec, feedback: str) -> CADSpec | None:
        if not self.is_ready():
            return None
        refined, _ = apply_feedback(spec, feedback)
        refined.source = "ml"
        refined.confidence = min(spec.confidence + 0.05, 0.95)
        return refined
