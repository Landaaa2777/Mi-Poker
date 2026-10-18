import type { User } from "../account";
import { formatChips } from "../format";
import { Avatar } from "./Avatar";
import { ChipStack } from "./Chips";

interface Props {
  user: User;
  balance: number | null; // el saldo tal como debe verse ahora: sigue el ritmo de la mesa
  disabled: boolean; // se está cerrando la sesión
  onSignOut: () => void;
  onProfile: () => void;
}

/** En la cabecera: quién soy, mi saldo y el botón para salir. */
export function AccountMenu({ user, balance, disabled, onSignOut, onProfile }: Props) {
  return (
    <div className="flex h-9 items-center gap-1 rounded-full bg-black/40 py-1 pl-1 pr-1.5 ring-1 ring-amber-400/35">
      <button
        className="flex items-center gap-2 rounded-full pr-2 hover:bg-white/10"
        title="Ver tu perfil y tus estadísticas"
        onClick={onProfile}
      >
        <Avatar name={user.username} size={28} ring="ring-amber-300/70" />
        <span className="max-w-[9rem] truncate text-sm font-semibold">{user.username}</span>
        {balance !== null && (
          <span
            className="flex items-center gap-1 text-sm font-bold tabular-nums text-amber-300"
            aria-label={`Saldo: ${formatChips(balance)} fichas`}
          >
            <ChipStack className="h-4 w-4" />
            {formatChips(balance)}
          </span>
        )}
      </button>
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
