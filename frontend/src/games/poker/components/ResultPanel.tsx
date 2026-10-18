import { formatChips } from "../format";
import type { GameState } from "../types";

interface Props {
  state: GameState;
  balance: number | null; // mi saldo; null si juego como invitado
  disabled: boolean; // ya se envió una intención y el servidor aún no ha contestado
  onNextHand?: () => void;
  onRestart?: () => void;
  onConfigure?: () => void;
  /** En una sala: las manos se reparten solas y no hay botones. */
  room?: boolean;
}

const BIG = "h-14 flex-1 whitespace-nowrap px-5 text-base uppercase tracking-wide sm:text-lg";

/** Resultado de la mano y qué se puede hacer después. */
export function ResultPanel({ state, balance, disabled, onNextHand, onRestart, onConfigure, room = false }: Props) {
  const result = state.result;
  if (!result || state.hand_in_progress) return null;

  const name = (seat: number | string) =>
    state.seats.find((candidate) => candidate.seat === Number(seat))?.name ?? "";
  const finished = state.human_out || state.game_over;
  const stack = state.config.starting_stack;
  // Con cuenta, repetir la mesa cuesta otra vez sus fichas: hay que tenerlas.
  const canRepeat = balance === null || balance >= stack;

  let headline: string | null = null;
  if (room) {
    const winner = state.seats.find((seat) => seat.seat === state.winner_seat);
    if (state.game_over) {
      headline = winner?.is_human
        ? "¡Has ganado la partida!"
        : winner
          ? `${winner.name} gana la partida.`
          : "La partida ha terminado.";
    } else if (state.human_out) {
      headline = "Te has quedado sin fichas: la partida sigue sin ti.";
    }
  } else if (state.human_out) {
    headline = balance === null ? "Te quedaste sin fichas." : "Te quedaste sin fichas en esta mesa.";
  } else if (state.game_over) {
    headline = "¡Ganaste la partida! Eliminaste a todos los bots.";
  }

  return (
    <div className="flex h-full flex-col justify-between gap-3">
      <div className="space-y-1.5">
        <h2 className="gold-text text-xs font-extrabold uppercase tracking-[0.2em]">
          {result.showdown ? "Showdown" : "Todos los demás se retiraron"}
        </h2>
        <ul className="space-y-0.5 text-sm">
          {result.awards.map((award, index) => (
            <li key={index}>
              <span className="text-stone-400">
                {index === 0 ? "Bote principal" : `Bote lateral ${index}`} ({award.amount}):
              </span>{" "}
              {Object.entries(award.payouts)
                .map(([seat, amount]) => {
                  const hand = result.hand_names[seat];
                  return `${name(seat)} +${amount}${hand ? ` (${hand})` : ""}`;
                })
                .join(", ")}
            </li>
          ))}
        </ul>
        {headline && <p className="text-lg font-bold text-amber-300">{headline}</p>}
      </div>

      {room && !state.game_over && state.next_hand_in != null && (
        <p className="pb-1 text-sm text-amber-100/70">La siguiente mano se reparte enseguida…</p>
      )}
      {!room && (
        <div className="flex flex-wrap items-center gap-2.5 pb-1">
          {finished && canRepeat && (
            <button className={`${BIG} btn-gold`} disabled={disabled} onClick={onRestart}>
              Reiniciar partida
            </button>
          )}
          {finished && !canRepeat && (
            <button className={`${BIG} btn-gold`} onClick={onConfigure}>
              Elegir otra mesa
            </button>
          )}
          {!finished && (
            <button className={`${BIG} btn-green`} disabled={disabled} onClick={onNextHand}>
              Siguiente mano
            </button>
          )}
          {(!finished || canRepeat) && (
            <button className="btn-dark h-14 px-4 text-sm" onClick={onConfigure}>
              Cambiar configuración
            </button>
          )}
        </div>
      )}
      {finished && !room && (
        <p className="text-xs text-stone-400">
          {balance === null
            ? "Al reiniciar recibes fichas virtuales nuevas, gratis."
            : canRepeat
              ? `Al reiniciar te sientas otra vez con ${formatChips(stack)} fichas de tu saldo.`
              : `Tu saldo no llega a las ${formatChips(stack)} fichas de esta mesa.`}
        </p>
      )}
    </div>
  );
}
