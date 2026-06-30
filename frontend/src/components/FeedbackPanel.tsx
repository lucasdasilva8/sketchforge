import { useState } from "react";
import type { VersionRecord } from "../types/cadSpec";

interface FeedbackPanelProps {
  versions: VersionRecord[];
  onSubmitFeedback: (feedback: string) => Promise<void>;
  disabled?: boolean;
}

export function FeedbackPanel({ versions, onSubmitFeedback, disabled }: FeedbackPanelProps) {
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [lastChanges, setLastChanges] = useState<string[]>([]);

  const handleSubmit = async () => {
    if (!feedback.trim()) return;
    setSubmitting(true);
    try {
      await onSubmitFeedback(feedback.trim());
      setLastChanges([]);
      setFeedback("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="feedback-panel">
      <div className="panel-header">
        <h2>Refine</h2>
        <p>Describe what to change and the model will update.</p>
      </div>

      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder='e.g. "Make it taller" or "Round the corners more" or "Set width to 120mm"'
        rows={4}
        disabled={disabled || submitting}
      />

      <button
        type="button"
        className="primary"
        disabled={disabled || submitting || !feedback.trim()}
        onClick={handleSubmit}
      >
        {submitting ? "Applying…" : "Apply feedback"}
      </button>

      {lastChanges.length > 0 && (
        <ul className="changes-list">
          {lastChanges.map((change) => (
            <li key={change}>{change}</li>
          ))}
        </ul>
      )}

      <div className="version-history">
        <h3>Version history</h3>
        {versions.length === 0 && <p className="muted">No versions yet.</p>}
        <ol>
          {versions.map((v) => (
            <li key={v.version}>
              <strong>v{v.version}</strong>
              <span className="muted"> · {v.source}</span>
              {v.feedback && <blockquote>{v.feedback}</blockquote>}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export function FeedbackPanelWithChanges(
  props: FeedbackPanelProps & { appliedChanges?: string[] },
) {
  return <FeedbackPanel {...props} />;
}
