// Identificador de invitado. Es lo único que identifica al jugador en la etapa 1.
// Está aislado en este módulo para poder sustituirlo por un login más adelante:
// el resto de la aplicación solo llama a `getGuestId()`.

const STORAGE_KEY = "mi-poker.guest-id";

function newGuestId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function getGuestId(): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return saved;
    const created = newGuestId();
    localStorage.setItem(STORAGE_KEY, created);
    return created;
  } catch {
    // Sin almacenamiento (modo privado estricto): un identificador solo para esta pestaña.
    return newGuestId();
  }
}
