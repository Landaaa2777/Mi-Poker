import { audio } from "../../../shared/audio/engine";
import type { PlaybackListener } from "../timeline/playback";
import { cueForSkipped, cuesForStep } from "./cues";

/** Sonido de la mesa de poker: cada paso suena en el momento en que lo hace su animación. */
export const tableSounds: PlaybackListener = {
  onStep(step, speed) {
    // Si la cola va atrasada, las animaciones se aceleran y los sonidos con ellas.
    for (const cue of cuesForStep(step)) audio.play(cue.name, cue.delay / speed);
  },
  onSkip(steps) {
    const cue = cueForSkipped(steps);
    if (cue) audio.play(cue);
  },
};
