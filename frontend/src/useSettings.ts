import { useSyncExternalStore } from "react";
import { SettingsStore, type Settings } from "./settings";

function browserStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null; // el navegador bloquea el almacenamiento
  }
}

const store = new SettingsStore(browserStorage());

/** Preferencias guardadas y la función para cambiarlas. */
export function useSettings(): [Settings, (changes: Partial<Settings>) => void] {
  return [useSyncExternalStore(store.subscribe, store.get), store.update];
}

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribeToReducedMotion(listener: () => void): () => void {
  const query = window.matchMedia(REDUCED_MOTION);
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
}

/** ¿Pide el sistema reducir el movimiento? */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeToReducedMotion,
    () => window.matchMedia(REDUCED_MOTION).matches,
  );
}
