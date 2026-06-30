import type {
  CADSpec,
  ConvertResponse,
  ProjectResponse,
  RefineResponse,
} from "../types/cadSpec";

const isLocalDev =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.port === "5173");

const API_BASE = isLocalDev
  ? "/api"
  : (window as unknown as { SKETCHFORGE_API?: string }).SKETCHFORGE_API ??
    "https://sketchforge-api.onrender.com";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function createProject(name = "Untitled sketch"): Promise<ProjectResponse> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return handle(res);
}

export async function getProject(projectId: string): Promise<ProjectResponse> {
  return handle(await fetch(`${API_BASE}/projects/${projectId}`));
}

export async function convertSketch(
  projectId: string,
  file: File,
  referenceDimension: number,
  referenceAxis: string,
  templateHint = "auto",
): Promise<ConvertResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("reference_dimension", String(referenceDimension));
  form.append("reference_axis", referenceAxis);
  form.append("use_ml", "true");
  form.append("template_hint", templateHint);
  return handle(await fetch(`${API_BASE}/projects/${projectId}/convert`, { method: "POST", body: form }));
}

export async function refineProject(
  projectId: string,
  feedback: string,
): Promise<RefineResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback, use_ml: true }),
  });
  return handle(res);
}

export function updateSpecParameters(spec: CADSpec, key: string, value: number): CADSpec {
  return {
    ...spec,
    parameters: { ...spec.parameters, [key]: value },
    source: "manual",
  };
}

export { API_BASE };
