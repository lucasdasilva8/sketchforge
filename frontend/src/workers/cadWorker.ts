import type { CADSpec, ExportResult, MeshData } from "../types/cadSpec";
import { compileCADSpecCode, syncSketchesFromParameters } from "../lib/cadCompiler";
import opencascade from "replicad-opencascadejs/src/replicad_single.js";
import opencascadeWasm from "replicad-opencascadejs/src/replicad_single.wasm?url";
import { setOC, draw, drawCircle } from "replicad";

type WorkerRequest =
  | { type: "build"; spec: CADSpec }
  | { type: "export"; spec: CADSpec };

type WorkerResponse =
  | { type: "ready" }
  | { type: "mesh"; mesh: MeshData }
  | { type: "export"; result: { stl: ArrayBuffer; step: ArrayBuffer } }
  | { type: "error"; message: string };

let ocReady: Promise<void> | null = null;

async function ensureOC() {
  if (!ocReady) {
    ocReady = (async () => {
      const oc = await opencascade({
        locateFile: () => opencascadeWasm,
      });
      setOC(oc);
    })();
  }
  await ocReady;
}

async function buildShape(spec: CADSpec) {
  await ensureOC();

  const synced = syncSketchesFromParameters(spec);
  const code = compileCADSpecCode(synced);
  const builder = new Function("draw", "drawCircle", `"use strict";\n${code}`);
  return builder(draw, drawCircle);
}

function shapeToMesh(shape: { mesh: (opts: { tolerance: number; angularTolerance: number }) => { vertices: number[]; normals: number[]; triangles: number[] } }): MeshData {
  const mesh = shape.mesh({ tolerance: 0.1, angularTolerance: 30 });
  return {
    vertices: new Float32Array(mesh.vertices),
    normals: new Float32Array(mesh.normals),
    indices: new Uint32Array(mesh.triangles),
  };
}

self.onmessage = async (event: MessageEvent<WorkerRequest & { _id?: number }>) => {
  const id = event.data._id;
  try {
    const msg = event.data;
    if (msg.type === "build") {
      const shape = await buildShape(msg.spec);
      const mesh = shapeToMesh(shape);
      self.postMessage(
        { _id: id, type: "mesh", mesh } satisfies WorkerResponse & { _id?: number },
        [mesh.vertices.buffer, mesh.normals.buffer, mesh.indices.buffer],
      );
      return;
    }

    if (msg.type === "export") {
      const shape = await buildShape(msg.spec);
      const stlBlob = shape.blobSTL({ tolerance: 0.1, angularTolerance: 30 });
      const stepBlob = shape.blobSTEP();
      const stlBuffer = await stlBlob.arrayBuffer();
      const stepBuffer = await stepBlob.arrayBuffer();
      self.postMessage(
        { _id: id, type: "export", result: { stl: stlBuffer, step: stepBuffer } } satisfies WorkerResponse & { _id?: number },
        [stlBuffer, stepBuffer],
      );
    }
  } catch (err) {
    self.postMessage({
      _id: id,
      type: "error",
      message: err instanceof Error ? err.message : "CAD worker failed",
    } satisfies WorkerResponse & { _id?: number });
  }
};

self.postMessage({ type: "ready" } satisfies WorkerResponse);

export type { WorkerRequest, WorkerResponse, ExportResult, MeshData };
