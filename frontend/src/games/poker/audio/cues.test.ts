import { describe, expect, it } from "vitest";
import { transitions } from "../timeline/fixtures/sessions";
import { buildSteps, type Step } from "../timeline/steps";
import { cueForSkipped, cuesForStep } from "./cues";

const batches = transitions().map(({ previous, next }) => buildSteps(previous, next));
const steps = batches.flat();

const names = (step: Step) => cuesForStep(step).map((cue) => cue.name).join("+");

/** Las combinaciones de sonidos distintas que producen los pasos que cumplen la condición. */
function soundsWhere(predicate: (step: Step) => boolean): Set<string> {
  return new Set(steps.filter(predicate).map(names));
}

const action = (name: string, allIn: boolean) => (step: Step) =>
  step.kind === "event" &&
  step.event.kind === "action" &&
  step.event.action === name &&
  step.event.all_in === allIn;

const isMine = (step: Step, seat: number | null) =>
  step.frame.seats.find((candidate) => candidate.seat === seat)?.isHuman === true;

describe("cuesForStep", () => {
  it("cada carta repartida suena al salir; las mías, además, al voltearse", () => {
    const mine = (step: Step) => step.kind === "deal" && isMine(step, step.seat);
    const theirs = (step: Step) => step.kind === "deal" && !isMine(step, step.seat);
    expect(soundsWhere(theirs)).toEqual(new Set(["deal"]));
    expect(soundsWhere(mine)).toEqual(new Set(["deal+flip"]));
  });

  it("las cartas comunitarias salen del mazo y se voltean en el aire", () => {
    expect(soundsWhere((step) => step.kind === "board")).toEqual(new Set(["deal+flip"]));
  });

  it("en el showdown suena cada carta que se enseña", () => {
    const shows = soundsWhere((step) => step.kind === "event" && step.event.kind === "show");
    expect(shows).toEqual(new Set(["flip"]));
  });

  it("distingue pasar, igualar, subir, retirarse y all-in", () => {
    expect(soundsWhere(action("check", false))).toEqual(new Set(["check"]));
    expect(soundsWhere(action("call", false))).toEqual(new Set(["chips"]));
    expect(soundsWhere(action("raise", false))).toEqual(new Set(["raise"]));
    expect(soundsWhere(action("fold", false))).toEqual(new Set(["fold"]));
    expect(soundsWhere(action("raise", true))).toEqual(new Set(["allIn"]));
    expect(soundsWhere(action("call", true))).toEqual(new Set(["allIn"]));
  });

  it("las ciegas suenan a fichas", () => {
    const blinds = soundsWhere(
      (step) => step.kind === "event" && step.event.kind.endsWith("_blind"),
    );
    expect(blinds).toEqual(new Set(["chips"]));
  });

  it("ganar el bote suena distinto si lo gano yo", () => {
    const wins = steps.filter((step) => step.kind === "event" && step.event.kind === "win");
    const mine = wins.filter((step) => step.kind === "event" && isMine(step, step.event.seat));
    expect(mine.length).toBeGreaterThan(0);
    expect(mine.length).toBeLessThan(wins.length);
    expect(new Set(mine.map(names))).toEqual(new Set(["win"]));
    expect(new Set(wins.filter((step) => !mine.includes(step)).map(names))).toEqual(
      new Set(["winOther"]),
    );
  });

  it("la mesa limpia, el estado final y las devoluciones no suenan", () => {
    const silent = soundsWhere(
      (step) =>
        step.kind === "new_hand" ||
        step.kind === "settle" ||
        (step.kind === "event" && step.event.kind === "refund"),
    );
    expect(silent).toEqual(new Set([""]));
  });

  it("las fichas suenan al llegar al bote y ningún sonido se retrasa más de lo que dura un paso", () => {
    for (const step of steps) {
      for (const cue of cuesForStep(step)) {
        expect(cue.delay).toBeGreaterThanOrEqual(0);
        expect(cue.delay).toBeLessThanOrEqual(0.5);
        if (cue.name === "chips") expect(cue.delay).toBeGreaterThan(0);
      }
    }
  });
});

describe("cueForSkipped", () => {
  it("resume cada tanda en un solo sonido, el más importante", () => {
    for (const batch of batches) {
      const all = batch.flatMap((step) => cuesForStep(step).map((cue) => cue.name));
      const summary = cueForSkipped(batch);
      if (all.length === 0) expect(summary).toBeNull();
      else expect(all).toContain(summary);
      if (all.includes("win")) expect(summary).toBe("win");
      else if (all.includes("winOther")) expect(summary).toBe("winOther");
      else if (all.includes("allIn")) expect(summary).toBe("allIn");
    }
  });

  it("no suena nada si no hay pasos con sonido", () => {
    expect(cueForSkipped([])).toBeNull();
    expect(cueForSkipped(batches[0].filter((step) => step.kind === "settle"))).toBeNull();
  });
});
