import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { GameState } from "../types";
import { sessions } from "./fixtures/sessions";
import { frameFromState, type Frame } from "./frame";
import { Playback, stepDelay } from "./playback";
import { buildSteps, type Step } from "./steps";

const sixHanded = sessions[0].states;
const shortStacks = sessions[1].states;

/** Estados de una misma mano, empezando por el que la reparte. */
function firstHand(states: GameState[]): GameState[] {
  const end = states.findIndex((state) => !state.hand_in_progress);
  return states.slice(0, end + 1);
}

/** Los frames que se van dibujando a partir de ahora, sin repetir el que ya estaba. */
function watch(playback: Playback): Frame[] {
  const frames: Frame[] = [];
  let shown = playback.getState().frame;
  playback.subscribe(() => {
    const { frame } = playback.getState();
    if (frame && frame !== shown) frames.push(frame);
    shown = frame;
  });
  return frames;
}

/** Duración de una tanda reproducida a velocidad normal. */
function duration(previous: GameState | null, next: GameState): number {
  const steps = buildSteps(previous, next);
  return steps.reduce((total, step, index) => total + stepDelay(step, steps[index + 1]), 0);
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("Playback", () => {
  it("reproduce los pasos en orden y termina en el estado del servidor", () => {
    const playback = new Playback(() => true);
    const frames = watch(playback);
    const [deal] = sixHanded;

    playback.push(deal);
    expect(playback.getState()).toMatchObject({ server: deal, busy: true });
    vi.runAllTimers();

    // Se dibujan todos los pasos con duración y, al final, el estado del servidor.
    const steps = buildSteps(null, deal);
    const drawn = steps.filter((step, index) => stepDelay(step, steps[index + 1]) > 0);
    expect(frames).toEqual([...drawn.map((step) => step.frame), frameFromState(deal)]);
    expect(playback.getState()).toEqual({ frame: frameFromState(deal), server: deal, busy: false });
  });

  it("sigue ocupado hasta que se dibuja el último paso", () => {
    const playback = new Playback(() => true);
    const [deal] = sixHanded;
    playback.push(deal);

    vi.advanceTimersByTime(duration(null, deal) - 1);
    expect(playback.getState().busy).toBe(true);
    expect(playback.getState().frame).not.toEqual(frameFromState(deal));
    vi.advanceTimersByTime(1);
    expect(playback.getState().busy).toBe(false);
  });

  it("encola los estados que llegan mientras reproduce y no se salta ninguno", () => {
    const playback = new Playback(() => true);
    const frames = watch(playback);
    const hand = firstHand(shortStacks);
    for (const state of hand) playback.push(state);
    expect(playback.getState()).toMatchObject({ server: hand.at(-1), busy: true });
    vi.runAllTimers();

    expect(playback.getState()).toMatchObject({ frame: frameFromState(hand.at(-1)!), busy: false });
    // El registro mostrado nunca retrocede y acaba completo.
    const lengths = frames.map((frame) => frame.events.length);
    expect(lengths).toEqual([...lengths].sort((a, b) => a - b));
    expect(lengths.at(-1)).toBe(hand.at(-1)!.events.length);
  });

  it("acelera cuando se acumulan estados sin reproducir", () => {
    const hand = firstHand(sixHanded);
    expect(hand.length).toBeGreaterThan(4);
    const normal = hand.reduce(
      (total, state, index) => total + duration(index > 0 ? hand[index - 1] : null, state),
      0,
    );

    const playback = new Playback(() => true);
    for (const state of hand) playback.push(state);
    vi.advanceTimersByTime(normal * 0.75);
    expect(playback.getState().busy).toBe(false);
  });

  it("no acelera con un solo estado en espera", () => {
    const [deal, second] = sixHanded;
    const playback = new Playback(() => true);
    playback.push(deal);
    playback.push(second);
    const total = duration(null, deal) + duration(deal, second);
    vi.advanceTimersByTime(total - 1);
    expect(playback.getState().busy).toBe(true);
    vi.advanceTimersByTime(1);
    expect(playback.getState().busy).toBe(false);
  });

  it("muestra el estado directamente si es instantáneo (reconexión)", () => {
    const playback = new Playback(() => true);
    const state = sixHanded[3];
    playback.push(state, true);
    expect(playback.getState()).toEqual({ frame: frameFromState(state), server: state, busy: false });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("no reproduce nada con las animaciones desactivadas", () => {
    let animated = false;
    const playback = new Playback(() => animated);
    const frames = watch(playback);
    playback.push(sixHanded[0]);
    playback.push(sixHanded[1]);
    expect(frames).toEqual([frameFromState(sixHanded[0]), frameFromState(sixHanded[1])]);
    expect(playback.getState().busy).toBe(false);

    // Al reactivarlas, sigue desde el último estado recibido: solo lo nuevo.
    animated = true;
    playback.push(sixHanded[2]);
    expect(playback.getState().busy).toBe(true);
    vi.runAllTimers();
    expect(playback.getState().frame).toEqual(frameFromState(sixHanded[2]));
    expect(frames.some((frame) => frame.events.length === 0)).toBe(false);
  });

  it("flush salta al último estado recibido", () => {
    const playback = new Playback(() => true);
    const hand = firstHand(shortStacks);
    for (const state of hand) playback.push(state);
    vi.advanceTimersByTime(300);
    playback.flush();

    expect(playback.getState()).toEqual({
      frame: frameFromState(hand.at(-1)!),
      server: hand.at(-1),
      busy: false,
    });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("al llegar una mano nueva descarta lo que quedaba de la anterior", () => {
    const playback = new Playback(() => true);
    const hand = firstHand(shortStacks);
    const nextDeal = shortStacks[hand.length];
    for (const state of hand) playback.push(state);
    vi.advanceTimersByTime(100);

    const frames = watch(playback);
    playback.push(nextDeal);
    expect(frames[0].events).toEqual([]);
    expect(frames[0].handNumber).toBe(nextDeal.hand_number);
    vi.runAllTimers();
    expect(frames.every((frame) => frame.handNumber === nextDeal.hand_number)).toBe(true);
    expect(playback.getState().frame).toEqual(frameFromState(nextDeal));
  });

  it("se queda sin mesa cuando no hay partida", () => {
    const playback = new Playback(() => true);
    playback.push(sixHanded[0]);
    playback.push(null);
    expect(playback.getState()).toEqual({ frame: null, server: null, busy: false });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("avisa de cada paso justo antes de dibujarlo", () => {
    const shown: Step[] = [];
    const skipped: Step[][] = [];
    const drawnBefore: (Frame | null)[] = [];
    const playback: Playback = new Playback(() => true, {
      onStep: (step) => {
        shown.push(step);
        drawnBefore.push(playback.getState().frame);
      },
      onSkip: (steps) => skipped.push(steps),
    });
    const [deal] = sixHanded;
    const steps = buildSteps(null, deal);
    const drawn = steps.filter((step, index) => stepDelay(step, steps[index + 1]) > 0);

    playback.push(deal);
    expect(shown).toEqual([drawn[0]]); // el primero, nada más llegar
    vi.advanceTimersByTime(stepDelay(drawn[0], drawn[1]));
    expect(shown).toEqual(drawn.slice(0, 2));
    vi.runAllTimers();
    // Todos los pasos con duración, una vez y en orden, y al final el estado del servidor.
    expect(shown).toEqual([...drawn, steps.at(-1)]);
    expect(shown.at(-1)?.kind).toBe("settle");
    expect(skipped).toEqual([]);
    // En el momento del aviso la mesa aún mostraba el paso anterior.
    expect(drawnBefore[0]).toBeNull();
    expect(drawnBefore.slice(1)).toEqual(shown.slice(0, -1).map((step) => step.frame));
  });

  it("dice a qué velocidad hay que animar: normal, o más deprisa si hay atasco", () => {
    const speeds: number[] = [];
    const playback = new Playback(() => true, { onStep: (_, speed) => speeds.push(speed) });
    playback.push(sixHanded[0]);
    vi.runAllTimers();
    expect(new Set(speeds)).toEqual(new Set([1]));

    speeds.length = 0;
    for (const state of firstHand(shortStacks)) playback.push(state);
    vi.runAllTimers();
    expect(Math.max(...speeds)).toBeGreaterThan(1);
    expect(speeds.at(-1)).toBe(1); // al ponerse al día vuelve a la velocidad normal
  });

  it("avisa cuando la mesa salta sin reproducir pasos", () => {
    const calls: string[] = [];
    let animated = true;
    const playback = new Playback(() => animated, {
      onStep: () => calls.push("step"),
      onJump: () => calls.push("jump"),
      onSkip: () => calls.push("skip"),
    });
    playback.push(sixHanded[0], true); // reconexión
    expect(calls).toEqual(["jump"]);

    playback.push(sixHanded[1]);
    playback.flush(); // pestaña oculta a mitad de reproducción
    expect(calls.at(-1)).toBe("jump");

    animated = false;
    calls.length = 0;
    playback.push(sixHanded[2]); // animaciones desactivadas
    expect(calls).toEqual(["jump", "skip"]);

    calls.length = 0;
    playback.push(null); // sin partida
    expect(calls).toEqual(["jump"]);
  });

  it("con las animaciones desactivadas avisa una vez con todos los pasos saltados", () => {
    const shown: Step[] = [];
    const skipped: Step[][] = [];
    const playback = new Playback(() => false, {
      onStep: (step) => shown.push(step),
      onSkip: (steps) => skipped.push(steps),
    });
    playback.push(sixHanded[0]);
    playback.push(sixHanded[1]);
    expect(shown).toEqual([]);
    expect(skipped).toEqual([
      buildSteps(null, sixHanded[0]),
      buildSteps(sixHanded[0], sixHanded[1]),
    ]);
  });

  it("no avisa de nada al reconectar ni al saltar al final", () => {
    const calls: string[] = [];
    const playback = new Playback(() => true, {
      onStep: () => calls.push("step"),
      onSkip: () => calls.push("skip"),
    });
    playback.push(sixHanded[3], true); // reconexión: no se vio lo anterior
    expect(calls).toEqual([]);
    playback.push(sixHanded[4]);
    const afterPush = calls.length;
    playback.flush();
    vi.runAllTimers();
    expect(calls.length).toBe(afterPush);
    expect(calls).not.toContain("skip");
  });

  it("deja de avisar a quien se da de baja", () => {
    const playback = new Playback(() => true);
    const listener = vi.fn();
    const unsubscribe = playback.subscribe(listener);
    playback.push(sixHanded[0], true);
    unsubscribe();
    playback.push(sixHanded[1], true);
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
