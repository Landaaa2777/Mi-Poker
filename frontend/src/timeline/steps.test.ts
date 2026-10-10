import { describe, expect, it } from "vitest";
import { isOpeningBet } from "../format";
import type { GameState, HandEvent } from "../types";
import { sessions, transitions } from "./fixtures/sessions";
import { frameFromState, type Frame } from "./frame";
import { buildSteps, continuesHand, dealOrder, type Step } from "./steps";

const all = transitions().map((transition) => ({
  ...transition,
  steps: buildSteps(transition.previous, transition.next),
}));
const newHands = all.filter((transition) => transition.steps[0].kind === "new_hand");

function totalChips(state: GameState): number {
  return state.config.starting_stack * state.seats.length;
}

/** Lo que tiene que cuadrar entre mis cuentas y el servidor. */
function ledger(frame: Frame) {
  return {
    board: frame.board,
    pot: frame.pot,
    events: frame.events,
    smallBlindSeat: frame.smallBlindSeat,
    bigBlindSeat: frame.bigBlindSeat,
    seats: frame.seats.map(({ stack, bet, cards, action, won, handName }) => ({
      stack,
      bet,
      cards,
      action,
      won,
      handName,
    })),
  };
}

function eventSteps(steps: Step[]): HandEvent[] {
  return steps.flatMap((step) => (step.kind === "event" ? [step.event] : []));
}

describe("partidas grabadas", () => {
  it("contienen los casos difíciles", () => {
    const cases = new Set(sessions.flatMap((session) => session.cases));
    for (const expected of [
      "side_pots",
      "burst",
      "complete_on_arrival",
      "restart_same_number",
      "refund",
      "human_fold",
      "fold_win",
      "showdown",
    ]) {
      expect(cases).toContain(expected);
    }
    expect(all.length).toBeGreaterThan(100);
    expect(newHands.length).toBeGreaterThanOrEqual(18);
  });
});

