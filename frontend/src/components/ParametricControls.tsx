import type { CADSpec } from "../types/cadSpec";
import { getEditableParameters } from "../lib/cadCompiler";
import { chairStyleDescription } from "../lib/chairModels";

interface ParametricControlsProps {
  spec: CADSpec | null;
  onChange: (key: string, value: number) => void;
}

export function ParametricControls({ spec, onChange }: ParametricControlsProps) {
  if (!spec) {
    return (
      <div className="params-panel">
        <h3>Parameters</h3>
        <p className="muted">Convert a sketch to edit dimensions.</p>
      </div>
    );
  }

  const keys = getEditableParameters(spec);

  return (
    <div className="params-panel">
      <div className="panel-header compact">
        <h3>Parameters</h3>
        <span className="badge">{spec.template}</span>
        {spec.template === "chair" && spec.parameters.furniture_style && (
          <span className="badge subtle">
            {chairStyleDescription(String(spec.parameters.furniture_style))}
          </span>
        )}
        {spec.confidence !== undefined && (
          <span className="badge subtle">Confidence {(spec.confidence * 100).toFixed(0)}%</span>
        )}
      </div>
      <div className="param-grid">
        {keys.map((key) => (
          <label key={key}>
            {key.replace(/_/g, " ")}
            <input
              type="number"
              min={0.1}
              step={0.5}
              value={spec.parameters[key] ?? 0}
              onChange={(e) => onChange(key, Number(e.target.value))}
            />
          </label>
        ))}
      </div>
    </div>
  );
}
