// Salas con amigos, sin React: códigos, enlaces y las peticiones al servidor
// (ver backend/server/salas_api.py). La sala en tiempo real va por WebSocket
// (`useSala.ts`).

import type { GameOption, OptionValues } from "../shared/options";

// Las mismas reglas que el servidor: 6 caracteres, sin 0, O, 1, I ni L.
export const CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
export const CODE_LENGTH = 6;

/** Una persona de la sala. */
export interface Member {
  name: string;
  connected: boolean;
  host: boolean;
}

/** Lo que veo de la sala (mensaje "sala" del WebSocket). */
export interface SalaView {
  code: string;
  game: string; // id del juego, como en el registro
  game_name: string;
  status: "waiting" | "playing";
  you: string;
  host: string | null;
  members: Member[];
  min_people: number;
  max_people: number;
  options: OptionValues;
  fields: GameOption[]; // con ellas el anfitrión pinta el panel de opciones
  can_start: boolean;
  game_over: boolean; // ya se jugó una partida: su mesa final sigue a la vista
}

/** Lo justo para saber a qué sala ir. */
export interface SalaSummary {
  code: string;
  game: string;
  status: "waiting" | "playing";
}

export type SalaResult = { ok: true; sala: SalaSummary } | { ok: false; message: string };

const NO_CONNECTION = "Sin conexión con el servidor. Inténtalo otra vez.";
const UNEXPECTED = "No se pudo completar. Inténtalo otra vez.";

/**
 * El código tal como lo guarda el servidor, o null si no puede ser un código.
 * Se aceptan minúsculas, espacios y guiones: " k7p-2qx " es "K7P2QX".
 */
export function normalizeCode(text: string): string | null {
  const code = text.replace(/[\s-]/g, "").toUpperCase();
  if (code.length !== CODE_LENGTH) return null;
  return [...code].every((char) => CODE_ALPHABET.includes(char)) ? code : null;
}

/** El enlace para invitar a la sala, con la dirección por la que se ha entrado. */
export function salaLink(code: string, origin = location.origin): string {
  return `${origin}/sala/${code}`;
}

/** Dirección del WebSocket de la sala. */
export function salaSocketUrl(code: string, where: Pick<Location, "protocol" | "host"> = location): string {
  const scheme = where.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${where.host}/ws/sala/${encodeURIComponent(code)}`;
}

/** Las opciones de la sala en palabras, para quien no es el anfitrión. */
export function describeOptions(fields: GameOption[], values: OptionValues): string[] {
  return fields.map((field) => {
    const value = values[field.key] ?? field.default;
    if (field.type === "toggle") return `${field.label}: ${value ? "sí" : "no"}`;
    if (field.type === "choice") {
      const choice = field.choices.find((option) => option.value === value);
      return `${field.label}: ${choice?.label ?? String(value)}`;
    }
    return `${field.label}: ${typeof value === "number" ? value.toLocaleString("es") : value}`;
  });
}

type Fetcher = typeof fetch;

async function request(path: string, fetcher: Fetcher, body?: unknown): Promise<SalaResult> {
  let response: Response;
  try {
    response = await fetcher(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, message: NO_CONNECTION };
  }
  let data: (Partial<SalaSummary> & { message?: unknown }) | null = null;
  try {
    data = await response.json();
  } catch {
    // Respuesta sin JSON: se trata abajo como un fallo inesperado.
  }
  if (response.ok && typeof data?.code === "string" && typeof data.game === "string") {
    return { ok: true, sala: { code: data.code, game: data.game, status: data.status ?? "waiting" } };
  }
  return { ok: false, message: typeof data?.message === "string" ? data.message : UNEXPECTED };
}

/** Crea una sala de ese juego, con quien la pide de anfitrión. */
export function createSala(game: string, fetcher: Fetcher = fetch): Promise<SalaResult> {
  return request("/api/salas", fetcher, { game });
}

/** Entra en una sala con su código (o vuelve a ella). */
export function joinSala(code: string, fetcher: Fetcher = fetch): Promise<SalaResult> {
  return request(`/api/salas/${encodeURIComponent(code)}`, fetcher);
}

/** La sala en la que estoy, si estoy en alguna. */
export async function fetchMySala(fetcher: Fetcher = fetch): Promise<SalaSummary | null> {
  try {
    const response = await fetcher("/api/salas/mia", { credentials: "same-origin" });
    if (!response.ok) return null;
    return ((await response.json()) as { sala: SalaSummary | null }).sala;
  } catch {
    return null;
  }
}
