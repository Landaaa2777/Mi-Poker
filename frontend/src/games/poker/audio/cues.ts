// Qué efectos de sonido le corresponden a cada paso de la mano, y cuándo.

import type { Step } from "../timeline/steps";
import type { EffectName } from "../../../shared/audio/effects";

export interface Cue {
  name: EffectName;
  /** Segundos desde que empieza el paso: el sonido cae cuando lo hace su animación. */
  delay: number;
}

const CHIPS_LAND = 0.25; // las fichas suenan al llegar al bote, no al salir
const CARD_LANDS = 0.3; // una carta repartida tarda esto en llegar

/** Los sonidos de un paso. Una lista vacía si el paso es silencioso. */
export function cuesForStep(step: Step): Cue[] {
  switch (step.kind) {
    case "deal": {
      const mine = step.frame.seats.find((seat) => seat.seat === step.seat)?.isHuman;
      // Mis cartas, además, se voltean al llegar.
      return mine
        ? [
            { name: "deal", delay: 0 },
            { name: "flip", delay: CARD_LANDS },
          ]
        : [{ name: "deal", delay: 0 }];
    }
    case "board":
      // Sale del mazo y gira en el aire.
      return [
        { name: "deal", delay: 0 },
        { name: "flip", delay: 0.2 },
      ];
    case "new_hand":
    case "settle":
      return [];
    case "event":
      break;
  }

  const { event } = step;
  switch (event.kind) {
    case "small_blind":
    case "big_blind":
      return [{ name: "chips", delay: CHIPS_LAND }];
    case "show":
      return [{ name: "flip", delay: 0.1 }];
    case "win": {
      const winner = step.frame.seats.find((seat) => seat.seat === event.seat);
      return [{ name: winner?.isHuman ? "win" : "winOther", delay: 0.3 }];
    }
    case "action":
      if (event.action === "fold") return [{ name: "fold", delay: 0 }];
      if (event.action === "check") return [{ name: "check", delay: 0 }];
      if (event.all_in) return [{ name: "allIn", delay: 0.2 }];
      if (event.action === "raise") return [{ name: "raise", delay: 0.2 }];
      return [{ name: "chips", delay: CHIPS_LAND }];
    default:
      return []; // devolución de fichas
  }
}

// De más a menos importante: cuando varios pasos se aplican de golpe, suena solo uno.
const PRIORITY: EffectName[] = [
  "win",
  "winOther",
  "allIn",
  "raise",
  "chips",
  "check",
  "fold",
  "flip",
  "deal",
];

/** El sonido que resume varios pasos aplicados a la vez (animaciones desactivadas). */
export function cueForSkipped(steps: Step[]): EffectName | null {
  const names = new Set(steps.flatMap((step) => cuesForStep(step).map((cue) => cue.name)));
  return PRIORITY.find((name) => names.has(name)) ?? null;
}
