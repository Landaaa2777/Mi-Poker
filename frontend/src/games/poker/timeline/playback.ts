// Cola de reproducción del poker: la cola común (shared/timeline) con los
// pasos y las duraciones de una mano de poker.

import {
  Playback as SharedPlayback,
  type PlaybackListener as SharedListener,
  type PlaybackState as SharedState,
  type Timeline,
} from "../../../shared/timeline/playback";
import type { GameState } from "../types";
import { frameFromState, type Frame } from "./frame";
import { buildSteps, type Step } from "./steps";

export type PlaybackState = SharedState<GameState, Frame>;
export type PlaybackListener = SharedListener<Step>;

/**
 * Milisegundos que se muestra cada paso antes de pasar al siguiente. Cada uno
 * deja tiempo a su animación (ver `motion/`), que dura entre 200 y 500 ms.
 */
export function stepDelay(step: Step, next: Step | undefined): number {
  switch (step.kind) {
    case "new_hand":
      return 250;
    case "deal":
      // Las cartas salen seguidas, solapándose en el aire; tras la última se
      // espera a que aterrice y a que se volteen las mías.
      return next?.kind === "deal" ? 90 : 560;
    case "board":
      // Dentro del flop van seguidas; al completar la calle, un respiro.
      return next?.kind === "board" && next.street === step.street ? 230 : 580;
    case "event":
      if (step.event.kind === "small_blind" || step.event.kind === "big_blind") return 220;
      if (step.event.kind === "refund") return 380;
      if (step.event.kind === "show") return 520;
      if (step.event.kind === "win") return 900;
      return step.event.action === "call" || step.event.action === "raise" ? 480 : 380;
    case "settle":
      return 0;
  }
}

/** Cómo se reproduce una mano de poker. */
export const POKER_TIMELINE: Timeline<GameState, Frame, Step> = {
  buildSteps,
  frameFromState,
  stepDelay,
  startsRound: (step) => step.kind === "new_hand",
};

export class Playback extends SharedPlayback<GameState, Frame, Step> {
  constructor(animated: () => boolean, listener: PlaybackListener = {}) {
    super(POKER_TIMELINE, animated, listener);
  }
}
