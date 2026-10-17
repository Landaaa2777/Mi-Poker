// Lógica del menú principal, sin React: qué juegos hay, cuáles se pueden
// jugar y cuáles tienen una partida a medias. Todo sale del servidor.

import { getGuestId } from "../shared/guest";

/** Una opción configurable de un juego, tal como la describe el servidor. */
export type GameOption =
  | { key: string; type: "number"; label: string; default: number; min: number | null; max: number | null; step: number; presets?: number[]; help?: string }
  | { key: string; type: "choice"; label: string; default: string; choices: { value: string; label: string; description?: string }[]; help?: string }
  | { key: string; type: "toggle"; label: string; default: boolean; help?: string };

/** Un juego del registro (GET /api/juegos). */
export interface GameEntry {
  id: string;
  name: string;
  description: string;
  min_bots: number;
  max_bots: number;
  min_players: number;
  max_players: number;
  available: boolean; // false = "Próximamente"
  options: GameOption[];
}

/** Una partida mía (GET /api/partidas). */
export interface PartidaInfo {
  game: string;
  partida_id: string;
  in_progress: boolean;
}

/** Qué ofrece la tarjeta de un juego. */
export type CardState = "play" | "continue" | "soon";

type Fetcher = typeof fetch;

export async function fetchGames(fetcher: Fetcher = fetch): Promise<GameEntry[]> {
  const response = await fetcher("/api/juegos");
  if (!response.ok) throw new Error("No se pudo leer la lista de juegos");
  return (await response.json()) as GameEntry[];
}

export async function fetchMyPartidas(fetcher: Fetcher = fetch): Promise<PartidaInfo[]> {
  const guest = encodeURIComponent(getGuestId());
  const response = await fetcher(`/api/partidas?guest_id=${guest}`, { credentials: "same-origin" });
  if (!response.ok) return [];
  return ((await response.json()) as { partidas: PartidaInfo[] }).partidas;
}

/** Cuántos juegan, en palabras: "2 a 6 jugadores". Sin dato útil, null. */
export function playersLabel(game: GameEntry): string | null {
  const { min_players: low, max_players: high } = game;
  if (high <= 1) return null; // un juego sin mesa (los minijuegos, por ejemplo)
  if (low === high) return `${low} jugadores`;
  return `${low} a ${high} jugadores`;
}

/**
 * Qué se puede hacer con un juego: jugarlo, continuar una partida a medias o
 * nada todavía. `playable` dice si el frontend tiene su página.
 */
export function cardState(game: GameEntry, partidas: PartidaInfo[], playable: boolean): CardState {
  if (!game.available || !playable) return "soon";
  return partidas.some((partida) => partida.game === game.id && partida.in_progress)
    ? "continue"
    : "play";
}

/** Los juegos en el orden del menú: primero los que se pueden jugar, cada grupo en el orden del registro. */
export function menuOrder(games: GameEntry[], playable: (id: string) => boolean): GameEntry[] {
  const ready = games.filter((game) => game.available && playable(game.id));
  return [...ready, ...games.filter((game) => !ready.includes(game))];
}
