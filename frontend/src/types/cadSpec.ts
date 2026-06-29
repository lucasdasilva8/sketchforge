export type TemplateType = "box" | "cylinder" | "profile_extrude" | "bracket";
export type PlaneType = "XY" | "XZ" | "YZ";

export interface SketchDef {
  id: string;
  plane: PlaneType;
  profile: number[][];
}

export interface ExtrudeOp {
  op: "extrude";
  sketch: string;
  distance: number;
}

export interface FilletOp {
  op: "fillet";
  edges: string[];
  radius: number;
}

export interface RevolveOp {
  op: "revolve";
  sketch: string;
  angle: number;
}

export type Operation = ExtrudeOp | FilletOp | RevolveOp;

export interface CADSpec {
  version: number;
  units: "mm" | "cm" | "in";
  template: TemplateType;
  sketches: SketchDef[];
  operations: Operation[];
  parameters: Record<string, number>;
  confidence?: number;
  source?: string;
}

export interface VersionRecord {
  version: number;
  cad_spec: CADSpec;
  feedback: string | null;
  source: string;
  created_at: string;
}

export interface ProjectResponse {
  id: string;
  name: string;
  sketch_path: string | null;
  current_version: number;
  cad_spec: CADSpec | null;
  versions: VersionRecord[];
}

export interface ConvertResponse {
  project_id: string;
  version: number;
  cad_spec: CADSpec;
  message?: string;
}

export interface RefineResponse {
  project_id: string;
  version: number;
  cad_spec: CADSpec;
  applied_changes: string[];
}

export interface MeshData {
  vertices: Float32Array;
  normals: Float32Array;
  indices: Uint32Array;
}

export interface ExportResult {
  stl: Blob;
  step: Blob;
}
