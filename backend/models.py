from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


TemplateType = Literal["box", "cylinder", "profile_extrude", "bracket", "chair"]
PlaneType = Literal["XY", "XZ", "YZ"]
SourceType = Literal["heuristic", "ml", "feedback", "manual"]


class SketchDef(BaseModel):
    id: str
    plane: PlaneType = "XY"
    profile: List[List[float]]


class ExtrudeOp(BaseModel):
    op: Literal["extrude"] = "extrude"
    sketch: str
    distance: float = Field(gt=0)


class FilletOp(BaseModel):
    op: Literal["fillet"] = "fillet"
    edges: List[str] = Field(default_factory=list)
    radius: float = Field(ge=0)


class RevolveOp(BaseModel):
    op: Literal["revolve"] = "revolve"
    sketch: str
    angle: float = Field(default=360, ge=0, le=360)


Operation = Union[ExtrudeOp, FilletOp, RevolveOp]


class CADSpec(BaseModel):
    version: int = 1
    units: Literal["mm", "cm", "in"] = "mm"
    template: TemplateType
    sketches: List[SketchDef]
    operations: List[Operation]
    parameters: Dict[str, Any]
    confidence: float = Field(default=0.5, ge=0, le=1)
    source: SourceType = "heuristic"


class ProjectCreate(BaseModel):
    name: str = "Untitled sketch"


class ConvertRequest(BaseModel):
    reference_dimension: float = Field(gt=0, description="Known size in mm")
    reference_axis: Literal["width", "depth", "height", "radius"] = "width"
    use_ml: bool = True


class RefineRequest(BaseModel):
    feedback: str = Field(min_length=1)
    use_ml: bool = True


class VersionRecord(BaseModel):
    version: int
    cad_spec: CADSpec
    feedback: Optional[str] = None
    source: SourceType
    created_at: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    sketch_path: Optional[str]
    current_version: int
    cad_spec: Optional[CADSpec]
    versions: List[VersionRecord]


class ConvertResponse(BaseModel):
    project_id: str
    version: int
    cad_spec: CADSpec
    message: Optional[str] = None


class RefineResponse(BaseModel):
    project_id: str
    version: int
    cad_spec: CADSpec
    applied_changes: List[str]


def spec_to_dict(spec: CADSpec) -> Dict[str, Any]:
    return spec.model_dump()
