import type { User } from "../account";
import { Avatar } from "./Avatar";

interface Props {
  user: User | null; // null = jugando como invitado
  disabled: boolean; // se está cerrando la sesión
  onSignIn: () => void;
  onSignOut: () => void;
}

/** En la cabecera: quién soy y el botón para entrar o salir. */
export function AccountMenu({ user, disabled, onSignIn, onSignOut }: Props) {
  if (!user) {
    return (
      <button className="btn-dark h-9 px-3 text-sm" onClick={onSignIn}>
        Entrar
      </button>
    );
  }
  return (
    <div className="flex h-9 items-center gap-2 rounded-full bg-black/40 py-1 pl-1 pr-1.5 ring-1 ring-amber-400/35">
      <Avatar name={user.username} size={28} ring="ring-amber-300/70" />
      <span className="max-w-[9rem] truncate text-sm font-semibold" title="Tu cuenta">
        {user.username}
      </span>
      <button
        className="rounded-full px-2 py-0.5 text-xs font-semibold text-amber-200 hover:bg-white/10 disabled:opacity-50"
        disabled={disabled}
        onClick={onSignOut}
      >
        Salir
      </button>
    </div>
  );
}
