import { describe, expect, it } from "vitest";
import { total } from "../../shared/chips/chips";
import { tableChips } from "./chips";
import { transitions } from "./timeline/fixtures/sessions";
import { buildSteps } from "./timeline/steps";

const steps = transitions().flatMap((transition) => buildSteps(transition.previous, transition.next));

describe("fichas en la mesa de poker", () => {
  it("cuadran siempre con las apuestas, el bote y lo ganado de cada paso", () => {
    for (const { frame } of steps) {
      const chips = tableChips(frame);
      const bets = frame.seats.reduce((sum, seat) => sum + seat.bet, 0);
      for (const seat of frame.seats) {
        expect(total(chips.bets.get(seat.seat) ?? [])).toBe(seat.bet);
        expect(total(chips.won.get(seat.seat) ?? [])).toBe(seat.won);
      }
      expect(total(chips.pot)).toBe(Math.max(0, frame.pot - bets));
    }
  });

  it("cada apuesta pone fichas encima de las que ya había en esa ronda", () => {
    let grew = 0;
    for (let index = 1; index < steps.length; index++) {
      const before = tableChips(steps[index - 1].frame);
      const after = tableChips(steps[index].frame);
      for (const [seat, chips] of after.bets) {
        const previous = before.bets.get(seat) ?? [];
        if (previous.length === 0 || total(chips) <= total(previous)) continue;
        if (steps[index].kind === "settle") continue; // el estado del servidor puede saltar
        expect(chips.slice(0, previous.length)).toEqual(previous);
        grew += 1;
      }
    }
    expect(grew).toBeGreaterThan(10);
  });

  it("al cerrar la ronda las apuestas van al bote y este crece", () => {
    let collected = 0;
    for (let index = 1; index < steps.length; index++) {
      if (steps[index].kind !== "board") continue;
      const before = tableChips(steps[index - 1].frame);
      const after = tableChips(steps[index].frame);
      const bets = [...before.bets.values()].reduce((sum, chips) => sum + total(chips), 0);
      if (bets === 0) continue;
      expect(after.bets.size).toBe(0);
      expect(total(after.pot)).toBe(total(before.pot) + bets);
      collected += 1;
    }
    expect(collected).toBeGreaterThan(3);
  });
});
