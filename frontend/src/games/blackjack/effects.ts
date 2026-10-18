// Lo que acompaña a cada paso de la ronda: el movimiento de las cartas y su sonido.

import { audio } from "../../shared/audio/engine";
import type { EffectName } from "../../shared/audio/effects";
import { motion } from "../../shared/motion";
import type { PlaybackListener } from "../../shared/timeline/playback";
import type { Step } from "./timeline";

/** El sonido de un paso, si tiene. `me` es mi asiento. */
export function soundFor(step: Step, me: number): EffectName | null {
  switch (step.kind) {
    case "card":
      return "deal";
    case "reveal":
      return "flip";
    case "event": {
      const { kind, action, seat, result } = step.event;
      if (kind === "bet" || kind === "insurance" || kind === "split") return "chips";
      if (kind === "action") {
        if (action === "stand") return "check";
        if (action === "double") return "chips";
        if (action === "surrender") return "fold";
        return null; // pedir suena con la carta que llega
      }
      if (kind === "settle" && seat === me && (result === "win" || result === "blackjack")) return "win";
      if (kind === "shuffle") return "select";
      return null;
    }
    default:
      return null;
  }
}

/** Animaciones y sonido de la mesa de blackjack, enganchados a la cola de reproducción. */
export function tableEffects(me: () => number): PlaybackListener<Step> {
  return {
    onStep(step, speed) {
      // Las cartas leen esto al aparecer: vuelan desde el zapato, y al destapar se voltean.
      motion.entering = step.kind === "card" ? "deal" : null;
      motion.revealing = step.kind === "reveal";
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
