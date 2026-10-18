// Lo que acompaña a cada paso de la ronda: el movimiento de las cartas y su sonido.

import { audio } from "../../shared/audio/engine";
import type { EffectName } from "../../shared/audio/effects";
import { motion } from "../../shared/motion";
import type { PlaybackListener } from "../../shared/timeline/playback";
import type { Step } from "./timeline";

/** El sonido de un paso, si tiene. `me` es mi asiento. */
export function soundFor(step: Step, me: number): EffectName | null {
  switch (step.kind) {
    case "deal":
    case "draw":
      return "deal";
    case "play": {
      const card = step.frame.top;
      if (!card) return "flip";
      if (card.color === null) return "raise"; // un comodín
      return card.kind === "number" ? "flip" : "chips"; // una acción suena con más fuerza
    }
    case "event":
      switch (step.event.kind) {
        case "last":
          return "check";
        case "caught":
        case "skip":
          return "fold";
        case "reverse":
        case "reshuffle":
          return "select";
        case "challenge":
          return "raise";
        case "round_over":
          return step.event.seat === me ? "win" : null;
        default:
          return null;
      }
    default:
      return null;
  }
}

/** Animaciones y sonido de la mesa de Prisma, enganchados a la cola de reproducción. */
export function tableEffects(me: () => number): PlaybackListener<Step> {
  return {
    onStep(step, speed) {
      // Las cartas leen esto al aparecer: las repartidas y robadas vuelan desde
      // el mazo; la jugada, desde quien la suelta hasta el descarte.
      motion.entering = step.kind === "deal" || step.kind === "draw" ? "deal" : step.kind === "play" ? "play" : null;
      motion.revealing = false;
      motion.speed = speed;
      const sound = soundFor(step, me());
      if (sound) audio.play(sound);
    },
    onJump() {
      motion.entering = null;
      motion.revealing = false;
      motion.speed = 1;
    },
  };
}
