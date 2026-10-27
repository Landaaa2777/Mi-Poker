import { describe, expect, it } from "vitest";
import { clearance, flipFrames, landingTime, settle, slideFrames, throwFrames, throwPath } from "./physics";

/** Los números de un transform: "translate3d(1px, 2px, 3px) rotateZ(4deg)" → [1, 2, 3, 4]. */
function numbers(transform: unknown): number[] {
  return [...String(transform).matchAll(/-?\d+(?:\.\d+)?/g)].map((match) => Number(match[0]));
}

describe("trayectoria de una carta lanzada", () => {
  const path = throwPath();

  it("empieza en el mazo y acaba en su sitio, siempre avanzando", () => {
    expect(path[0].along).toBe(0);
    expect(path.at(-1)!.along).toBeCloseTo(1, 9);
    for (let index = 1; index < path.length; index++) {
      expect(path[index].along).toBeGreaterThanOrEqual(path[index - 1].along);
      expect(path[index].time).toBeGreaterThan(path[index - 1].time);
    }
  });

  it("sube, cae, toca el tapete antes de acabar y termina apoyada", () => {
    const highest = Math.max(...path.map((sample) => sample.height));
    expect(highest).toBeGreaterThan(0.9);
    expect(path.at(-1)!.height).toBe(0);
    const land = landingTime();
    expect(land).toBeGreaterThan(0.25);
    expect(land).toBeLessThan(0.85);
    for (const sample of path) expect(sample.height).toBeGreaterThanOrEqual(0);
  });

  it("frena: al final avanza mucho menos que al principio", () => {
    const first = path[1].along - path[0].along;
    const last = path.at(-1)!.along - path.at(-2)!.along;
    expect(last).toBeLessThan(first / 4);
  });
});

describe("fotogramas", () => {
  it("la carta acaba exactamente en su sitio, sin giro ni escala", () => {
    const { card, shadow } = throwFrames({ from: { x: -300, y: 120 }, height: 50, spin: 30, width: 70, flip: true });
    expect(card[0].offset).toBe(0);
    expect(card.at(-1)!.offset).toBe(1);
    // translate3d(0, 0, 0) rotateZ(0) rotateX(0) rotateY(0) scale(1); el "3" es el de translate3d.
    expect(numbers(card.at(-1)!.transform).map(Math.abs)).toEqual([3, 0, 0, 0, 0, 0, 0, 1]);
    expect(card.at(-1)!.opacity).toBe(1);
    expect(shadow).toHaveLength(card.length);
  });

  it("sale desde el mazo", () => {
    const { card } = throwFrames({ from: { x: -300, y: 120 }, height: 50, spin: 30, width: 70 });
    const [x, y] = numbers(card[0].transform).slice(1);
    expect(x).toBeCloseTo(-300, 1);
    expect(y).toBeCloseTo(120, 1);
  });

  it("al voltearse en el aire nunca atraviesa el tapete", () => {
    for (const frames of [
      throwFrames({ from: { x: 200, y: -80 }, height: 10, spin: -20, width: 90, flip: true }).card,
      flipFrames(90).card,
    ]) {
      for (const frame of frames) {
        const transform = String(frame.transform);
        const lift = Number(/translate(?:3d\([^,]+,[^,]+,|Z\()\s*(-?[\d.]+)px/.exec(transform)![1]);
        const turn = Number(/rotateY\((-?[\d.]+)deg/.exec(transform)![1]);
        expect(lift).toBeGreaterThanOrEqual(clearance(90, turn) - 0.01);
      }
    }
  });

  it("al voltear en el sitio acaba boca arriba y apoyada", () => {
    const last = String(flipFrames(70).card.at(-1)!.transform);
    expect(last).toContain("rotateY(0.00deg)");
    expect(Number(/translateZ\((-?[\d.]+)px/.exec(last)![1])).toBeLessThan(3);
  });

  it("al retirarse se desliza hasta su destino y desaparece", () => {
    const frames = slideFrames({ x: 100, y: -40 }, 25);
    expect(frames[0].opacity).toBe(1);
    expect(frames.at(-1)!.opacity).toBe(0);
    expect(String(frames.at(-1)!.transform)).toContain("translate3d(100.00px, -40.00px, 0.00px)");
  });

  it("el muelle va de 0 a 1 pasándose un poco", () => {
    expect(settle(0)).toBe(0);
    expect(settle(1)).toBe(1);
    const values = Array.from({ length: 50 }, (_, index) => settle(index / 49));
    expect(Math.max(...values)).toBeGreaterThan(1);
    expect(Math.max(...values)).toBeLessThan(1.15);
  });
});
