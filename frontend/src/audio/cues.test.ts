import { describe, expect, it } from "vitest";
import { transitions } from "../timeline/fixtures/sessions";
import { buildSteps, type Step } from "../timeline/steps";
import { cueForSkipped, cueForStep } from "./cues";
import type { EffectName } from "./effects";

const batches = transitions().map(({ previous, next }) => buildSteps(previous, next));
const steps = batches.flat();

function cuesWhere(predicate: (step: Step) => boolean): Set<EffectName | null> {
  return new Set(steps.filter(predicate).map(cueForStep));
}

const action = (name: string, allIn: boolean) => (step: Step) =>
  step.kind === "event" &&
  step.event.kind === "action" &&
  step.event.action === name &&
  step.event.all_in === allIn;

describe("cueForStep", () => {
  it("cada carta repartida y cada carta que se voltea tiene su sonido", () => {
    expect(cuesWhere((step) => step.kind === "deal")).toEqual(new Set(["deal"]));
    expect(cuesWhere((step) => step.kind === "board")).toEqual(new Set(["flip"]));
    expect(cuesWhere((step) => step.kind === "event" && step.event.kind === "show")).toEqual(
      new Set(["flip"]),
    );
  });

  it("distingue pasar, igualar, subir, retirarse y all-in", () => {
    expect(cuesWhere(action("check", false))).toEqual(new Set(["check"]));
    expect(cuesWhere(action("call", false))).toEqual(new Set(["chips"]));
    expect(cuesWhere(action("raise", false))).toEqual(new Set(["raise"]));
    expect(cuesWhere(action("fold", false))).toEqual(new Set(["fold"]));
    expect(cuesWhere(action("raise", true))).toEqual(new Set(["allIn"]));
    expect(cuesWhere(action("call", true))).toEqual(new Set(["allIn"]));
  });

  it("las ciegas suenan a fichas", () => {
    const blinds = cuesWhere(
      (step) => step.kind === "event" && step.event.kind.endsWith("_blind"),
    );
    expect(blinds).toEqual(new Set(["chips"]));
  });

  it("ganar el bote suena distinto si lo gano yo", () => {
    const wins = steps.filter((step) => step.kind === "event" && step.event.kind === "win");
    const mine = wins.filter(
      (step) =>
        step.kind === "event" &&
        step.frame.seats.find((seat) => seat.seat === step.event.seat)?.isHuman,
    );
    expect(mine.length).toBeGreaterThan(0);
    expect(mine.length).toBeLessThan(wins.length);
    expect(new Set(mine.map(cueForStep))).toEqual(new Set(["win"]));
    expect(new Set(wins.filter((step) => !mine.includes(step)).map(cueForStep))).toEqual(
      new Set(["winOther"]),
    );
  });

  it("la mesa limpia, el estado final y las devoluciones no suenan", () => {
    const silent = cuesWhere(
      (step) =>
        step.kind === "new_hand" ||
        step.kind === "settle" ||
        (step.kind === "event" && step.event.kind === "refund"),
    );
    expect(silent).toEqual(new Set([null]));
  });
});

describe("cueForSkipped", () => {
  it("resume cada tanda en un solo sonido, el más importante", () => {
    for (const batch of batches) {
      const cues = batch.map(cueForStep).filter((cue) => cue !== null);
      const summary = cueForSkipped(batch);
      if (cues.length === 0) expect(summary).toBeNull();
      else expect(cues).toContain(summary);
      if (cues.includes("win")) expect(summary).toBe("win");
      else if (cues.includes("winOther")) expect(summary).toBe("winOther");
      else if (cues.includes("allIn")) expect(summary).toBe("allIn");
    }
  });

  it("no suena nada si no hay pasos con sonido", () => {
    expect(cueForSkipped([])).toBeNull();
    expect(cueForSkipped(batches[0].filter((step) => step.kind === "settle"))).toBeNull();
  });
});
