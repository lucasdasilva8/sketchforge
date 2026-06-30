import type { CADSpec } from "../types/cadSpec";

export interface ConversionSummary {
  headline: string;
  steps: string[];
  dimensions: string[];
}

const TEMPLATE_LABELS: Record<string, string> = {
  box: "box / enclosure",
  cylinder: "cylinder",
  bracket: "L-bracket",
  profile_extrude: "custom profile",
  chair: "chair / furniture",
};

export function buildConversionSummary(
  spec: CADSpec,
  apiMessage?: string,
  version?: number,
): ConversionSummary {
  const label = TEMPLATE_LABELS[spec.template] ?? spec.template;
  const conf = spec.confidence !== undefined ? `${(spec.confidence * 100).toFixed(0)}%` : "—";
  const source = spec.source ?? "heuristic";

  const steps: string[] = [
    `Classified sketch as ${label} (${conf} confidence, ${source}).`,
  ];

  if (apiMessage) {
    steps.push(apiMessage);
  }

  const p = spec.parameters;
  const dimensions: string[] = [];

  switch (spec.template) {
    case "chair":
      dimensions.push(
        `Seat ${fmt(p.width)} × ${fmt(p.depth)} mm, thickness ${fmt(p.seat_thickness)} mm`,
        `Leg height ${fmt(p.height)} mm, leg thickness ${fmt(p.leg_width)} mm`,
        `Back height ${fmt(p.back_height ?? (p.height ?? 0) * 1.9)} mm`,
      );
      steps.push(
        "Estimated seat footprint and leg height from sketch proportions.",
        "Built ladder-back chair: seat, four posts, two back slats, front apron.",
      );
      break;
    case "cylinder":
      dimensions.push(`Radius ${fmt(p.radius)} mm, height ${fmt(p.height)} mm`);
      steps.push("Extruded circular profile to 3D cylinder.");
      break;
    case "bracket":
      dimensions.push(
        `Footprint ${fmt(p.width)} × ${fmt(p.depth)} mm, height ${fmt(p.height)} mm`,
        `Wall thickness ${fmt(p.wall_thickness)} mm`,
      );
      steps.push("Extruded L-shaped bracket profile.");
      break;
    case "profile_extrude":
      dimensions.push(`Profile extrude height ${fmt(p.height)} mm`);
      steps.push("Traced sketch outline and extruded vertically.");
      break;
    default:
      dimensions.push(
        `Footprint ${fmt(p.width)} × ${fmt(p.depth)} mm, height ${fmt(p.height)} mm`,
      );
      if ((p.fillet_radius ?? 0) > 0) {
        dimensions.push(`Corner fillet ${fmt(p.fillet_radius)} mm`);
      }
      steps.push("Extruded rectangular profile to 3D box.");
  }

  if (version !== undefined) {
    steps.push(`Saved as version ${version}.`);
  }

  return {
    headline: `Detected ${label}`,
    steps,
    dimensions,
  };
}

function fmt(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(1);
}
