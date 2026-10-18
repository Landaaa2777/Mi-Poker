import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Playback, type PlaybackListener, type PlaybackState, type Timeline, type TimelineStep } from "./playback";

export interface PlaybackHandle<State, Frame> extends PlaybackState<State, Frame> {
  /** Entrega un estado recién llegado del servidor. */
  push: (state: State | null, instant?: boolean) => void;
}

/**
 * Cola de reproducción de un juego, conectada a React. Con `animated` en falso,
 * o con la pestaña oculta, no reproduce pasos: muestra directamente el último
 * estado. `timeline` y `listener` tienen que ser siempre los mismos objetos.
 */
export function usePlayback<State, Frame, Step extends TimelineStep<Frame>>(
  timeline: Timeline<State, Frame, Step>,
  animated: boolean,
  listener?: PlaybackListener<Step>,
): PlaybackHandle<State, Frame> {
  const animatedRef = useRef(animated);
  const [playback] = useState(
    () => new Playback(timeline, () => animatedRef.current && !document.hidden, listener),
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
