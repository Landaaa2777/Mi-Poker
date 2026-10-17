// Cuenta del jugador: registrarse, entrar y salir. Todo lo que la aplicación
// sabe de cuentas pasa por este módulo, igual que el invitado pasa por `guest.ts`.
//
// La sesión va en una cookie que este código no puede leer. Quién soy lo dice
// el servidor al conectar con la mesa (mensaje "hello"), no se guarda aquí.

export interface User {
  username: string;
  balance: number; // fichas virtuales de la cuenta, contando las que tenga en la mesa
}

/** Lo acumulado en las manos jugadas con la cuenta. */
export interface Stats {
  hands_played: number;
  hands_won: number;
  biggest_win: number; // lo máximo cobrado en una sola mano
  best_hand: string | null; // la mejor mano enseñada en un showdown, por su nombre
  games_played: number;
  games_won: number;
}

export interface LevelStats extends Stats {
  difficulty: string;
  name: string; // nombre del nivel de los rivales
}

export interface Profile {
  user: User & { member_since: number | null }; // segundos desde 1970
  stats: { total: Stats; levels: LevelStats[] };
}

export type ProfileResult = { ok: true; profile: Profile } | { ok: false; message: string };

export type RefillResult = { ok: true; balance: number } | { ok: false; message: string };

export type AccountMode = "login" | "register";

export type AccountResult = { ok: true; user: User | null } | { ok: false; message: string };

// Las mismas reglas que aplica el servidor, que es quien decide de verdad.
export const USERNAME_MIN = 3;
export const USERNAME_MAX = 16;
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

const NO_CONNECTION = "Sin conexión con el servidor. Inténtalo otra vez.";
const UNEXPECTED = "No se pudo completar. Inténtalo otra vez.";

/** El primer problema de lo que se va a enviar, o `null` si se puede enviar. */
export function checkCredentials(
  mode: AccountMode,
  username: string,
  password: string,
  repeat: string,
): string | null {
  const name = username.trim();
  if (mode === "login") {
    return name && password ? null : "Escribe tu usuario y tu contraseña.";
  }
  if (name.length < USERNAME_MIN || name.length > USERNAME_MAX) {
    return `El nombre de usuario debe tener entre ${USERNAME_MIN} y ${USERNAME_MAX} caracteres.`;
  }
  if (!/^[A-Za-z0-9_-]+$/.test(name)) {
    return "El nombre de usuario solo puede llevar letras sin acento, números, guion y guion bajo.";
  }
  if (password.length < PASSWORD_MIN) {
    return `La contraseña debe tener al menos ${PASSWORD_MIN} caracteres.`;
  }
  if (password.length > PASSWORD_MAX) {
    return `La contraseña no puede pasar de ${PASSWORD_MAX} caracteres.`;
  }
  return password === repeat ? null : "Las dos contraseñas no coinciden.";
}

/** Porcentaje entero de `part` sobre `whole`; 0 si no hay nada sobre lo que calcular. */
export function percent(part: number, whole: number): number {
  return whole > 0 ? Math.round((100 * part) / whole) : 0;
}

type Fetcher = typeof fetch;

async function post(path: string, body: unknown, fetcher: Fetcher): Promise<AccountResult> {
  let response: Response;
  try {
    response = await fetcher(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin", // para que viaje la cookie de sesión
    });
  } catch {
    return { ok: false, message: NO_CONNECTION };
  }
  let data: { user?: User | null; message?: unknown } | null = null;
  try {
    data = await response.json();
  } catch {
    // Respuesta sin JSON: se trata abajo como un fallo inesperado.
  }
  if (response.ok && data && "user" in data) return { ok: true, user: data.user ?? null };
  const message = typeof data?.message === "string" ? data.message : UNEXPECTED;
  return { ok: false, message };
}

export function register(username: string, password: string, fetcher: Fetcher = fetch) {
  return post("/api/register", { username: username.trim(), password }, fetcher);
}

export function login(username: string, password: string, fetcher: Fetcher = fetch) {
  return post("/api/login", { username: username.trim(), password }, fetcher);
}

export function logout(fetcher: Fetcher = fetch) {
  return post("/api/logout", {}, fetcher);
}

/** Quién soy según el servidor: la cuenta de la cookie de sesión, o null si juego como invitado. */
export async function fetchMe(fetcher: Fetcher = fetch): Promise<User | null> {
  try {
    const response = await fetcher("/api/me", { credentials: "same-origin" });
    const data = (await response.json()) as { user?: User | null };
    return data.user ?? null;
  } catch {
    return null; // sin conexión: hasta que vuelva, como invitado
  }
}

/** Recarga gratis de fichas. El servidor solo la concede a quien se ha quedado sin ellas. */
export async function refill(fetcher: Fetcher = fetch): Promise<RefillResult> {
  let response: Response;
  try {
    response = await fetcher("/api/refill", { method: "POST", credentials: "same-origin" });
  } catch {
    return { ok: false, message: NO_CONNECTION };
  }
  let data: { balance?: unknown; message?: unknown } | null = null;
  try {
    data = await response.json();
  } catch {
    // Respuesta sin JSON: se trata abajo como un fallo inesperado.
  }
  if (response.ok && typeof data?.balance === "number") return { ok: true, balance: data.balance };
  return { ok: false, message: typeof data?.message === "string" ? data.message : UNEXPECTED };
}

/** El perfil de la cuenta con la que hay sesión: quién es y sus estadísticas. */
export async function fetchProfile(fetcher: Fetcher = fetch): Promise<ProfileResult> {
  let response: Response;
  try {
    response = await fetcher("/api/profile", { credentials: "same-origin" });
  } catch {
    return { ok: false, message: NO_CONNECTION };
  }
  let data: (Partial<Profile> & { message?: unknown }) | null = null;
  try {
    data = await response.json();
  } catch {
    // Respuesta sin JSON: se trata abajo como un fallo inesperado.
  }
  if (response.ok && data?.user && data.stats) {
    return { ok: true, profile: { user: data.user, stats: data.stats } };
  }
  return { ok: false, message: typeof data?.message === "string" ? data.message : UNEXPECTED };
}
