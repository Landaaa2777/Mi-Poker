import { describe, expect, it } from "vitest";
import { sessions, transitions } from "./fixtures/sessions";
import { buildSteps, continuesRound, frameAt, frameFromState, stepDelay, type Frame } from "./timeline";

/** Lo esencial de una mesa, para comparar dos frames. */
function essence(frame: Frame) {
  return {
    hand: frame.hand.map((card) => card.id),
    counts: frame.players.map((player) => player.count),
    top: frame.top?.id ?? null,
    color: frame.color,
    direction: frame.direction,
    drawCount: frame.drawCount,
    discardCount: frame.discardCount,
  };
}

describe("las partidas grabadas", () => {
  it("cubren repartos, jugadas, robos, saltos, cambios de sentido y avisos", () => {
    const kinds = new Set(sessions.flatMap((s) => s.states.flatMap((state) => state.events.map((e) => e.kind))));
    for (const kind of ["deal", "start", "play", "draw", "skip", "reverse", "last", "round_over"]) {
      expect(kinds).toContain(kind);
    }
  });

  it("siempre suman 108 cartas", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        const inHands = state.players.reduce((sum, player) => sum + player.count, 0);
        expect(inHands + state.draw_count + state.discard_count).toBe(108);
        expect(state.hand).toHaveLength(state.players[state.human_seat].count);
      }
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

  it("antes del reparto la mesa está vacía y con el mazo entero", () => {
    const state = sessions[0].states[0];
    const start = frameAt(state, 0);
    expect(start.hand).toEqual([]);
    expect(start.top).toBeNull();
    expect(start.drawCount).toBe(108);
  });

  it("solo muestra mis cartas, nunca las de los demás", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        for (const event of state.events) {
          if (event.seat !== state.human_seat) expect(event.cards).toEqual([]);
        }
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

  it("en una ronda que sigue solo reproduce lo nuevo", () => {
    for (const { previous, next } of transitions()) {
      if (!continuesRound(previous, next)) continue;
      const steps = buildSteps(previous, next);
      expect(steps[0].kind).not.toBe("round");
      expect(steps.length).toBeLessThanOrEqual(next.events.length - previous!.events.length + 1);
    }
  });

  it("una ronda nueva empieza limpia y reparte jugador a jugador", () => {
    for (const { previous, next } of transitions()) {
      if (continuesRound(previous, next)) continue;
      const steps = buildSteps(previous, next);
      expect(steps[0].kind).toBe("round");
      const deals = steps.filter((step) => step.kind === "deal");
      expect(deals).toHaveLength(next.players.length);
    }
  });

  it("cada carta jugada es un paso que la lleva al descarte", () => {
    for (const { previous, next } of transitions()) {
      const steps = buildSteps(previous, next);
      for (const step of steps) {
        if (step.kind === "play") expect(step.frame.top).not.toBeNull();
      }
    }
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
