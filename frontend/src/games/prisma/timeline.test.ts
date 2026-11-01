import { describe, expect, it } from "vitest";
import { sessions, transitions } from "./fixtures/sessions";
import { DECK_SIZES, buildSteps, continuesRound, frameAt, frameFromState, stepDelay, type Frame } from "./timeline";

/** Lo esencial de una mesa, para comparar dos frames. */
function essence(frame: Frame) {
  return {
    hand: frame.hand.map((card) => card.id),
    counts: frame.players.map((player) => player.count),
    out: frame.players.map((player) => player.out),
    // Doble cara: la otra cara que veo de cada mano ajena, carta a carta.
    backs: frame.players.map((player) => player.backs),
    side: frame.side,
    deckBack: frame.deckBack,
    top: frame.top?.id ?? null,
    color: frame.color,
    direction: frame.direction,
    drawCount: frame.drawCount,
    discardCount: frame.discardCount,
    asideCount: frame.asideCount,
    // Las acumuladas solo se siguen paso a paso fuera de las opciones de la casa del Clásico.
    pending: frame.mode === "clasico" ? 0 : frame.pending,
  };
}

const byMode = (mode: string) => sessions.filter((session) => session.states[0].mode === mode);

describe("las partidas grabadas", () => {
  it("cubren repartos, jugadas, robos, saltos, cambios de sentido y avisos", () => {
    const kinds = new Set(sessions.flatMap((s) => s.states.flatMap((state) => state.events.map((e) => e.kind))));
    for (const kind of ["deal", "start", "play", "draw", "skip", "reverse", "last", "round_over"]) {
      expect(kinds).toContain(kind);
    }
  });

  it("cubren los sucesos de Doble cara y de Sin tregua", () => {
    const kinds = (mode: string) => new Set(byMode(mode).flatMap((s) => s.states.flatMap((state) => state.events.map((e) => e.kind))));
    expect(kinds("doble_cara")).toContain("eclipse");
    for (const kind of ["swap", "rotate", "sweep", "reveal", "stack", "skip_all", "eliminated"]) {
      expect(kinds("sin_tregua")).toContain(kind);
    }
  });

  it("siempre suman todas las cartas de su modo (108, 112 o 168)", () => {
    for (const session of sessions) {
      for (const state of session.states) {
        const inHands = state.players.reduce((sum, player) => sum + player.count, 0);
        expect(inHands + state.draw_count + state.discard_count + state.aside_count).toBe(DECK_SIZES[state.mode]);
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
    // Salvo las que se destapan a la vista de todos (la Ruleta y el Barrido) y
    // mi mano nueva tras un Eclipse, un 7 o un 0 (que puede ser de otro suceso).
    const PUBLIC = new Set(["reveal", "sweep", "eclipse", "swap", "rotate"]);
    for (const session of sessions) {
      for (const state of session.states) {
        for (const event of state.events) {
          if (event.seat !== state.human_seat && !PUBLIC.has(event.kind)) expect(event.cards).toEqual([]);
        }
      }
    }
  });

  it("de mis cartas nunca llega la otra cara, ni a la mesa ni en el registro", () => {
    for (const state of byMode("doble_cara").flatMap((session) => session.states)) {
      expect(state.players[state.human_seat].backs).toEqual([]);
      for (const event of state.events) {
        expect(Object.keys(event.backs ?? {})).not.toContain(String(state.human_seat));
        for (const card of event.cards) expect(card).not.toHaveProperty("back");
      }
      for (const card of state.hand) expect(Object.keys(card).sort()).toEqual(["color", "id", "kind", "number"]);
    }
  });

  it("en Doble cara, el Eclipse le da la vuelta a todo: cara en juego, mano y descarte", () => {
    for (const state of byMode("doble_cara").flatMap((session) => session.states)) {
      state.events.forEach((event, index) => {
        if (event.kind !== "eclipse") return;
        const before = frameAt(state, index);
        const after = frameAt(state, index + 1);
        expect(after.side).not.toBe(before.side);
        expect(after.top?.id).toBe(event.card!.id);
        expect(after.hand.map((card) => card.id).sort()).toEqual(before.hand.map((card) => card.id).sort());
      });
    }
  });

  it("en Sin tregua, quien se desborda queda fuera y sus cartas, apartadas", () => {
    for (const state of byMode("sin_tregua").flatMap((session) => session.states)) {
      state.events.forEach((event, index) => {
        if (event.kind !== "eliminated") return;
        const after = frameAt(state, index + 1);
        expect(after.players[event.seat!].out).toBe(true);
        expect(after.players[event.seat!].count).toBe(0);
        expect(event.count).toBeGreaterThanOrEqual(25);
      });
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
