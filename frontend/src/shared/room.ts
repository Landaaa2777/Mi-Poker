// Lo que comparten las mesas de los juegos cuando se juegan en una sala con
// amigos (ver backend/core/room.py). La sala en sí está en `src/salas/`.

/** La cuenta atrás de una decisión, tal como la manda el servidor en cada estado. */
export interface TurnTimer {
  seat: number | null; // null = la cuenta atrás es de todos a la vez (por ejemplo, las apuestas)
  left: number; // segundos que quedaban al enviarla
  total: number;
}

/** Lo que la sala le da a la mesa de un juego para jugar. */
export interface RoomPlay {
  /** Avisa de cada estado de la partida; al apuntarse, recibe el último que haya. */
  subscribe: (listener: (state: unknown, instant: boolean) => void) => () => void;
  send: (message: object) => void;
  waiting: boolean; // hay una jugada enviada y el servidor aún no ha contestado
}

/** Lo que recibe la vista de sala de cada juego (`games/<juego>/<Juego>Room.tsx`). */
export interface RoomViewProps {
  play: RoomPlay;
}

/** Segundos enteros que le quedan a una cuenta atrás, `elapsed` segundos después de recibirla. */
export function secondsLeft(timer: TurnTimer, elapsed: number): number {
  return Math.max(0, Math.ceil(timer.left - elapsed));
}
