import { createContext, useCallback, useContext, useLayoutEffect, type ReactNode } from "react";
import { useAudio } from "./audio/useAudio";
import { motion } from "./motion";
import type { Settings, TableView } from "./settings";
import { usePrefersReducedMotion, useSettings } from "./useSettings";

/** Preferencias de toda la plataforma: sonido y animaciones, iguales en todos los juegos. */
export interface PlatformSettings {
  settings: Settings;
  update: (changes: Partial<Settings>) => void;
  animations: boolean; // valor efectivo: lo elegido o, si no se eligió, lo que pide el sistema
  reducedMotion: boolean; // el sistema pide reducir el movimiento
  view: TableView; // vista de las mesas: la elegida o, si no se ha elegido, 2D
}

const SettingsContext = createContext<PlatformSettings | null>(null);

export function usePlatformSettings(): PlatformSettings {
  const settings = useContext(SettingsContext);
  if (!settings) throw new Error("usePlatformSettings necesita un <SettingsProvider> por encima");
  return settings;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, save] = useSettings();
  // Al cambiar de vista la mesa se vuelve a dibujar entera: nada debe entrar
  // volando ni caer como si acabara de llegar.
  const update = useCallback(
    (changes: Partial<Settings>) => {
      if (changes.view !== undefined) {
        motion.entering = null;
        motion.revealing = false;
        motion.chipLanding = null;
      }
      save(changes);
    },
    [save],
  );
  const reducedMotion = usePrefersReducedMotion();
  const animations = settings.animations ?? !reducedMotion;
  const view = settings.view ?? "2d";
  useAudio(settings);

  // Las piezas de las mesas y las hojas de estilo miran aquí si deben moverse.
  useLayoutEffect(() => {
    motion.enabled = animations;
    document.documentElement.dataset.motion = animations ? "on" : "off";
  }, [animations]);

  return (
    <SettingsContext.Provider value={{ settings, update, animations, reducedMotion, view }}>
      {children}
    </SettingsContext.Provider>
  );
}
