import { SUITS } from "../shapes";
import type { GameState } from "../types";

interface Props {
  state: GameState;
  settled: boolean; // la mesa ya enseña el último estado
  waiting: boolean; // hay una intención enviada sin respuesta
  send: (type: "draw" | "pass" | "challenge" | "accept" | "last" | "catch" | "next_round" | "restart") => void;
  onConfigure: () => void;
}

/**
 * El panel de decisiones: lo que puedo hacer ahora mismo. "¡Última!" y
 * "¡Pillado!" no esperan a la animación: hay que ser rápido.
 */
export function Controls({ state, settled, waiting, send, onConfigure }: Props) {
  const { legal } = state;
  const me = state.players[state.human_seat];
  const current = state.players[state.turn];
  const color = state.color ? SUITS[state.color] : null;
  const quick = (
    <div className="flex flex-wrap justify-center gap-2">
      {legal.declare && (
        <button className="btn-gold last-call h-12 px-5 text-base uppercase tracking-wide" disabled={waiting} onClick={() => send("last")}>
          ¡Última!
        </button>
      )}
      {legal.catch && (
        <button className="btn-red h-12 px-5 text-base uppercase tracking-wide" disabled={waiting} onClick={() => send("catch")}>
          ¡Pillado!
        </button>
      )}
    </div>
  );

  if (state.phase === "round_over") {
    if (!settled) return null;
    const winner = state.players[state.winner!];
    const won = winner.seat === state.human_seat;
    return (
      <div className="flex flex-col gap-3 text-center">
        <p className={`pop-in rounded-lg px-3 py-2 text-lg font-black ${won ? "bg-emerald-900/60 text-emerald-100" : "bg-black/40 text-amber-100"}`}>
          {won ? "¡Has ganado la ronda!" : `${winner.name} gana la ronda`}
        </p>
        {state.rules.scoring && (
          <ul className="text-sm text-stone-300">
            {[...state.players]
              .sort((a, b) => b.score - a.score)
              .map((player) => (
                <li key={player.seat} className={player.seat === state.human_seat ? "font-bold text-amber-200" : ""}>
                  {player.name}: {player.score} / {state.rules.target} puntos
                </li>
              ))}
          </ul>
        )}
        <div className="flex flex-wrap justify-center gap-2">
          {!state.game_over ? (
            <button className="btn-gold h-12 px-6" disabled={waiting} onClick={() => send("next_round")}>
              Siguiente ronda
            </button>
          ) : (
            <button className="btn-gold h-12 px-6" disabled={waiting} onClick={() => send("restart")}>
              Jugar otra
            </button>
          )}
          <button className="btn-dark h-12 px-5" onClick={onConfigure}>
            Cambiar configuración
          </button>
        </div>
      </div>
    );
  }

  if (legal.challenge && settled) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-sm text-amber-100">
          Te han echado un <strong>Camaleón +4</strong>. Si crees que era un farol (que tenían cartas del
          color de antes), desafíalo: si aciertas, roban ellos 4; si fallas, robas 6.
        </p>
        <div className="flex gap-2">
          <button className="btn-red h-12 flex-1 px-4" disabled={waiting} onClick={() => send("challenge")}>
            Desafiar
          </button>
          <button className="btn-dark h-12 flex-1 px-4" disabled={waiting} onClick={() => send("accept")}>
            Aceptar y robar 4
          </button>
        </div>
        {quick}
      </div>
    );
  }

  const myTurn = settled && (legal.play.length > 0 || legal.draw || legal.pass);
  return (
    <div className="flex flex-col items-center gap-3 text-center">
      {myTurn ? (
        <>
          <p className="text-sm text-amber-100">
            {state.drawn !== null
              ? "Has robado una carta que sirve: juégala o pásate."
              : legal.play.length > 0
                ? "Te toca: juega una carta resaltada o roba del mazo."
                : "Te toca: no tienes ninguna carta que case. Roba del mazo."}
            {color && (
              <>
                {" "}
                Color en juego: <strong style={{ color: color.color }}>{color.name}</strong>.
              </>
            )}
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {legal.draw && (
              <button className="btn-green h-12 px-6 text-base" disabled={waiting} onClick={() => send("draw")}>
                {state.pending_draw ? `Robar ${state.pending_draw}` : "Robar"}
              </button>
            )}
            {legal.pass && (
              <button className="btn-dark h-12 px-6 text-base" disabled={waiting} onClick={() => send("pass")}>
                Pasar
              </button>
            )}
          </div>
        </>
      ) : (
        <p className="flex min-h-12 items-center text-amber-100/60">
          {settled && current && !current.is_human ? `Turno de ${current.name}…` : " "}
        </p>
      )}
      {me.count === 2 && legal.declare && (
        <p className="text-xs text-stone-400">Vas a quedarte con una carta: avisa con «¡Última!».</p>
      )}
      {quick}
    </div>
  );
}
