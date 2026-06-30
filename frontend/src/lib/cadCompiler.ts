import type { CADSpec } from "../types/cadSpec";

export function syncSketchesFromParameters(spec: CADSpec): CADSpec {
  const p = spec.parameters;
  const next = structuredClone(spec);

  if (next.template === "box") {
    const w = p.width ?? 100;
    const d = p.depth ?? 50;
    next.sketches[0].profile = [
      [0, 0],
      [w, 0],
      [w, d],
      [0, d],
    ];
  } else if (next.template === "cylinder") {
    const r = p.radius ?? (p.width ?? 50) / 2;
    next.sketches[0].profile = [
      [r, 0],
      [0, r],
      [-r, 0],
      [0, -r],
      [r, 0],
    ];
  } else if (next.template === "chair") {
    const w = p.width ?? 80;
    const d = p.depth ?? 60;
    next.sketches[0].profile = [
      [0, 0],
      [w, 0],
      [w, d],
      [0, d],
    ];
  } else if (next.template === "bracket") {
    const w = p.width ?? 100;
    const d = p.depth ?? 60;
    const wall = p.wall_thickness ?? 10;
    next.sketches[0].profile = [
      [0, 0],
      [w, 0],
      [w, wall],
      [wall, wall],
      [wall, d],
      [0, d],
      [0, 0],
    ];
  }

  for (const op of next.operations) {
    if (op.op === "extrude") {
      if (next.template === "chair") {
        op.distance = p.seat_thickness ?? op.distance;
      } else {
        op.distance = p.height ?? op.distance;
      }
    }
    if (op.op === "fillet") {
      op.radius = p.fillet_radius ?? op.radius;
    }
  }

  return next;
}

export function compileCADSpecCode(spec: CADSpec): string {
  const synced = syncSketchesFromParameters(spec);
  const sketch = synced.sketches[0];
  const profileJson = JSON.stringify(sketch.profile);
  const height =
    synced.operations.find((o) => o.op === "extrude")?.distance ??
    synced.parameters.height ??
    30;
  const fillet =
    synced.operations.find((o) => o.op === "fillet")?.radius ??
    synced.parameters.fillet_radius ??
    0;

  if (synced.template === "cylinder") {
    const r = synced.parameters.radius ?? 25;
    return `
      const radius = ${r};
      const height = ${height};
      let base = drawCircle(radius).sketchOnPlane("XY");
      let shape = base.extrude(height);
      return shape;
    `;
  }

  if (synced.template === "chair") {
    const sw = synced.parameters.width ?? 80;
    const sd = synced.parameters.depth ?? 60;
    const st = synced.parameters.seat_thickness ?? 5;
    const lw = synced.parameters.leg_width ?? synced.parameters.wall_thickness ?? 8;
    const lh = synced.parameters.height ?? 45;
    return `
      const sw = ${sw}, sd = ${sd}, st = ${st}, lw = ${lw}, lh = ${lh};
      const leg = draw().hLine(lw).vLine(lw).close().sketchOnPlane("XY").extrude(lh);
      const leg2 = leg.translate(sw - lw, 0, 0);
      const leg3 = leg.translate(0, sd - lw, 0);
      const leg4 = leg.translate(sw - lw, sd - lw, 0);
      const seat = draw().hLine(sw).vLine(sd).close().sketchOnPlane("XY").extrude(st).translate(0, 0, lh);
      return seat.fuse(leg).fuse(leg2).fuse(leg3).fuse(leg4);
    `;
  }

  return `
    const profile = ${profileJson};
    const height = ${height};
    const fillet = ${fillet};
    let sketch = draw().movePointerTo(profile[0]);
    for (let i = 1; i < profile.length; i++) {
      sketch = sketch.lineTo(profile[i]);
    }
    sketch = sketch.close().sketchOnPlane("${sketch.plane}");
    let shape = sketch.extrude(height);
    if (fillet > 0.01) {
      try {
        shape = shape.fillet(fillet, (e) => e.inDirection("Z"));
      } catch (_) {
        /* fillet may fail on complex profiles */
      }
    }
    return shape;
  `;
}

export function getEditableParameters(spec: CADSpec): string[] {
  switch (spec.template) {
    case "cylinder":
      return ["radius", "height"];
    case "chair":
      return ["width", "depth", "height", "leg_width", "seat_thickness"];
    case "bracket":
      return ["width", "depth", "height", "wall_thickness", "fillet_radius"];
    case "profile_extrude":
      return ["height"];
    default:
      return ["width", "depth", "height", "fillet_radius"];
  }
}
