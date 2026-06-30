import { useCallback, useEffect, useState } from "react";
import { ConversionSummary } from "./components/ConversionSummary";
import { ChairHelpPanel } from "./components/ChairHelpPanel";
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
import { buildConversionSummary, type ConversionSummary as Summary } from "./lib/conversionSummary";
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
  const [furnitureStyleHint, setFurnitureStyleHint] = useState("auto");
  const [sketchFile, setSketchFile] = useState<File | null>(null);
  const [spec, setSpec] = useState<CADSpec | null>(null);
  const [versions, setVersions] = useState<VersionRecord[]>([]);
  const [mesh, setMesh] = useState<MeshData | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [meshError, setMeshError] = useState<string | null>(null);
  const [converting, setConverting] = useState(false);
  const [buildingMesh, setBuildingMesh] = useState(false);
  const [exporting, setExporting] = useState(false);

  const rebuildMesh = useCallback(async (nextSpec: CADSpec) => {
    setBuildingMesh(true);
    setMeshError(null);
    try {
      const synced = syncSketchesFromParameters(nextSpec);
      const worker = getCADWorker();
      const nextMesh = await worker.buildMesh(synced);
      setMesh(nextMesh);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to build 3D model";
      setMeshError(message);
      setMesh(null);
    } finally {
      setBuildingMesh(false);
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
    async (file: File, hint = templateHint, styleHint = furnitureStyleHint) => {
      if (!projectId) return;
      setConverting(true);
      setError(null);
      setMeshError(null);
      setStatus("Converting sketch…");
      try {
        const result = await convertSketch(
          projectId,
          file,
          referenceDimension,
          referenceAxis,
          hint,
          styleHint,
        );
        setSpec(result.cad_spec);
        setSummary(buildConversionSummary(result.cad_spec, result.message, result.version));
        setStatus(result.message ?? `Generated v${result.version}`);
        const project = await (await import("./lib/api")).getProject(projectId);
        setVersions(project.versions);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Conversion failed");
      } finally {
        setConverting(false);
      }
    },
    [projectId, referenceDimension, referenceAxis, templateHint, furnitureStyleHint],
  );

  const handleFileSelected = async (file: File) => {
    setSketchFile(file);
    setSketchUrl(URL.createObjectURL(file));
    await runConversion(file, templateHint, furnitureStyleHint);
  };

  const handleTemplateHintChange = (hint: string) => {
    setTemplateHint(hint);
    if (sketchFile && hint !== "auto") {
      void runConversion(sketchFile, hint, furnitureStyleHint);
    }
  };

  const handleFurnitureStyleHintChange = (hint: string) => {
    setFurnitureStyleHint(hint);
    if (sketchFile && (templateHint === "chair" || templateHint === "auto")) {
      void runConversion(sketchFile, templateHint, hint);
    }
  };

  const handleParamChange = (key: string, value: number) => {
    if (!spec) return;
    const updated = syncSketchesFromParameters(updateSpecParameters(spec, key, value));
    setSpec(updated);
    setSummary(buildConversionSummary(updated));
  };

  const handleFeedback = async (feedback: string) => {
    if (!projectId) return;
    setConverting(true);
    setError(null);
    setStatus("Applying feedback…");
    try {
      const result = await refineProject(projectId, feedback);
      setSpec(result.cad_spec);
      setSummary(
        buildConversionSummary(
          result.cad_spec,
          result.applied_changes.join("; "),
          result.version,
        ),
      );
      setStatus(result.applied_changes.join("; "));
      const project = await (await import("./lib/api")).getProject(projectId);
      setVersions(project.versions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Feedback failed");
    } finally {
      setConverting(false);
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

  const handleRebuildMesh = () => {
    if (spec) void rebuildMesh(spec);
  };

  const handleReconvert = () => {
    if (sketchFile) void runConversion(sketchFile, templateHint, furnitureStyleHint);
  };

  const loading = converting || buildingMesh;

  return (
    <div className="app">
      <header className="editorial-header">
        <nav className="top-nav">
          <span className="nav-brand">SketchForge</span>
          <div className="nav-actions">
            <button type="button" disabled={!spec || exporting} onClick={() => handleExport("stl")}>
              Export STL
            </button>
            <button type="button" disabled={!spec || exporting} onClick={() => handleExport("step")}>
              Export STEP
            </button>
          </div>
        </nav>
        <div className="hero-title">
          <div>
            <h1 className="hero-word">Sketch</h1>
            <p className="hero-tagline">Convert hand sketches into editable parametric 3D models</p>
          </div>
          <h1 className="hero-word-vertical" aria-hidden="true">
            Forge
          </h1>
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
            furnitureStyleHint={furnitureStyleHint}
            onReferenceDimensionChange={setReferenceDimension}
            onReferenceAxisChange={setReferenceAxis}
            onTemplateHintChange={handleTemplateHintChange}
            onFurnitureStyleHintChange={handleFurnitureStyleHintChange}
            onFileSelected={handleFileSelected}
            disabled={loading || !projectId}
          />
          <ChairHelpPanel
            context={{
              templateHint,
              furnitureStyleHint,
              detectedStyle:
                spec?.template === "chair"
                  ? String(spec.parameters.furniture_style ?? "")
                  : undefined,
              hasSketch: Boolean(sketchFile),
            }}
          />
          <ConversionSummary
            summary={summary}
            meshReady={mesh !== null && !meshError}
            meshError={meshError}
            converting={converting}
            buildingMesh={buildingMesh}
            canReconvert={Boolean(sketchFile && projectId)}
            canRebuild={Boolean(spec)}
            onReconvert={handleReconvert}
            onRebuildMesh={handleRebuildMesh}
          />
          <ParametricControls spec={spec} onChange={handleParamChange} />
          <FeedbackPanel
            versions={versions}
            onSubmitFeedback={handleFeedback}
            disabled={!spec || loading}
            isChair={spec?.template === "chair"}
          />
        </section>
        <section className="right-column">
          <ModelViewer
            mesh={mesh}
            loading={buildingMesh}
            error={meshError}
            onRebuild={handleRebuildMesh}
            canRebuild={Boolean(spec) && !buildingMesh}
          />
        </section>
      </main>

      <footer className="footer-note">
        <span className="footer-dot" aria-hidden="true" />
        <span>SketchForge — Sketch to parametric CAD</span>
      </footer>
    </div>
  );
}
