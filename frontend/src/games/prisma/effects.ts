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
        case "skip_all":
          return "fold";
        case "reverse":
        case "reshuffle":
          return "select";
        case "challenge":
        case "stack":
          return "raise";
        case "eclipse":
          return "flip"; // toda la mesa se da la vuelta
        case "swap":
        case "rotate":
          return "deal"; // las manos cambian de sitio
        case "sweep":
          return "chips";
        case "eliminated":
          return "allIn";
        case "round_over":
          return step.event.seat === me ? "win" : null;
        default:
          return null;
      }
    default:
      return null;
  }
}

/** Cómo entran en la mesa las cartas que aparecen en un paso. */
function entering(step: Step): string | null {
  if (step.kind === "deal" || step.kind === "draw") return "deal";
  if (step.kind === "play") return "play";
  // Con un 7 o un 0, mi mano nueva llega volando desde quien me la pasa.
  if (step.kind === "event" && (step.event.kind === "swap" || step.event.kind === "rotate")) return "deal";
  return null;
}

/** Animaciones y sonido de la mesa de Prisma, enganchados a la cola de reproducción. */
export function tableEffects(me: () => number): PlaybackListener<Step> {
  return {
    onStep(step, speed) {
      // Las cartas leen esto al aparecer: las repartidas y robadas vuelan desde
      // el mazo; la jugada, desde quien la suelta hasta el descarte. Con el
      // Eclipse, las que ya están a la vista se dan la vuelta en su sitio.
      motion.entering = entering(step);
      motion.revealing = false;
      motion.turning = step.kind === "event" && step.event.kind === "eclipse";
      motion.speed = speed;
      const sound = soundFor(step, me());
      if (sound) audio.play(sound);
    },
    onJump() {
      motion.entering = null;
      motion.revealing = false;
      motion.turning = false;
      motion.speed = 1;
    },
  };
}
