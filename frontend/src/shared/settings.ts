// Preferencias del jugador, guardadas en el navegador. Como `guest.ts`, está
// aislado: el resto de la aplicación no sabe dónde ni cómo se guardan.

/** Cómo se ven las mesas: planas, como siempre, o en perspectiva. */
export type TableView = "2d" | "3d";

export interface Settings {
  /** Animaciones de la mesa. `null` = lo que pida el sistema (prefers-reduced-motion). */
  animations: boolean | null;
  /** Vista de las mesas. `null` = todavía no se ha elegido (se ven en 2D). */
  view: TableView | null;
  /** Volumen de la música de fondo, de 0 a 1. */
  musicVolume: number;
  /** Volumen de los efectos de sonido, de 0 a 1. */
  effectsVolume: number;
  /** Silenciar todo, sin perder los volúmenes elegidos. */
  muted: boolean;
}

export const DEFAULT_SETTINGS: Settings = {
  animations: null,
  view: null,
  musicVolume: 0.5, // al cuadrado queda en un cuarto: música baja por defecto
  effectsVolume: 0.7,
  muted: false,
};

const STORAGE_KEY = "mi-poker.settings";

type KeyValueStorage = Pick<Storage, "getItem" | "setItem">;

function volume(value: unknown, fallback: number): number {
  return typeof value === "number" && value >= 0 && value <= 1 ? value : fallback;
}

/** Lee las preferencias guardadas; lo que falte o esté mal vuelve a su valor por defecto. */
export function parseSettings(text: string | null): Settings {
  if (!text) return DEFAULT_SETTINGS;
  let saved: unknown;
  try {
    saved = JSON.parse(text);
  } catch {
    return DEFAULT_SETTINGS;
  }
  if (typeof saved !== "object" || saved === null) return DEFAULT_SETTINGS;
  const { animations, view, musicVolume, effectsVolume, muted } = saved as Record<string, unknown>;
  return {
    animations: typeof animations === "boolean" ? animations : null,
    view: view === "2d" || view === "3d" ? view : null,
    musicVolume: volume(musicVolume, DEFAULT_SETTINGS.musicVolume),
    effectsVolume: volume(effectsVolume, DEFAULT_SETTINGS.effectsVolume),
    muted: typeof muted === "boolean" ? muted : DEFAULT_SETTINGS.muted,
  };
}

export class SettingsStore {
  private settings: Settings;
  private readonly listeners = new Set<() => void>();

  /** `storage` es `null` cuando el navegador no deja guardar nada. */
  constructor(private readonly storage: KeyValueStorage | null) {
    let saved: string | null = null;
    try {
      saved = storage?.getItem(STORAGE_KEY) ?? null;
    } catch {
      // Sin acceso al almacenamiento: valen las preferencias por defecto.
    }
    this.settings = parseSettings(saved);
  }

  get = (): Settings => this.settings;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  update = (changes: Partial<Settings>): void => {
    this.settings = { ...this.settings, ...changes };
    try {
      this.storage?.setItem(STORAGE_KEY, JSON.stringify(this.settings));
    } catch {
      // No se pudo guardar (modo privado, cuota llena): el cambio vale para esta visita.
    }
    for (const listener of this.listeners) listener();
  };
}
