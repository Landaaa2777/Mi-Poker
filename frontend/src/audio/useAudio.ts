import { useEffect } from "react";
import type { Settings } from "../settings";
import type { PlaybackListener } from "../timeline/playback";
import { cueForSkipped, cuesForStep } from "./cues";
import { audio } from "./engine";

/** Sonido de la mesa: cada paso suena en el momento en que lo hace su animación. */
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

/**
 * Conecta el motor de audio con la página: aplica los volúmenes elegidos, lo
 * activa con la primera interacción del usuario y lo calla con la pestaña oculta.
 */
export function useAudio(settings: Settings): void {
  const { musicVolume, effectsVolume, muted } = settings;
  useEffect(() => {
    audio.setLevels({ music: musicVolume, effects: effectsVolume, muted });
  }, [musicVolume, effectsVolume, muted]);

  useEffect(() => {
    const onVisibility = () => audio.setHidden(document.hidden);
    window.addEventListener("pointerdown", audio.unlock);
    window.addEventListener("keydown", audio.unlock);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("pointerdown", audio.unlock);
      window.removeEventListener("keydown", audio.unlock);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);
}
