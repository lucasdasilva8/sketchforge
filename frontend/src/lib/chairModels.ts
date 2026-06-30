export type FurnitureStyle =
  | "ladder_back"
  | "dining"
  | "stool"
  | "armchair"
  | "bench";

export const FURNITURE_STYLE_LABELS: Record<FurnitureStyle, string> = {
  ladder_back: "Ladder-back chair",
  dining: "Dining chair",
  stool: "Stool",
  armchair: "Armchair",
  bench: "Bench",
};

export const FURNITURE_STYLE_OPTIONS = [
  { value: "auto", label: "Auto-detect style" },
  ...Object.entries(FURNITURE_STYLE_LABELS).map(([value, label]) => ({ value, label })),
];

interface ChairParams {
  sw: number;
  sd: number;
  st: number;
  lw: number;
  lh: number;
  bh: number;
}

const MK_BAR = `
  const mkBar = (w, d, h, x, y, z) => {
    let bar = draw().hLine(w).vLine(d).close().sketchOnPlane("XY").extrude(h);
    return bar.translate(x, y, z);
  };
`;

function fuseAll(parts: string[]): string {
  if (parts.length === 0) return "return draw().hLine(1).vLine(1).close().sketchOnPlane('XY').extrude(1);";
  let code = `let body = ${parts[0]};`;
  for (let i = 1; i < parts.length; i++) {
    code += `\nbody = body.fuse(${parts[i]});`;
  }
  return `${code}\nreturn body;`;
}

function compileLadderBack({ sw, sd, st, lw, lh, bh }: ChairParams): string {
  const innerW = `sw - 2 * lw`;
  return `
    const sw = ${sw}, sd = ${sd}, st = ${st}, lw = ${lw}, lh = ${lh}, bh = ${bh};
    ${MK_BAR}
    const slatT = Math.max(lw * 0.35, 3);
    const slatD = Math.max(lw * 0.75, 4);
    const innerW = ${innerW};
    const legFL = mkBar(lw, lw, lh, 0, 0, 0);
    const legFR = mkBar(lw, lw, lh, sw - lw, 0, 0);
    const postBL = mkBar(lw, lw, bh, 0, sd - lw, 0);
    const postBR = mkBar(lw, lw, bh, sw - lw, sd - lw, 0);
    let seat = draw().hLine(sw).vLine(sd).close().sketchOnPlane("XY").extrude(st);
    seat = seat.translate(0, 0, lh);
    const slat1 = mkBar(innerW, slatD, slatT, lw, sd - lw - slatD, lh + (bh - lh) * 0.38);
    const slat2 = mkBar(innerW, slatD, slatT, lw, sd - lw - slatD, lh + (bh - lh) * 0.78);
    const apron = mkBar(innerW, Math.max(lw * 0.65, 4), st * 0.55, lw, 0, lh - st * 0.55);
    ${fuseAll(["seat", "legFL", "legFR", "postBL", "postBR", "slat1", "slat2", "apron"])}
  `;
}

function compileDining({ sw, sd, st, lw, lh, bh }: ChairParams): string {
  const innerW = `sw - 2 * lw`;
  return `
    const sw = ${sw}, sd = ${sd}, st = ${st}, lw = ${lw}, lh = ${lh}, bh = ${bh};
    ${MK_BAR}
    const innerW = ${innerW};
    const legFL = mkBar(lw, lw, lh, 0, 0, 0);
    const legFR = mkBar(lw, lw, lh, sw - lw, 0, 0);
    const legBL = mkBar(lw, lw, lh, 0, sd - lw, 0);
    const legBR = mkBar(lw, lw, lh, sw - lw, sd - lw, 0);
    let seat = draw().hLine(sw).vLine(sd).close().sketchOnPlane("XY").extrude(st);
    seat = seat.translate(0, 0, lh);
    const backPanel = mkBar(innerW, lw * 0.9, bh - lh, lw, sd - lw, lh);
    ${fuseAll(["seat", "legFL", "legFR", "legBL", "legBR", "backPanel"])}
  `;
}

