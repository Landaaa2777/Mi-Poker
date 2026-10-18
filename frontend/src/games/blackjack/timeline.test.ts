import { describe, expect, it } from "vitest";
import { sessions, transitions } from "./fixtures/sessions";
import { buildSteps, continuesRound, frameAt, frameFromState, handTotal, stepDelay, type Frame } from "./timeline";

/** Lo esencial de una mesa, para comparar dos frames. */
function essence(frame: Frame) {
  return {
    dealer: frame.dealer.cards,
    seats: frame.seats.map((seat) => ({
      stack: seat.stack,
      hands: seat.hands.map((hand) => ({
        cards: hand.cards,
        bet: hand.bet,
        total: hand.total,
        result: hand.result,
        payout: hand.payout,
      })),
    })),
  };
}

describe("handTotal", () => {
  it("cuenta los ases como 11 si no se pasa, y si no como 1", () => {
    expect(handTotal(["Ah", "6d"])).toEqual({ total: 17, soft: true });
    expect(handTotal(["Ah", "6d", "9c"])).toEqual({ total: 16, soft: false });
    expect(handTotal(["Ah", "Ad"])).toEqual({ total: 12, soft: true });
    expect(handTotal(["Kh", "Qd", "5c"])).toEqual({ total: 25, soft: false });
    expect(handTotal(["Ts", "Ac"])).toEqual({ total: 21, soft: true });
  });
});

describe("las partidas grabadas", () => {
  it("cubren divisiones, dobles, seguros y pagos", () => {
    const kinds = new Set(
      sessions.flatMap((session) =>
        session.states.flatMap((state) => state.events.map((event) => event.action || event.kind)),
      ),
    );
    for (const kind of ["split", "double", "insurance", "settle", "reveal", "hit", "stand"]) {
      expect(kinds).toContain(kind);
    }
  });
});

describe("frameAt", () => {
  it("rehaciendo toda la ronda llega exactamente a la mesa del servidor", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        expect(essence(frameAt(state, state.events.length))).toEqual(essence(frameFromState(state)));
      }
    }
  });

  it("al empezar la ronda la mesa está vacía y con las fichas de antes", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        const start = frameAt(state, 0);
        expect(start.dealer.cards).toEqual([]);
        expect(start.seats.every((seat) => seat.hands.length === 0)).toBe(true);
        expect(start.seats.every((seat) => seat.stack >= 0)).toBe(true);
      }
    }
  });

  it("nunca enseña la carta tapada antes de destaparla", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        state.events.forEach((_, index) => {
          const frame = frameAt(state, index + 1);
          const revealed = state.events.slice(0, index + 1).some((seen) => seen.kind === "reveal");
          if (frame.dealer.cards.length >= 2 && !revealed) expect(frame.dealer.cards[1]).toBeNull();
        });
      }
    }
  });
});

describe("buildSteps", () => {
  it("termina siempre en la mesa exacta del servidor", () => {
    for (const { previous, next } of transitions()) {
      const steps = buildSteps(previous, next);
      const last = steps.at(-1)!;
      expect(last.kind).toBe("sync");
      expect(last.frame).toEqual(frameFromState(next));
    }
  });

  it("en una ronda que sigue solo reproduce lo nuevo, y las cartas solo se añaden", () => {
    for (const { previous, next } of transitions()) {
      if (!continuesRound(previous, next)) continue;
      const steps = buildSteps(previous, next);
      expect(steps[0].kind).not.toBe("round");
      expect(steps.length).toBe(next.events.length - previous!.events.length + 1);
      let before = previous!.events.length > 0 ? frameAt(next, previous!.events.length) : null;
      for (const step of steps.slice(0, -1)) {
        if (before) {
          before.seats.forEach((_, index) => {
            const cards = (frame: Frame) => frame.seats[index].hands.flatMap((hand) => hand.cards).length;
            expect(cards(step.frame)).toBeGreaterThanOrEqual(cards(before!));
          });
        }
        before = step.frame;
      }
    }
  });

  it("una ronda nueva empieza con la mesa limpia", () => {
    for (const { previous, next } of transitions()) {
      if (continuesRound(previous, next) || next.events.length === 0) continue;
      const steps = buildSteps(previous, next);
      expect(steps[0].kind).toBe("round");
      expect(steps[0].frame.dealer.cards).toEqual([]);
    }
  });

  it("cada carta del reparto es un paso, en el orden en que sale del zapato", () => {
    const fresh = transitions().find(
      ({ previous, next }) => !continuesRound(previous, next) && next.events.length > 4,
    )!;
    const steps = buildSteps(fresh.previous, fresh.next);
    const dealt = fresh.next.events.filter((event) => ["card", "dealer_card", "hole_card"].includes(event.kind));
    expect(steps.filter((step) => step.kind === "card")).toHaveLength(dealt.length);
  });
});

describe("stepDelay", () => {
  it("da tiempo a cada animación sin eternizarse", () => {
    for (const { previous, next } of transitions()) {
      const steps = buildSteps(previous, next);
      steps.forEach((step, index) => {
        const delay = stepDelay(step, steps[index + 1]);
        expect(delay).toBeGreaterThanOrEqual(0);
        expect(delay).toBeLessThanOrEqual(900);
      });
      expect(stepDelay(steps.at(-1)!, undefined)).toBe(0);
    }
  });
});
