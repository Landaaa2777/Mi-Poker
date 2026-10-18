// Cola de reproducción, común a todos los juegos: muestra los pasos en orden,
// de uno en uno.
//
// El servidor envía el estado completo tras cada cambio. Cada juego sabe
// convertir el salto entre dos estados en pasos (`Timeline`); esta cola los
// reproduce sin que se pisen. Mientras quedan pasos, la pantalla va por detrás
// del servidor y los botones de acción deben seguir bloqueados (`busy`). Al
// vaciarse la cola, lo mostrado es exactamente el último estado recibido.

/** Un paso de la reproducción: qué ha pasado y cómo queda la mesa al dibujarlo. */
export interface TimelineStep<Frame> {
  kind: string;
  frame: Frame;
}

/** Lo que cada juego aporta a la cola: cómo trocear los cambios y cuánto dura cada trozo. */
export interface Timeline<State, Frame, Step extends TimelineStep<Frame>> {
  /** Los pasos para ir de `previous` a `next`. El último deja la mesa exactamente como `next`. */
  buildSteps(previous: State | null, next: State): Step[];
  /** La mesa tal como la tiene el servidor. */
  frameFromState(state: State): Frame;
  /** Milisegundos que se muestra `step` antes de pasar al siguiente (0 = no llega a dibujarse). */
  stepDelay(step: Step, next: Step | undefined): number;
  /** ¿Empieza aquí una mano o ronda nueva? Lo que quedara de la anterior se descarta. */
  startsRound(step: Step): boolean;
}

export interface PlaybackState<State, Frame> {
  frame: Frame | null; // lo que se dibuja ahora
  server: State | null; // último estado recibido del servidor
  busy: boolean; // quedan pasos por reproducir
}

/** Quien quiera acompañar la reproducción: las animaciones y el sonido. */
export interface PlaybackListener<Step> {
  /**
   * Va a mostrarse un paso. Se avisa justo antes de dibujarlo, para que quien
   * escucha pueda mirar cómo estaba la mesa. `speed` es mayor que 1 cuando la
   * cola va atrasada y hay que animar más deprisa.
   */
  onStep?: (step: Step, speed: number) => void;
  /** La mesa va a saltar a otro estado sin reproducir pasos (reconexión, animaciones desactivadas...). */
  onJump?: () => void;
  /** Estos pasos se han aplicado de golpe, sin reproducirlos (animaciones desactivadas). */
  onSkip?: (steps: Step[]) => void;
}

/** Si se acumulan estados del servidor sin reproducir, la cola se acelera. */
function catchUpSpeed(waitingBatches: number): number {
  if (waitingBatches <= 1) return 1;
  return waitingBatches === 2 ? 1.5 : 2.5;
}

interface Queued<Step> {
  step: Step;
  batch: number; // un lote por cada estado recibido del servidor
}

export class Playback<State, Frame, Step extends TimelineStep<Frame>> {
  private state: PlaybackState<State, Frame> = { frame: null, server: null, busy: false };
  private queue: Queued<Step>[] = [];
  private batches = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private readonly listeners = new Set<() => void>();

  /** `animated` dice si ahora mismo hay que reproducir paso a paso o saltar al final. */
  constructor(
    private readonly timeline: Timeline<State, Frame, Step>,
    private readonly animated: () => boolean,
    private readonly listener: PlaybackListener<Step> = {},
  ) {}

  getState = (): PlaybackState<State, Frame> => this.state;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  /**
   * Recibe un estado del servidor. Con `instant` se muestra directamente, sin
   * pasos: es lo que toca al reconectar, porque no se vio lo anterior.
   */
  push = (server: State | null, instant = false): void => {
    const previous = this.state.server;
    if (server === null || instant) {
      this.jump(server);
      return;
    }

    const steps = this.timeline.buildSteps(previous, server);
    if (!this.animated()) {
      this.jump(server);
      this.listener.onSkip?.(steps);
      return;
    }

    // Si empieza otra mano, lo que quedara por reproducir de la anterior sobra.
    if (steps.length > 0 && this.timeline.startsRound(steps[0])) this.clear();
    this.batches += 1;
    for (const step of steps) this.queue.push({ step, batch: this.batches });
    this.emit({ ...this.state, server, busy: true });
    if (this.timer === null) this.advance();
  };

  /** Salta al último estado recibido sin reproducir lo pendiente. */
  flush = (): void => {
    if (this.state.busy) this.jump(this.state.server);
  };

  /** Muestra directamente un estado del servidor, descartando lo pendiente. */
  private jump(server: State | null): void {
    this.clear();
    this.listener.onJump?.();
    this.emit({ frame: server && this.timeline.frameFromState(server), server, busy: false });
  }

  private clear(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.queue = [];
  }

  private emit(state: PlaybackState<State, Frame>): void {
    this.state = state;
    for (const listener of this.listeners) listener();
  }

  private advance = (): void => {
    this.timer = null;
    let current = this.queue.shift();
    let delay = 0;
    // Los pasos sin duración no llegan a dibujarse: se pasa directamente al siguiente.
    while (current !== undefined) {
      delay = this.timeline.stepDelay(current.step, this.queue[0]?.step);
      if (delay > 0 || this.queue.length === 0) break;
      current = this.queue.shift();
    }
    if (current === undefined) return;

    const busy = this.queue.length > 0;
    const waiting = new Set(this.queue.map((queued) => queued.batch));
    waiting.delete(current.batch);
    const speed = catchUpSpeed(waiting.size);
    this.listener.onStep?.(current.step, speed);
    this.emit({ ...this.state, frame: current.step.frame, busy });
    if (busy) this.timer = setTimeout(this.advance, delay / speed);
  };
}