function compileStool({ sw, sd, st, lw, lh }: ChairParams): string {
  return `
    const sw = ${sw}, sd = ${sd}, st = ${st}, lw = ${lw}, lh = ${lh};
    ${MK_BAR}
    const leg1 = mkBar(lw, lw, lh, 0, 0, 0);
    const leg2 = mkBar(lw, lw, lh, sw - lw, 0, 0);
    const leg3 = mkBar(lw, lw, lh, 0, sd - lw, 0);
    const leg4 = mkBar(lw, lw, lh, sw - lw, sd - lw, 0);
    let seat = draw().hLine(sw).vLine(sd).close().sketchOnPlane("XY").extrude(st);
    seat = seat.translate(0, 0, lh);
    ${fuseAll(["seat", "leg1", "leg2", "leg3", "leg4"])}
  `;
}

function compileArmchair({ sw, sd, st, lw, lh, bh }: ChairParams): string {
  const innerW = `sw - 2 * lw`;
  const armW = `lw * 1.4`;
  return `
    const sw = ${sw}, sd = ${sd}, st = ${st}, lw = ${lw}, lh = ${lh}, bh = ${bh};
    ${MK_BAR}
    const innerW = ${innerW};
    const armW = ${armW};
    const legFL = mkBar(lw, lw, lh, 0, 0, 0);
    const legFR = mkBar(lw, lw, lh, sw - lw, 0, 0);
    const legBL = mkBar(lw, lw, lh, 0, sd - lw, 0);
    const legBR = mkBar(lw, lw, lh, sw - lw, sd - lw, 0);
    let seat = draw().hLine(sw).vLine(sd).close().sketchOnPlane("XY").extrude(st);
    seat = seat.translate(0, 0, lh);
    const backPanel = mkBar(innerW, lw, bh - lh, lw, sd - lw, lh);
    const armL = mkBar(armW, sd * 0.55, lw, 0, sd * 0.2, lh);
    const armR = mkBar(armW, sd * 0.55, lw, sw - lw, sd * 0.2, lh);
    ${fuseAll(["seat", "legFL", "legFR", "legBL", "legBR", "backPanel", "armL", "armR"])}
  `;
}

function compileBench({ sw, sd, st, lw, lh, bh }: ChairParams): string {
  return `
    const sw = ${sw}, sd = ${sd}, st = ${st}, lw = ${lw}, lh = ${lh}, bh = ${bh};
    ${MK_BAR}
    const legCount = sw > lh * 4 ? 4 : 3;
    const span = sw - 2 * lw;
    let seat = draw().hLine(sw).vLine(sd).close().sketchOnPlane("XY").extrude(st);
    seat = seat.translate(0, 0, lh);
    const legs = [];
    for (let i = 0; i < legCount; i++) {
      const x = lw + (span * i) / Math.max(legCount - 1, 1);
      legs.push(mkBar(lw, lw, lh, x, 0, 0));
      legs.push(mkBar(lw, lw, lh, x, sd - lw, 0));
    }
    const backRail = mkBar(sw - 2 * lw, lw * 0.8, lw * 0.6, lw, sd - lw, bh - lw * 0.6);
    let body = seat;
    for (const leg of legs) body = body.fuse(leg);
    return body.fuse(backRail);
  `;
}

export function compileChairModel(
  params: Record<string, number | string | undefined>,
): string {
  const p: ChairParams = {
    sw: Number(params.width ?? 80),
    sd: Number(params.depth ?? 60),
    st: Number(params.seat_thickness ?? 5),
    lw: Number(params.leg_width ?? params.wall_thickness ?? 8),
    lh: Number(params.height ?? 45),
    bh: Number(params.back_height ?? Number(params.height ?? 45) * 1.85),
  };
  const style = String(params.furniture_style ?? "dining") as FurnitureStyle;

  switch (style) {
    case "ladder_back":
      return compileLadderBack(p);
    case "stool":
      return compileStool(p);
    case "armchair":
      return compileArmchair(p);
    case "bench":
      return compileBench(p);
    case "dining":
    default:
      return compileDining(p);
  }
}

export function chairStyleDescription(style: string): string {
  return (
    FURNITURE_STYLE_LABELS[style as FurnitureStyle] ??
    FURNITURE_STYLE_LABELS.dining
  );
}