describe("buildSteps", () => {
  it("termina siempre exactamente en el estado del servidor", () => {
    for (const { next, steps } of all) {
      const last = steps.at(-1)!;
      expect(last.kind).toBe("settle");
      expect(last.frame).toEqual(frameFromState(next));
      expect(steps.filter((step) => step.kind === "settle")).toHaveLength(1);
    }
  });

  it("llega a las mismas fichas, apuestas y cartas que el servidor usando solo los sucesos", () => {
    let checked = 0;
    for (const { steps } of all) {
      if (steps.length < 2) continue;
      const mine = steps.at(-2)!.frame;
      const server = steps.at(-1)!.frame;
      expect(ledger(mine)).toEqual(ledger(server));
      mine.seats.forEach((seat, index) => {
        // El servidor marca "out" al eliminado cuando acaba la mano; yo aún lo veo all-in.
        const expected = server.seats[index].status;
        if (expected !== "out") expect(seat.status).toBe(expected);
      });
      checked += 1;
    }
    expect(checked).toBeGreaterThan(100);
  });

  it("conserva las fichas en todos los pasos", () => {
    for (const { next, steps } of all) {
      for (const { frame } of steps) {
        const stacks = frame.seats.reduce((sum, seat) => sum + seat.stack, 0);
        expect(stacks + frame.pot).toBe(totalChips(next));
        for (const seat of frame.seats) {
          expect(seat.stack).toBeGreaterThanOrEqual(0);
          expect(seat.bet).toBeGreaterThanOrEqual(0);
        }
        expect(frame.pot).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("revela el registro y la mesa en orden, sin adelantarse al servidor", () => {
    for (const { next, steps } of all) {
      let events = 0;
      let board = 0;
      for (const { frame } of steps) {
        expect(frame.events).toEqual(next.events.slice(0, frame.events.length));
        expect(frame.board).toEqual(next.board.slice(0, frame.board.length));
        expect(frame.events.length).toBeGreaterThanOrEqual(events);
        expect(frame.board.length).toBeGreaterThanOrEqual(board);
        events = frame.events.length;
        board = frame.board.length;
      }
    }
  });

  it("genera un paso por cada suceso nuevo, en el mismo orden", () => {
    for (const { previous, next, steps } of all) {
      const from = previous && continuesHand(previous, next) ? previous.events.length : 0;
      const expected = next.events.slice(from).filter((event) => event.kind !== "board");
      expect(eventSteps(steps)).toEqual(expected);
    }
  });

  it("no enseña las cartas de un bot antes de que las muestre", () => {
    for (const { steps } of all) {
      for (const { frame } of steps) {
        for (const seat of frame.seats) {
          if (seat.isHuman || seat.cards.every((card) => card === null)) continue;
          const shown = frame.events.find(
            (event) => event.kind === "show" && event.seat === seat.seat,
          );
          expect(shown?.cards).toEqual(seat.cards);
        }
      }
    }
  });
});

describe("mano nueva", () => {
  it("empieza con la mesa limpia", () => {
    for (const { steps } of newHands) {
      const { frame } = steps[0];
      expect(frame.board).toEqual([]);
      expect(frame.pot).toBe(0);
      expect(frame.events).toEqual([]);
      expect(frame.actingSeat).toBeNull();
      for (const seat of frame.seats) {
        expect(seat).toMatchObject({ bet: 0, cards: [], action: null, won: 0, handName: null });
      }
    }
  });

  it("pone las ciegas y después reparte una carta a cada uno, dos veces, desde la izquierda del botón", () => {
    for (const { next, steps } of newHands) {
      expect(steps[1]).toMatchObject({ kind: "event", event: { kind: "small_blind" } });
      expect(steps[2]).toMatchObject({ kind: "event", event: { kind: "big_blind" } });

      const order = dealOrder(next);
      const deals = steps.slice(3, 3 + 2 * order.length);
      expect(deals.map((step) => step.kind === "deal" && step.seat)).toEqual([...order, ...order]);
      expect(steps[3 + 2 * order.length].kind).not.toBe("deal");

      // El botón recibe la última carta de cada vuelta.
      expect(order.at(-1)).toBe(next.button_seat);
      const button = next.button_seat!;
      const expectedFirst = order.find((seat) => seat > button) ?? order[0];
      expect(order[0]).toBe(expectedFirst);

      const dealt = deals.at(-1)!.frame;
      for (const seat of dealt.seats) {
        const inHand = order.includes(seat.seat);
        expect(seat.cards).toHaveLength(inHand ? 2 : 0);
        if (seat.isHuman && inHand) expect(seat.cards).toEqual(next.hole_cards);
        if (!seat.isHuman) expect(seat.cards.every((card) => card === null)).toBe(true);
      }
    }
  });

  it("se detecta al reiniciar aunque el número de mano se repita", () => {
    const restarts = all.filter(
      ({ previous, next }) =>
        previous !== null &&
        previous.hand_number === next.hand_number &&
        !continuesHand(previous, next),
    );
    expect(restarts.length).toBeGreaterThan(0);
    for (const { steps } of restarts) expect(steps[0].kind).toBe("new_hand");
  });

  it("se reproduce entera aunque llegue terminada en el primer mensaje", () => {
    const complete = newHands.filter(({ next }) => !next.hand_in_progress);
    expect(complete.length).toBeGreaterThan(0);
    for (const { next, steps } of complete) {
      const kinds = steps.map((step) => step.kind);
      expect(kinds.filter((kind) => kind === "board")).toHaveLength(5);
      expect(kinds.indexOf("deal")).toBeLessThan(kinds.indexOf("board"));
      expect(eventSteps(steps).filter((event) => event.kind === "win").length).toBeGreaterThan(0);
      expect(steps.at(-1)!.frame.pot).toBe(0);
      expect(steps.at(-1)!.frame.seats.map((seat) => seat.won)).toEqual(
        next.seats.map((seat) => next.result!.payouts[String(seat.seat)] ?? 0),
      );
    }
  });
});

describe("misma mano", () => {
  it("solo añade los sucesos nuevos y no vuelve a repartir", () => {
    const continued = all.filter(({ steps }) => steps[0].kind !== "new_hand");
    expect(continued.length).toBeGreaterThan(50);
    for (const { steps } of continued) {
      expect(steps.some((step) => step.kind === "deal" || step.kind === "new_hand")).toBe(false);
    }
  });

  it("saca el flop de una en una y lo apunta en el registro con la tercera carta", () => {
    const flops = all.flatMap(({ steps }) => {
      const cards = steps.filter((step) => step.kind === "board" && step.street === "flop");
      return cards.length > 0 ? [cards] : [];
    });
    expect(flops.length).toBeGreaterThan(5);
    for (const cards of flops) {
      expect(cards.map((step) => step.frame.board.length)).toEqual([1, 2, 3]);
      const logged = cards.map((step) => step.frame.events.at(-1)?.kind === "board");
      expect(logged).toEqual([false, false, true]);
      for (const { frame } of cards) {
        expect(frame.phase).toBe("flop");
        expect(frame.seats.every((seat) => seat.bet === 0 && seat.action === null)).toBe(true);
      }
    }
  });

  it("resalta a quien acaba de jugar", () => {
    for (const { steps } of all) {
      for (const step of steps) {
        if (step.kind !== "event") continue;
        const acting = step.event.kind === "action" ? step.event.seat : null;
        expect(step.frame.actingSeat).toBe(acting);
      }
    }
  });

  it("no genera pasos nuevos si el estado se repite", () => {
    const state = sessions[0].states[5];
    const steps = buildSteps(state, state);
    expect(steps.map((step) => step.kind)).toEqual(["settle"]);
  });
});

describe("isOpeningBet", () => {
  const event = (kind: HandEvent["kind"], action = ""): HandEvent => ({
    kind,
    seat: 0,
    amount: 10,
    action,
    cards: [],
    all_in: false,
  });

  it("preflop nunca abre: las ciegas ya son una apuesta", () => {
    const events = [event("small_blind"), event("big_blind"), event("action", "raise")];
    expect(isOpeningBet(events, 2)).toBe(false);
  });

  it("después del flop abre la primera apuesta y las siguientes suben", () => {
    const events = [
      event("small_blind"),
      event("big_blind"),
      event("action", "call"),
      event("board", "flop"),
      event("action", "check"),
      event("action", "raise"),
      event("action", "raise"),
    ];
    expect(isOpeningBet(events, 5)).toBe(true);
    expect(isOpeningBet(events, 6)).toBe(false);
  });
});
