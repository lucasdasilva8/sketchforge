import type { CADSpec, ExportResult, MeshData } from "../types/cadSpec";

type Pending = {
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
};

export class CADWorkerClient {
  private worker: Worker;
  private pending = new Map<number, Pending>();
  private seq = 0;
  private ready: Promise<void>;

  constructor() {
    this.worker = new Worker(new URL("../workers/cadWorker.ts", import.meta.url), {
      type: "module",
    });
    this.ready = new Promise((resolve, reject) => {
      const onMessage = (event: MessageEvent) => {
        if (event.data?.type === "ready") {
          this.worker.removeEventListener("message", onMessage);
          resolve();
        }
        if (event.data?.type === "error") {
          this.worker.removeEventListener("message", onMessage);
          reject(new Error(event.data.message));
        }
      };
      this.worker.addEventListener("message", onMessage);
    });

    this.worker.onmessage = (event: MessageEvent) => {
      const id = event.data?._id as number | undefined;
      if (id === undefined) return;
      const pending = this.pending.get(id);
      if (!pending) return;
      this.pending.delete(id);
      if (event.data.type === "error") {
        pending.reject(new Error(event.data.message));
      } else {
        pending.resolve(event.data);
      }
    };
  }

  private send<T>(payload: Record<string, unknown>): Promise<T> {
    return this.ready.then(
      () =>
        new Promise<T>((resolve, reject) => {
          const id = ++this.seq;
          this.pending.set(id, { resolve: resolve as (v: unknown) => void, reject });
          this.worker.postMessage({ ...payload, _id: id });
        }),
    );
  }

  async buildMesh(spec: CADSpec): Promise<MeshData> {
    const res = await this.send<{ type: "mesh"; mesh: MeshData }>({ type: "build", spec });
    return res.mesh;
  }

  async exportFiles(spec: CADSpec): Promise<ExportResult> {
    const res = await this.send<{ type: "export"; result: { stl: ArrayBuffer; step: ArrayBuffer } }>({
      type: "export",
      spec,
    });
    return {
      stl: new Blob([res.result.stl], { type: "model/stl" }),
      step: new Blob([res.result.step], { type: "application/step" }),
    };
  }

  terminate() {
    this.worker.terminate();
  }
}

let client: CADWorkerClient | null = null;

export function getCADWorker(): CADWorkerClient {
  if (!client) client = new CADWorkerClient();
  return client;
}
