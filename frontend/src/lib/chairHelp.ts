import type { FurnitureStyle } from "./chairModels";
import { chairStyleDescription } from "./chairModels";

export interface ChairHelpContext {
  templateHint: string;
  furnitureStyleHint: string;
  detectedStyle?: string;
  hasSketch: boolean;
}

export interface ChairHelpSection {
  title: string;
  items: string[];
}

const UPLOAD_TIPS: ChairHelpSection = {
  title: "Before you upload",
  items: [
    "Side-view or 3/4 sketches work best — legs and back should be visible.",
    "Set Shape type to Chair / furniture if auto-detect picks box.",
    "Enter a real seat width (mm) as the reference dimension, axis Width.",
    "Use a clear photo: dark lines on light paper, minimal shadows.",
  ],
};

const REFERENCE_TIPS: ChairHelpSection = {
  title: "Reference dimension",
  items: [
    "Width — measure the seat left-to-right in your sketch (most common).",
    "Height — use overall chair height (floor to top of back) for tall side views.",
    "If proportions look wrong, try the other axis or re-measure the longest labeled edge.",
  ],
};

const STYLE_TIPS: Record<FurnitureStyle, ChairHelpSection> = {
  ladder_back: {
    title: "Ladder-back chair",
    items: [
      "Best for side views with vertical back posts and horizontal slats.",
      "Adjust back height for taller or shorter backrests.",
      "Leg height controls seat height from the floor.",
    ],
  },
  dining: {
    title: "Dining chair",
    items: [
      "Simple side chair with a solid back panel and four legs.",
      "Good default when the sketch shows a single chair silhouette.",
      "Use depth for how far the seat extends front-to-back.",
    ],
  },
  stool: {
    title: "Stool",
    items: [
      "No backrest — use for short, squat sketches.",
      "Pick this manually if auto chooses a chair with a back.",
      "Height sets leg length; seat thickness is usually thin.",
    ],
  },
  armchair: {
    title: "Armchair",
    items: [
      "For wide sketches with arms or bulky upholstered shapes.",
      "Seat depth is usually deeper than a dining chair.",
      "Try feedback: “wider seat” or “taller back”.",
    ],
  },
  bench: {
    title: "Bench",
    items: [
      "For long, wide seat sketches (plan view or front view).",
      "Width is the bench length; depth is seat depth.",
      "Auto-detect may miss benches — select Bench style manually.",
    ],
  },
};

export const CHAIR_FEEDBACK_SUGGESTIONS = [
  "Make it a stool",
  "Taller back",
  "Wider seat",
  "Set height to 450mm",
  "This is a ladder-back chair",
  "Make it an armchair",
  "Longer legs",
];

export function getChairHelpSections(ctx: ChairHelpContext): ChairHelpSection[] {
  const sections: ChairHelpSection[] = [];

  if (!ctx.hasSketch) {
    sections.push(UPLOAD_TIPS);
  } else {
    sections.push(REFERENCE_TIPS);
  }

  const style =
    ctx.detectedStyle && ctx.detectedStyle !== "auto"
      ? ctx.detectedStyle
      : ctx.furnitureStyleHint !== "auto"
        ? ctx.furnitureStyleHint
        : ctx.detectedStyle;

  if (style && style in STYLE_TIPS) {
    sections.push(STYLE_TIPS[style as FurnitureStyle]);
  } else if (ctx.templateHint === "chair") {
    sections.push({
      title: "Furniture styles",
      items: [
        "Ladder-back — slats and apron (classic side view).",
        "Dining — solid back, four legs.",
        "Stool — no back, shorter.",
        "Armchair — arms + deep seat.",
        "Bench — long seat, multiple legs.",
        "Leave style on Auto-detect or pick one before uploading.",
      ],
    });
  }

  sections.push({
    title: "If the result is wrong",
    items: [
      "Use Re-convert after changing Shape type or Furniture style.",
      "Rebuild 3D model if only the preview failed.",
      "Sliders: width, depth, height, back height, leg width, seat thickness.",
      "Refine with plain language — corrections train the model.",
    ],
  });

  return sections;
}

export function chairHelpHeadline(ctx: ChairHelpContext): string {
  if (ctx.detectedStyle) {
    return `Chair help — ${chairStyleDescription(ctx.detectedStyle)}`;
  }
  if (ctx.furnitureStyleHint !== "auto") {
    return `Chair help — ${chairStyleDescription(ctx.furnitureStyleHint)}`;
  }
  return "Chair help";
}
