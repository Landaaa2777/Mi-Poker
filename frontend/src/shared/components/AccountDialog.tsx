import { useEffect, useId, useState, type FormEvent } from "react";
import {
  PASSWORD_MAX,
  PASSWORD_MIN,
  USERNAME_MAX,
  checkCredentials,
  login,
  register,
  type AccountMode,
} from "../account";

interface Props {
  onClose: () => void;
  onSignedIn: () => void; // ya hay sesión: toca volver a conectar con la mesa
}

const TABS: { mode: AccountMode; label: string }[] = [
  { mode: "login", label: "Entrar" },
  { mode: "register", label: "Crear cuenta" },
];

const INPUT =
  "w-full rounded-lg border border-amber-400/30 bg-black/45 px-3 py-2 outline-none focus:border-amber-300";
const LABEL = "mb-1.5 block text-xs font-bold uppercase tracking-[0.16em] text-amber-200/75";

/** Ventana para entrar con una cuenta o crear una nueva. */
export function AccountDialog({ onClose, onSignedIn }: Props) {
  const [mode, setMode] = useState<AccountMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const title = useId();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  function change(next: AccountMode) {
    setMode(next);
    setProblem(null);
    setRepeat("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (sending) return;
    const invalid = checkCredentials(mode, username, password, repeat);
    if (invalid) {
      setProblem(invalid);
      return;
    }
    setSending(true);
    setProblem(null);
    const result = await (mode === "login" ? login : register)(username, password);
    setSending(false);
    if (result.ok) onSignedIn();
    else setProblem(result.message);
  }

  const creating = mode === "register";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div role="dialog" aria-modal="true" aria-labelledby={title} className="panel pop-in w-full max-w-sm p-5">
        <div className="flex items-center justify-between">
          <h2 id={title} className="gold-text text-lg font-black">
            Tu cuenta
          </h2>
          <button className="btn-dark h-8 w-8 text-sm" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
        </div>

        <div
          className="mt-4 grid grid-cols-2 overflow-hidden rounded-full border border-amber-400/40 bg-black/50 text-sm font-extrabold"
          role="tablist"
        >
          {TABS.map((tab) => (
            <button
              key={tab.mode}
              role="tab"
              aria-selected={mode === tab.mode}
              className={`py-2 ${mode === tab.mode ? "bg-gradient-to-b from-[#d6b160] to-[#b0862f] text-stone-900" : "text-amber-100 hover:bg-white/10"}`}
              onClick={() => change(tab.mode)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <form className="mt-4 space-y-4" onSubmit={submit} noValidate>
          <label className="block">
            <span className={LABEL}>Usuario</span>
            <input
              type="text"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              autoFocus
              maxLength={USERNAME_MAX}
              className={INPUT}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label className="block">
            <span className={LABEL}>Contraseña</span>
            <input
              type="password"
              name="password"
              autoComplete={creating ? "new-password" : "current-password"}
              maxLength={PASSWORD_MAX}
              className={INPUT}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {creating && (
            <label className="block">
              <span className={LABEL}>Repite la contraseña</span>
              <input
                type="password"
                name="repeat"
                autoComplete="new-password"
                maxLength={PASSWORD_MAX}
                className={INPUT}
                value={repeat}
                onChange={(event) => setRepeat(event.target.value)}
              />
            </label>
          )}

          {problem && (
            <p role="alert" className="text-sm font-semibold text-amber-300">
              {problem}
            </p>
          )}

          <button type="submit" disabled={sending} className="btn-gold h-12 w-full uppercase tracking-wide">
            {creating ? "Crear cuenta" : "Entrar"}
          </button>
        </form>

        <p className="mt-4 text-xs leading-relaxed text-stone-400">
          {creating
            ? `Mínimo ${PASSWORD_MIN} caracteres. No se pide correo, así que una contraseña olvidada no se puede recuperar: apúntala.`
            : "Sin cuenta puedes seguir jugando como invitado."}
        </p>
      </div>
    </div>
  );
}
