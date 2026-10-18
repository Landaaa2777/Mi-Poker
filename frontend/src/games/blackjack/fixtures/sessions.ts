// Partidas reales de blackjack grabadas del servidor con `frontend/tools/record_blackjack.py`.

import type { GameState } from "../types";
import recorded from "./sessions.json";

export interface RecordedSession {
  name: string;
  states: GameState[]; // todos los estados, en el orden en que llegaron al navegador
}

export const sessions = recorded as unknown as RecordedSession[];

/** Cada estado grabado junto al que llegó justo antes. */
export function transitions(): { previous: GameState | null; next: GameState }[] {
  return sessions.flatMap((session) =>
    session.states.map((next, index) => ({
      previous: index > 0 ? session.states[index - 1] : null,
      next,
    })),
  );
}
