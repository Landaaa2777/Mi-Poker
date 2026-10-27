import { describe, expect, it } from "vitest";
import { total } from "../../shared/chips/chips";
import { handChips, seatChips } from "./chips";
import { transitions } from "./fixtures/sessions";
import { buildSteps } from "./timeline";

const steps = transitions().flatMap(({ previous, next }) => buildSteps(previous, next));

describe("fichas en la mesa de blackjack", () => {
  it("la apuesta de cada mano está en la mesa mientras se juega", () => {
    for (const { frame } of steps) {
      for (const seat of frame.seats) {
        seatChips(frame, seat).hands.forEach((chips, index) => {
          const hand = seat.hands[index];
          if (hand.result === null) expect(total(chips.bet)).toBe(hand.bet);
        });
      }
    }
  });

  it("al acabar, en la mesa queda exactamente lo que cobra cada mano", () => {
    let settled = 0;
    for (const { frame } of steps) {
      for (const seat of frame.seats) {
        seatChips(frame, seat).hands.forEach((chips, index) => {
          const hand = seat.hands[index];
          if (hand.result === null) return;
          expect(total(chips.bet) + total(chips.win)).toBe(hand.payout);
          settled += 1;
        });
      }
    }
    expect(settled).toBeGreaterThan(20);
  });

  it("doblar pone otra pila igual al lado, sin cambiar las fichas", () => {
    const chips = handChips({ cards: [], bet: 60, total: 20, soft: false, result: null, payout: 0, doubled: true, status: "stood" });
    expect(chips.bet).toEqual([25, 5, 25, 5]);
  });

  it("un blackjack cobra 3 a 2 y lo perdido no deja fichas", () => {
    const base = { cards: [], total: 21, soft: false, doubled: false, status: "stood" };
    expect(total(handChips({ ...base, bet: 100, result: "blackjack", payout: 250 }).win)).toBe(150);
    expect(handChips({ ...base, bet: 100, result: "lose", payout: 0 })).toEqual({ bet: [], win: [] });
    expect(total(handChips({ ...base, bet: 100, result: "surrender", payout: 50 }).bet)).toBe(50);
  });
});
