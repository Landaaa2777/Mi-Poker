// Cuenta del jugador: registrarse, entrar y salir. Todo lo que la aplicación
// sabe de cuentas pasa por este módulo, igual que el invitado pasa por `guest.ts`.
//
// La sesión va en una cookie que este código no puede leer. Quién soy lo dice
// el servidor al conectar con la mesa (mensaje "hello"), no se guarda aquí.

export interface User {
  username: string;
}

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
