import type { PlaybackHandle } from "../../shared/timeline/usePlayback";
import { usePlayback as useSharedPlayback } from "../../shared/timeline/usePlayback";
import { POKER_TIMELINE, type PlaybackListener } from "./timeline/playback";
import type { Frame } from "./timeline/frame";
import type { GameState } from "./types";

/** La cola de reproducción de la mesa de poker, conectada a React. */
export function usePlayback(
  animated: boolean,
  listener?: PlaybackListener,
): PlaybackHandle<GameState, Frame> {
  return useSharedPlayback(POKER_TIMELINE, animated, listener);
}
