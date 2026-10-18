import { describe, expect, it } from "vitest";
import { describeEvent, handProfit, totalLabel } from "./describe";
import { sessions } from "./fixtures/sessions";
import { frameAt } from "./timeline";

describe("totalLabel", () => {
  it("enseña los dos valores de una mano blanda", () => {
    expect(totalLabel(17, true)).toBe("7/17");
    expect(totalLabel(17, false)).toBe("17");
    expect(totalLabel(21, true)).toBe("21");
  });
});

describe("handProfit", () => {
  it("es lo cobrado menos lo apostado", () => {
    expect(handProfit({ bet: 100, payout: 250, result: "blackjack" })).toBe(150);
    expect(handProfit({ bet: 100, payout: 0, result: "lose" })).toBe(-100);
    expect(handProfit({ bet: 100, payout: 100, result: "push" })).toBe(0);
    expect(handProfit({ bet: 100, payout: 0, result: null })).toBe(0);
  });
});

describe("describeEvent", () => {
  it("cuenta cada suceso de las partidas grabadas en una frase", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        const frame = frameAt(state, state.events.length);
        state.events.forEach((event, index) => {
          const line = describeEvent(index, frame, state.human_seat);
          if (event.kind === "split") expect(line).toBeNull();
          else expect(line && line.length > 3).toBe(true);
          expect(line ?? "").not.toContain("undefined");
        });
      }
    }
  });

  it("habla de mí en segunda persona y de los demás en tercera", () => {
    const state = sessions[1].states.find((s) => s.events.some((e) => e.kind === "bet" && e.seat !== s.human_seat))!;
    const mine = state.events.findIndex((e) => e.kind === "bet" && e.seat === state.human_seat);
    const theirs = state.events.findIndex((e) => e.kind === "bet" && e.seat !== state.human_seat);
    const frame = frameAt(state, state.events.length);
    expect(describeEvent(mine, frame, state.human_seat)).toMatch(/^Apuestas \d+$/);
    expect(describeEvent(theirs, frame, state.human_seat)).toMatch(/^\S.* apuesta \d+$/);
  });

  it("la primera carta del crupier se enseña y las siguientes se sacan", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        const frame = frameAt(state, state.events.length);
        const dealer = state.events
          .map((event, index) => ({ event, index }))
          .filter(({ event }) => event.kind === "dealer_card");
        dealer.forEach(({ index }, order) => {
          const line = describeEvent(index, frame, state.human_seat)!;
          expect(line.startsWith(order === 0 ? "El crupier enseña" : "El crupier saca")).toBe(true);
        });
      }
    }
  });
});
