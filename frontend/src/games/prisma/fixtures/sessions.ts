// Partidas reales de Prisma grabadas del servidor con `frontend/tools/record_prisma.py`.
// Para que pesen poco, el registro de cada ronda va una sola vez y cada estado
// dice cuántos sucesos lleva: aquí se rehacen los estados completos.

import type { GameEvent, GameState } from "../types";
import recorded from "./sessions.json";

interface Compact {
  name: string;
  rounds: Record<string, GameEvent[]>;
  states: (Omit<GameState, "events"> & { event_count: number })[];
}

export interface RecordedSession {
  name: string;
  states: GameState[];
}

export const sessions: RecordedSession[] = (recorded as unknown as Compact[]).map((session) => ({
  name: session.name,
  states: session.states.map(({ event_count, ...state }) => ({
    ...state,
    events: session.rounds[String(state.round_number)].slice(0, event_count),
  })),
}));

/** Cada estado grabado junto al que llegó justo antes. */
export function transitions(): { previous: GameState | null; next: GameState }[] {
  return sessions.flatMap((session) =>
    session.states.map((next, index) => ({
      previous: index > 0 ? session.states[index - 1] : null,
      next,
    })),
  );
}
