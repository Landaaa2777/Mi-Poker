import { describe, expect, it } from "vitest";
import { cardName } from "./cardArt";
import { describeEvent } from "./describe";
import { sessions } from "./fixtures/sessions";
import { frameAt } from "./timeline";

describe("cardName", () => {
  it("nombra cada carta en español", () => {
    expect(cardName({ id: 1, kind: "number", color: "panal", number: 7 })).toBe("Panal 7");
    expect(cardName({ id: 2, kind: "pausa", color: "halo", number: null })).toBe("Halo Pausa");
    expect(cardName({ id: 3, kind: "carga", color: "astro", number: null })).toBe("Astro Carga +2");
    expect(cardName({ id: 4, kind: "camaleon4", color: null, number: null })).toBe("Camaleón +4");
  });
});

describe("describeEvent", () => {
  it("cuenta cada suceso de las partidas grabadas sin dejar huecos", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        const frame = frameAt(state, state.events.length);
        state.events.forEach((event, index) => {
          const line = describeEvent(index, frame, state.human_seat);
          if (event.kind === "deal" && event.seat !== state.human_seat) expect(line).toBeNull();
          else expect(line && line.length > 3).toBe(true);
          expect(line ?? "").not.toContain("undefined");
          expect(line ?? "").not.toContain("null");
        });
      }
    }
  });

  it("habla de mí en segunda persona", () => {
    const state = sessions[0].states.at(-1)!;
    const frame = frameAt(state, state.events.length);
    const mine = state.events.findIndex((e) => e.kind === "play" && e.seat === state.human_seat);
    const theirs = state.events.findIndex((e) => e.kind === "play" && e.seat !== state.human_seat);
    expect(describeEvent(mine, frame, state.human_seat)).toMatch(/^Juegas /);
    expect(describeEvent(theirs, frame, state.human_seat)).toMatch(/^\S.* juega /);
  });
});
