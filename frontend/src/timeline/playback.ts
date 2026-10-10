// Cola de reproducción: muestra los pasos en orden, de uno en uno.
//
// Mientras quedan pasos, la pantalla va por detrás del servidor y los botones
// de acción deben seguir bloqueados (`busy`). Al vaciarse la cola, lo mostrado
// es exactamente el último estado recibido.

import type { GameState } from "../types";
import { frameFromState, type Frame } from "./frame";
import { buildSteps, type Step } from "./steps";

export interface PlaybackState {
  frame: Frame | null; // lo que se dibuja ahora
  server: GameState | null; // último estado recibido del servidor
  busy: boolean; // quedan pasos por reproducir
}

/** Milisegundos que se muestra cada paso antes de pasar al siguiente. */
export function stepDelay(step: Step, next: Step | undefined): number {
  switch (step.kind) {
    case "new_hand":
      return 250;
    case "deal":
      // Las cartas salen seguidas; tras la última, una pausa para mirarlas.
      return next?.kind === "deal" ? 80 : 330;
    case "board":
      // Dentro del flop van seguidas; al completar la calle, un respiro.
      return next?.kind === "board" && next.street === step.street ? 220 : 520;
    case "event":
      if (step.event.kind === "small_blind" || step.event.kind === "big_blind") return 200;
      if (step.event.kind === "refund") return 300;
      if (step.event.kind === "show") return 500;
      if (step.event.kind === "win") return 800;
      return step.event.action === "call" || step.event.action === "raise" ? 450 : 350;
    case "settle":
      return 0;
  }
}

/** Si se acumulan estados del servidor sin reproducir, la cola se acelera. */
function catchUpSpeed(waitingBatches: number): number {
  if (waitingBatches <= 1) return 1;
  return waitingBatches === 2 ? 1.5 : 2.5;
}

/** Quien quiera acompañar la reproducción (por ejemplo, con sonido). */
export interface PlaybackListener {
  /** Empieza a mostrarse un paso de la reproducción. */
  onStep?: (step: Step) => void;
  /** Estos pasos se han aplicado de golpe, sin reproducirlos (animaciones desactivadas). */
  onSkip?: (steps: Step[]) => void;
}

interface Queued {
  step: Step;
  batch: number; // un lote por cada estado recibido del servidor
}

export class Playback {
  private state: PlaybackState = { frame: null, server: null, busy: false };
  private queue: Queued[] = [];
  private batches = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private readonly listeners = new Set<() => void>();

  /** `animated` dice si ahora mismo hay que reproducir paso a paso o saltar al final. */
  constructor(
    private readonly animated: () => boolean,
    private readonly listener: PlaybackListener = {},
  ) {}

  getState = (): PlaybackState => this.state;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  /**
   * Recibe un estado del servidor. Con `instant` se muestra directamente, sin
   * pasos: es lo que toca al reconectar, porque no se vio lo anterior.
   */
  push = (server: GameState | null, instant = false): void => {
    const previous = this.state.server;
    if (server === null || instant) {
      this.clear();
      this.emit({ frame: server && frameFromState(server), server, busy: false });
      return;
    }

    const steps = buildSteps(previous, server);
    if (!this.animated()) {
      this.clear();
      this.emit({ frame: frameFromState(server), server, busy: false });
      this.listener.onSkip?.(steps);
      return;
    }

    // Si empieza otra mano, lo que quedara por reproducir de la anterior sobra.
    if (steps[0].kind === "new_hand") this.clear();
    this.batches += 1;
    for (const step of steps) this.queue.push({ step, batch: this.batches });
    this.emit({ ...this.state, server, busy: true });
    if (this.timer === null) this.advance();
  };

  /** Salta al último estado recibido sin reproducir lo pendiente. */
  flush = (): void => {
    if (!this.state.busy) return;
    const server = this.state.server;
    this.clear();
    this.emit({ frame: server && frameFromState(server), server, busy: false });
  };

  private clear(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.queue = [];
  }

  private emit(state: PlaybackState): void {
    this.state = state;
    for (const listener of this.listeners) listener();
  }

  private advance = (): void => {
    this.timer = null;
    let current = this.queue.shift();
    let delay = 0;
    // Los pasos sin duración no llegan a dibujarse: se pasa directamente al siguiente.
    while (current !== undefined) {
      delay = stepDelay(current.step, this.queue[0]?.step);
      if (delay > 0 || this.queue.length === 0) break;
      current = this.queue.shift();
    }
    if (current === undefined) return;

    const busy = this.queue.length > 0;
    this.emit({ ...this.state, frame: current.step.frame, busy });
    this.listener.onStep?.(current.step);
    if (!busy) return;
    const waiting = new Set(this.queue.map((queued) => queued.batch));
    waiting.delete(current.batch);
    this.timer = setTimeout(this.advance, delay / catchUpSpeed(waiting.size));
  };
}
