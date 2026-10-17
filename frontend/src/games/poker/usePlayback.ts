import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Playback, type PlaybackListener, type PlaybackState } from "./timeline/playback";
import type { GameState } from "./types";

export interface PlaybackHandle extends PlaybackState {
  /** Entrega un estado recién llegado del servidor. */
  push: (state: GameState | null, instant?: boolean) => void;
}

/**
 * Cola de reproducción conectada a React. Con `animated` en falso, o con la
 * pestaña oculta, no reproduce pasos: muestra directamente el último estado.
 * `listener` se entera de cada paso; tiene que ser siempre el mismo objeto.
 */
export function usePlayback(animated: boolean, listener?: PlaybackListener): PlaybackHandle {
  const animatedRef = useRef(animated);
  const [playback] = useState(
    () => new Playback(() => animatedRef.current && !document.hidden, listener),
  );

  useEffect(() => {
    animatedRef.current = animated;
    if (!animated) playback.flush();
  }, [animated, playback]);

  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) playback.flush();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [playback]);

  const state = useSyncExternalStore(playback.subscribe, playback.getState);
  return { ...state, push: playback.push };
}
