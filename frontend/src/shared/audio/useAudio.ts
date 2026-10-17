import { useEffect } from "react";
import type { Settings } from "../settings";
import { audio } from "./engine";

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
