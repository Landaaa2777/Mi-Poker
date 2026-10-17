// Partidas reales grabadas del servidor con `frontend/tools/record_fixtures.py`.

import type { GameState } from "../../types";
import recorded from "./sessions.json";

export interface RecordedSession {
  name: string;
  cases: string[]; // casos difíciles que contiene (botes laterales, reinicios...)
  states: GameState[]; // todos los estados, en el orden en que llegaron al navegador
}

export const sessions = recorded as unknown as RecordedSession[];

export interface Transition {
  session: string;
  previous: GameState | null;
  next: GameState;
}

/** Cada estado grabado junto al que llegó justo antes. */
export function transitions(): Transition[] {
  return sessions.flatMap((session) =>
    session.states.map((next, index) => ({
      session: session.name,
      previous: index > 0 ? session.states[index - 1] : null,
      next,
    })),
  );
}
