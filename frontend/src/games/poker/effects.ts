import { tableSounds } from "./audio/tableSounds";
import { tableMotion } from "./director";
import type { PlaybackListener } from "./timeline/playback";

/** Lo que acompaña a cada paso de la mano: primero el movimiento y después su sonido. */
export const tableEffects: PlaybackListener = {
  onStep(step, speed) {
    tableMotion.onStep?.(step, speed);
    tableSounds.onStep?.(step, speed);
  },
  onJump: tableMotion.onJump,
  onSkip: tableSounds.onSkip,
};
