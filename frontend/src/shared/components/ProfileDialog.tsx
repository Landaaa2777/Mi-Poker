import { useEffect, useId, useState, type ReactNode } from "react";
import { fetchProfile, percent, type Profile, type User } from "../account";
import { formatChips } from "../format";
import { Avatar } from "./Avatar";

interface Props {
  user: User;
  balance: number | null; // el saldo tal como debe verse ahora
  onClose: () => void;
  onSignOut: () => void;
}

const dateFormat = new Intl.DateTimeFormat("es", { day: "numeric", month: "long", year: "numeric" });

function Tile({ label, children, note }: { label: string; children: ReactNode; note?: string }) {
  return (
    <div className="rounded-xl border border-amber-400/25 bg-black/35 px-3 py-2.5">
      <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-amber-200/70">
        {label}
      </div>
      <div className="mt-0.5 text-xl font-black tabular-nums text-amber-100">{children}</div>
      {note && <div className="text-xs text-stone-400">{note}</div>}
    </div>
  );
}

/** Ventana de perfil: quién soy y cómo me ha ido en las manos jugadas con la cuenta. */
export function ProfileDialog({ user, balance, onClose, onSignOut }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const title = useId();

  // Se pide cada vez que se abre: las estadísticas cambian con cada mano.
  useEffect(() => {
    let closed = false;
    void fetchProfile().then((result) => {
      if (closed) return;
      if (result.ok) setProfile(result.profile);
      else setProblem(result.message);
    });
    return () => {
      closed = true;
    };
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const stats = profile?.stats;
  const total = stats?.total;
  const since = profile?.user.member_since;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={title}
        className="panel pop-in quiet-scroll max-h-full w-full max-w-lg overflow-y-auto p-5"
      >
        <div className="flex items-center gap-3">
          <Avatar name={user.username} size={52} ring="ring-amber-300/70" />
          <div className="min-w-0 flex-1">
            <h2 id={title} className="gold-text truncate text-xl font-black">
              {user.username}
            </h2>
            <p className="text-xs text-stone-400">
              {since ? `Cuenta creada el ${dateFormat.format(new Date(since * 1000))}` : " "}
            </p>
            {profile?.user.email && (
              <p className="truncate text-xs text-stone-400">Correo: {profile.user.email}</p>
            )}
          </div>
          <button className="btn-dark h-8 w-8 shrink-0 text-sm" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
        </div>

        {balance !== null && (
          <div className="mt-4 flex items-baseline justify-between rounded-xl border border-amber-400/40 bg-black/45 px-4 py-3">
            <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-amber-200/70">
              Saldo
            </span>
            <span className="text-2xl font-black tabular-nums text-amber-300">
              {formatChips(balance)}
              <span className="ml-1.5 text-xs font-semibold text-stone-400">fichas virtuales</span>
            </span>
          </div>
        )}

        {problem && (
          <p role="alert" className="mt-4 text-sm font-semibold text-amber-300">
            {problem}
          </p>
        )}
        {!profile && !problem && <p className="mt-4 text-sm text-stone-400">Cargando…</p>}

        {total && total.hands_played === 0 && (
          <p className="mt-4 rounded-xl border border-amber-400/25 bg-black/35 px-3 py-4 text-center text-sm text-stone-300">
            Todavía no has terminado ninguna mano con esta cuenta. Juega una y vuelve por aquí.
          </p>
        )}

        {stats && total && total.hands_played > 0 && (
          <>
            <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
              <Tile label="Manos jugadas">{formatChips(total.hands_played)}</Tile>
              <Tile
                label="Manos ganadas"
                note={`${percent(total.hands_won, total.hands_played)} % de las jugadas`}
              >
                {formatChips(total.hands_won)}
              </Tile>
              <Tile label="Mayor bote ganado" note="fichas, en una mano">
                {formatChips(total.biggest_win)}
              </Tile>
              <Tile label="Mejor mano" note={total.best_hand ? "enseñada en un showdown" : undefined}>
                {total.best_hand ?? "—"}
              </Tile>
              <Tile label="Partidas jugadas">{formatChips(total.games_played)}</Tile>
              <Tile label="Partidas ganadas" note="dejando sin fichas a todos">
                {formatChips(total.games_won)}
              </Tile>
            </div>

            <h3 className="mt-5 text-xs font-bold uppercase tracking-[0.16em] text-amber-200/75">
              Según el nivel de los rivales
            </h3>
            <table className="mt-2 w-full text-sm tabular-nums">
              <thead>
                <tr className="text-left text-xs text-stone-400">
                  <th className="py-1 font-semibold">Nivel</th>
                  <th className="py-1 text-right font-semibold">Manos</th>
                  <th className="py-1 text-right font-semibold">Ganadas</th>
                  <th className="py-1 text-right font-semibold">Partidas ganadas</th>
                </tr>
              </thead>
              <tbody>
                {stats.levels.map((level) => (
                  <tr key={level.difficulty} className="border-t border-amber-400/15">
                    <td className="py-1.5 font-semibold text-amber-100">{level.name}</td>
                    <td className="py-1.5 text-right">{formatChips(level.hands_played)}</td>
                    <td className="py-1.5 text-right">
                      {formatChips(level.hands_won)}
                      <span className="text-stone-400">
                        {" "}
                        ({percent(level.hands_won, level.hands_played)} %)
                      </span>
                    </td>
                    <td className="py-1.5 text-right">
                      {formatChips(level.games_won)}
                      <span className="text-stone-400"> de {formatChips(level.games_played)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <div className="mt-5 flex items-center justify-between gap-3">
          <p className="text-xs leading-relaxed text-stone-400">
            Solo cuentan las manos que terminas con la sesión iniciada.
          </p>
          <button className="btn-dark h-9 shrink-0 px-3 text-sm" onClick={onSignOut}>
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  );
}
