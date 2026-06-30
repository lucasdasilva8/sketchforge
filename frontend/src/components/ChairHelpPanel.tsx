import { useState } from "react";
import {
  chairHelpHeadline,
  getChairHelpSections,
  type ChairHelpContext,
} from "../lib/chairHelp";

interface ChairHelpPanelProps {
  context: ChairHelpContext;
}

export function ChairHelpPanel({ context }: ChairHelpPanelProps) {
  const [open, setOpen] = useState(true);
  const sections = getChairHelpSections(context);

  const show =
    context.templateHint === "chair" || Boolean(context.detectedStyle);

  if (!show) return null;

  return (
    <div className="help-panel">
      <button
        type="button"
        className="help-panel-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>{chairHelpHeadline(context)}</span>
        <span className="help-panel-chevron" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>

      {open && (
        <div className="help-panel-body">
          {sections.map((section) => (
            <div key={section.title} className="help-section">
              <h4>{section.title}</h4>
              <ul>
                {section.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
