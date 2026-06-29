import { useRef, useState } from "react";

interface SketchUploadProps {
  sketchUrl: string | null;
  referenceDimension: number;
  referenceAxis: string;
  onReferenceDimensionChange: (value: number) => void;
  onReferenceAxisChange: (axis: string) => void;
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

const AXES = [
  { value: "width", label: "Width" },
  { value: "depth", label: "Depth" },
  { value: "height", label: "Height" },
  { value: "radius", label: "Radius" },
];

export function SketchUpload({
  sketchUrl,
  referenceDimension,
  referenceAxis,
  onReferenceDimensionChange,
  onReferenceAxisChange,
  onFileSelected,
  disabled,
}: SketchUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onFileSelected(file);
  };

  return (
    <div className="sketch-panel">
      <div className="panel-header">
        <h2>Sketch Input</h2>
        <p>Upload a photo of a hand-drawn product sketch.</p>
      </div>

      <div
        className={`dropzone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          hidden
          disabled={disabled}
          onChange={(e) => handleFiles(e.target.files)}
        />
        {sketchUrl ? (
          <img src={sketchUrl} alt="Uploaded sketch" className="sketch-preview" />
        ) : (
          <div className="dropzone-placeholder">
            <strong>Drop sketch here</strong>
            <span>or click to browse (PNG, JPG, WebP)</span>
          </div>
        )}
      </div>

      <div className="reference-fields">
        <label>
          Reference dimension (mm)
          <input
            type="number"
            min={1}
            step={0.1}
            value={referenceDimension}
            onChange={(e) => onReferenceDimensionChange(Number(e.target.value))}
          />
        </label>
        <label>
          Reference axis
          <select
            value={referenceAxis}
            onChange={(e) => onReferenceAxisChange(e.target.value)}
          >
            {AXES.map((axis) => (
              <option key={axis.value} value={axis.value}>
                {axis.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
