// Qué efecto de sonido le corresponde a cada paso de la mano.

import type { Step } from "../timeline/steps";
import type { EffectName } from "./effects";

/** El sonido de un paso, o `null` si ese paso es silencioso. */
export function cueForStep(step: Step): EffectName | null {
  switch (step.kind) {
    case "deal":
      return "deal";
    case "board":
      return "flip";
    case "new_hand":
    case "settle":
      return null;
    case "event":
      break;
  }

  const { event } = step;
  switch (event.kind) {
    case "small_blind":
    case "big_blind":
      return "chips";
    case "show":
      return "flip";
    case "win": {
      const winner = step.frame.seats.find((seat) => seat.seat === event.seat);
      return winner?.isHuman ? "win" : "winOther";
    }
    case "action":
      if (event.action === "fold") return "fold";
      if (event.action === "check") return "check";
      if (event.all_in) return "allIn";
      return event.action === "raise" ? "raise" : "chips";
    default:
      return null; // devolución de fichas, cartas comunitarias (van con su propio paso)
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
  const cues = new Set(steps.map(cueForStep));
  return PRIORITY.find((name) => cues.has(name)) ?? null;
}
