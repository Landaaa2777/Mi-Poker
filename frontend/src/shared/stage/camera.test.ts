import { describe, expect, it } from "vitest";
import { onPlane, project, stageFor, unproject, type Camera } from "./camera";

const CAMERA: Camera = { tilt: 40, distance: 1500, eye: 0.5, top: 20, bottom: 30 };
const stage = stageFor(1120, 640, CAMERA);

/** Lo mismo que hace el navegador: girar el tapete sobre su borde cercano y proyectar. */
function browser(x: number, y: number) {
  const tilt = (CAMERA.tilt * Math.PI) / 180;
  const planeY = y * stage.stretch - stage.planeHeight; // respecto al borde cercano
  const Y = planeY * Math.cos(tilt);
  const Z = planeY * Math.sin(tilt);
  const k = stage.distance / (stage.distance - Z);
  const originX = stage.width / 2;
  const originY = stage.originY - stage.base; // el punto de fuga, respecto al borde cercano
  return {
    x: originX + (x - originX) * k,
    y: stage.base + originY + (Y - originY) * k,
  };
}

describe("cámara 3D", () => {
  it("proyecta igual que la perspectiva del navegador", () => {
    for (const [x, y] of [[0, 0], [560, 320], [1120, 640], [200, 100], [900, 600]]) {
      const seen = project(stage, { x, y });
      const expected = browser(x, y);
      expect(seen.x).toBeCloseTo(expected.x, 6);
      expect(seen.y).toBeCloseTo(expected.y, 6);
    }
  });

  it("deja el borde cercano en su sitio y a tamaño real", () => {
    const near = project(stage, { x: 100, y: 640 });
    expect(near).toEqual({ x: 100, y: stage.base, depth: 1 });
  });

  it("encoge y junta lo que está lejos", () => {
    const far = project(stage, { x: 0, y: 0 });
    const middle = project(stage, { x: 0, y: 320 });
    expect(far.depth).toBeLessThan(middle.depth);
    expect(middle.depth).toBeLessThan(1);
    expect(far.x).toBeGreaterThan(middle.x); // el borde izquierdo se acerca al centro
    expect(far.y).toBeLessThan(middle.y);
  });

  it("el borde lejano queda justo bajo el margen de arriba", () => {
    expect(project(stage, { x: 560, y: 0 }).y).toBeCloseTo(CAMERA.top, 6);
    expect(stage.stageHeight).toBeCloseTo(stage.base + CAMERA.bottom, 6);
    // Más baja que la mesa 2D: la perspectiva la acorta.
    expect(stage.stageHeight).toBeLessThan(640 + CAMERA.top + CAMERA.bottom);
  });

  it("deshace la proyección", () => {
    for (const [x, y] of [[0, 0], [560, 320], [1120, 640], [37, 512], [999, 3], [500, 700]]) {
      const back = unproject(stage, project(stage, { x, y }));
      expect(back.x).toBeCloseTo(x, 6);
      expect(back.y).toBeCloseTo(y, 6);
    }
  });

  it("estira el tapete lo que la inclinación lo acorta", () => {
    expect(onPlane(stage, { x: 10, y: 100 })).toEqual({ x: 10, y: 100 * stage.stretch });
    expect(stage.planeHeight * Math.cos((CAMERA.tilt * Math.PI) / 180)).toBeCloseTo(640, 6);
    expect(stage.planeTop + stage.planeHeight).toBeCloseTo(stage.base, 6);
  });
});
