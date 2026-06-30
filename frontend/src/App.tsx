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
    if (spec) rebuildMesh(spec);
  }, [spec, rebuildMesh]);

  const handleFileSelected = async (file: File) => {
    if (!projectId) return;
    setSketchUrl(URL.createObjectURL(file));
    setLoading(true);
    setError(null);
    setStatus("Converting sketch…");
    try {
      const result = await convertSketch(
        projectId,
        file,
        referenceDimension,
        referenceAxis,
        templateHint,
      );
      setSpec(result.cad_spec);
      setStatus(
        result.message ??
          `Generated v${result.version} (${result.cad_spec.template})`,
      );
      const project = await (await import("./lib/api")).getProject(projectId);
      setVersions(project.versions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Conversion failed");
    } finally {
      setLoading(false);
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
            onTemplateHintChange={setTemplateHint}
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
