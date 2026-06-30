import { useCallback, useEffect, useState } from "react";
import { FeedbackPanel } from "./components/FeedbackPanel";
import { ModelViewer } from "./components/ModelViewer";
import { ParametricControls } from "./components/ParametricControls";
import { SketchUpload } from "./components/SketchUpload";
import {
  convertSketch,
  createProject,
  refineProject,
  updateSpecParameters,
  API_BASE,
} from "./lib/api";
import { syncSketchesFromParameters } from "./lib/cadCompiler";
import { getCADWorker } from "./lib/cadWorkerClient";
import type { CADSpec, MeshData, VersionRecord } from "./types/cadSpec";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [sketchUrl, setSketchUrl] = useState<string | null>(null);
  const [referenceDimension, setReferenceDimension] = useState(100);
  const [referenceAxis, setReferenceAxis] = useState("width");
  const [templateHint, setTemplateHint] = useState("auto");
  const [sketchFile, setSketchFile] = useState<File | null>(null);
  const [spec, setSpec] = useState<CADSpec | null>(null);
  const [versions, setVersions] = useState<VersionRecord[]>([]);
  const [mesh, setMesh] = useState<MeshData | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  const rebuildMesh = useCallback(async (nextSpec: CADSpec) => {
    setLoading(true);
    setError(null);
    try {
      const synced = syncSketchesFromParameters(nextSpec);
      const worker = getCADWorker();
      const nextMesh = await worker.buildMesh(synced);
      setMesh(nextMesh);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to build 3D model");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    createProject("My sketch")
      .then((p) => setProjectId(p.id))
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const isLocal =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.port === "5173";
    if (!isLocal) return;
    fetch(`${API_BASE}/health`)
      .then((res) => (res.ok ? res.json() : null))
      .then((health: { chair_detection?: boolean } | null) => {
        if (health && health.chair_detection === false) {
          setError(
            "Backend is outdated (no chair detection). Stop the old server and run ./scripts/dev.sh",
          );
        }
      })
      .catch(() => {
        /* ignore health probe failures */
      });
  }, []);

  useEffect(() => {
    if (spec) rebuildMesh(spec);
  }, [spec, rebuildMesh]);

  const runConversion = useCallback(
    async (file: File, hint = templateHint) => {
      if (!projectId) return;
      setLoading(true);
      setError(null);
      setStatus("Converting sketch…");
      try {
        const result = await convertSketch(
          projectId,
          file,
          referenceDimension,
          referenceAxis,
          hint,
        );
        setSpec(result.cad_spec);
        const template = result.cad_spec.template;
        let message =
          result.message ?? `Generated v${result.version} (${template})`;
        if (template === "box" && hint === "auto") {
          message +=
            " — If this is a chair, pick “Chair / furniture” above and re-upload (or change shape type to re-convert).";
        }
        setStatus(message);
        const project = await (await import("./lib/api")).getProject(projectId);
        setVersions(project.versions);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Conversion failed");
      } finally {
        setLoading(false);
      }
    },
    [projectId, referenceDimension, referenceAxis, templateHint],
  );

  const handleFileSelected = async (file: File) => {
    setSketchFile(file);
    setSketchUrl(URL.createObjectURL(file));
    await runConversion(file, templateHint);
  };

  const handleTemplateHintChange = (hint: string) => {
    setTemplateHint(hint);
    if (sketchFile && hint !== "auto") {
      void runConversion(sketchFile, hint);
    }
  };

  const handleParamChange = (key: string, value: number) => {
    if (!spec) return;
    const updated = syncSketchesFromParameters(updateSpecParameters(spec, key, value));
    setSpec(updated);
  };

  const handleFeedback = async (feedback: string) => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    setStatus("Applying feedback…");
    try {
      const result = await refineProject(projectId, feedback);
      setSpec(result.cad_spec);
      setStatus(result.applied_changes.join("; "));
      const project = await (await import("./lib/api")).getProject(projectId);
      setVersions(project.versions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Feedback failed");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: "stl" | "step") => {
    if (!spec) return;
    setExporting(true);
    try {
      const worker = getCADWorker();
      const files = await worker.exportFiles(syncSketchesFromParameters(spec));
      downloadBlob(format === "stl" ? files.stl : files.step, `model.${format}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>SketchForge</h1>
          <p>Convert hand sketches into editable parametric 3D models</p>
        </div>
        <div className="export-actions">
          <button type="button" disabled={!spec || exporting} onClick={() => handleExport("stl")}>
            Export STL
          </button>
          <button type="button" disabled={!spec || exporting} onClick={() => handleExport("step")}>
            Export STEP
          </button>
        </div>
      </header>

      {status && <div className="status-banner">{status}</div>}
      {error && <div className="status-banner error">{error}</div>}

      <main className="workspace">
        <section className="left-column">
          <SketchUpload
            sketchUrl={sketchUrl}
            referenceDimension={referenceDimension}
            referenceAxis={referenceAxis}
            templateHint={templateHint}
            onReferenceDimensionChange={setReferenceDimension}
            onReferenceAxisChange={setReferenceAxis}
            onTemplateHintChange={handleTemplateHintChange}
            onFileSelected={handleFileSelected}
            disabled={loading || !projectId}
          />
          <ParametricControls spec={spec} onChange={handleParamChange} />
          <FeedbackPanel
            versions={versions}
            onSubmitFeedback={handleFeedback}
            disabled={!spec || loading}
          />
        </section>
        <section className="right-column">
          <ModelViewer mesh={mesh} loading={loading} error={error} />
        </section>
      </main>
    </div>
  );
}
