import { useId, useState, type FormEvent } from "react";
import {
  EMAIL_MAX,
  PASSWORD_MAX,
  PASSWORD_MIN,
  USERNAME_MAX,
  USERNAME_MIN,
  checkCredentials,
  login,
  register,
  rememberSignedIn,
  signedInBefore,
  type AccountMode,
} from "../account";
import { INPUT } from "./form";

interface Props {
  onSignedIn: () => void; // ya hay sesión: toca leer la cuenta del servidor
}

const TABS: { mode: AccountMode; label: string }[] = [
  { mode: "register", label: "Crear cuenta" },
  { mode: "login", label: "Entrar" },
];

const LABEL = "mb-1.5 block text-xs font-bold uppercase tracking-[0.16em] text-amber-200/75";
const HINT = "mt-1 block text-xs text-stone-400";

/** Un ojo (pulsa para ver la contraseña) o un ojo tachado (pulsa para ocultarla). */
function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" />
      {!open && <path d="M4 20 20 4" strokeLinecap="round" />}
    </svg>
  );
}

/**
 * Crear una cuenta o entrar. Sin sesión es lo único que se ve: hace falta una
 * cuenta para jugar. Crearla pide lo mínimo (un nombre y una contraseña); el
 * correo es opcional y solo sirve para entrar con él.
 */
export function SignInPanel({ onSignedIn }: Props) {
  // Quien ya entró alguna vez con este navegador seguramente quiere "Entrar".
  const [mode, setMode] = useState<AccountMode>(() => (signedInBefore() ? "login" : "register"));
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const id = useId();
  const creating = mode === "register";

  function change(next: AccountMode) {
    setMode(next);
    setProblem(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (sending) return;
    const invalid = checkCredentials(mode, username, password, creating ? email : "");
    if (invalid) {
      setProblem(invalid);
      return;
    }
    setSending(true);
    setProblem(null);
    const result = creating
      ? await register(username, password, email)
      : await login(username, password);
    setSending(false);
    if (result.ok) {
      rememberSignedIn();
      onSignedIn();
    } else {
      setProblem(result.message);
    }
  }

  return (
    <section aria-labelledby={`${id}-title`} className="panel w-full p-5 sm:p-6">
      <h2 id={`${id}-title`} className="gold-text text-xl font-black">
        {creating ? "Crea tu cuenta" : "Entra en tu cuenta"}
      </h2>
      <p className="mt-1 text-sm text-stone-300">
        {creating ? "Solo un nombre y una contraseña." : "Con tu nombre de usuario o tu correo."}
      </p>

      <div
        className="mt-4 grid grid-cols-2 overflow-hidden rounded-full border border-amber-400/40 bg-black/50 text-sm font-extrabold"
        role="tablist"
        aria-label="Crear cuenta o entrar"
      >
        {TABS.map((tab) => (
          <button
            key={tab.mode}
            type="button"
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
        <div>
          <label htmlFor={`${id}-user`} className={LABEL}>
            {creating ? "Nombre de usuario" : "Usuario o correo"}
          </label>
          <input
            id={`${id}-user`}
            type="text"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            maxLength={creating ? USERNAME_MAX : EMAIL_MAX}
            className={INPUT}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
          {creating && (
            <span className={HINT}>
              Es tu nombre en todas las mesas: de {USERNAME_MIN} a {USERNAME_MAX} letras sin acento,
              números, - o _.
            </span>
          )}
        </div>

        <div>
          <label htmlFor={`${id}-password`} className={LABEL}>
            Contraseña
          </label>
          <div className="relative">
            <input
              id={`${id}-password`}
              type={showPassword ? "text" : "password"}
              name="password"
              autoComplete={creating ? "new-password" : "current-password"}
              maxLength={PASSWORD_MAX}
              className={`${INPUT} pr-11`}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-amber-200/75 hover:text-amber-100 focus-visible:outline-2 focus-visible:outline-amber-300"
              aria-label={showPassword ? "Ocultar la contraseña" : "Mostrar la contraseña"}
              aria-pressed={showPassword}
              onClick={() => setShowPassword((shown) => !shown)}
            >
              <EyeIcon open={!showPassword} />
            </button>
          </div>
          {creating && <span className={HINT}>Al menos {PASSWORD_MIN} caracteres.</span>}
        </div>

        {creating && (
          <div>
            <label htmlFor={`${id}-email`} className={LABEL}>
              Correo <span className="normal-case tracking-normal text-stone-400">(opcional)</span>
            </label>
            <input
              id={`${id}-email`}
              type="email"
              name="email"
              autoComplete="email"
              autoCapitalize="none"
              spellCheck={false}
              maxLength={EMAIL_MAX}
              className={INPUT}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <span className={HINT}>Solo sirve para entrar con él. No se verifica ni lo ve nadie más.</span>
          </div>
        )}

        {problem && (
          <p role="alert" className="text-sm font-semibold text-amber-300">
            {problem}
          </p>
        )}

        <button type="submit" disabled={sending} className="btn-gold h-12 w-full uppercase tracking-wide">
          {sending ? "Un momento…" : creating ? "Crear cuenta y jugar" : "Entrar"}
        </button>
      </form>

      <p className="mt-4 text-xs leading-relaxed text-stone-400">
        {creating ? (
          "Una contraseña olvidada no se puede recuperar: apúntala en un lugar seguro."
        ) : (
          <>
            ¿Es tu primera vez?{" "}
            <button
              type="button"
              className="font-semibold text-amber-200 underline underline-offset-2 hover:text-amber-100"
              onClick={() => change("register")}
            >
              Crea una cuenta
            </button>{" "}
            en un momento.
          </>
        )}
      </p>
    </section>
  );
}
