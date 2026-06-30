import type { ConversionSummary as Summary } from "../lib/conversionSummary";

interface ConversionSummaryProps {
  summary: Summary | null;
  meshReady: boolean;
  meshError: string | null;
  converting: boolean;
  buildingMesh: boolean;
  canReconvert: boolean;
  canRebuild: boolean;
  onReconvert: () => void;
  onRebuildMesh: () => void;
}

export function ConversionSummary({
  summary,
  meshReady,
  meshError,
  converting,
  buildingMesh,
  canReconvert,
  canRebuild,
  onReconvert,
  onRebuildMesh,
}: ConversionSummaryProps) {
  if (!summary) {
    return (
      <div className="summary-panel">
        <h3>Process</h3>
        <p className="muted">Upload a sketch to see detection steps and dimensions.</p>
      </div>
    );
  }

  return (
    <div className="summary-panel">
      <div className="panel-header compact">
        <h3>Process</h3>
        {meshReady && !meshError && <span className="badge subtle">3D ready</span>}
        {buildingMesh && <span className="badge">Building 3D…</span>}
        {meshError && <span className="badge error-badge">3D failed</span>}
      </div>

      <p className="summary-headline">{summary.headline}</p>

      <ul className="summary-list">
        {summary.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>

      {summary.dimensions.length > 0 && (
        <div className="summary-dimensions">
          <strong>Dimensions used</strong>
          <ul>
            {summary.dimensions.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      {meshError && <p className="summary-error">{meshError}</p>}

      <div className="summary-actions">
        <button
          type="button"
          className="secondary"
          disabled={!canRebuild || buildingMesh || converting}
          onClick={onRebuildMesh}
        >
          Rebuild 3D model
        </button>
        <button
          type="button"
          className="secondary"
          disabled={!canReconvert || converting || buildingMesh}
          onClick={onReconvert}
        >
          Re-convert sketch
        </button>
      </div>
    </div>
  );
}
