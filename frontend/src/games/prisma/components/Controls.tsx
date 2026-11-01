import { SUITS } from "../shapes";
import type { GameState } from "../types";

// El desafío de cada comodín restringido: qué es, qué pasa si aciertas o fallas
// y qué robas si lo aceptas.
const CHALLENGES: Record<string, { name: string; win: string; lose: string; accept: string }> = {
  camaleon4: { name: "Camaleón +4", win: "roban ellos 4", lose: "robas 6", accept: "Aceptar y robar 4" },
  camaleon2: { name: "Camaleón +2", win: "roban ellos 2", lose: "robas 4", accept: "Aceptar y robar 2" },
  sabueso: {
    name: "Camaleón Sabueso",
    win: "roban ellos hasta sacar el color",
    lose: "robas hasta sacarlo y 2 más",
    accept: "Aceptar y robar hasta el color",
  },
};

interface Props {
  state: GameState;
  settled: boolean; // la mesa ya enseña el último estado
  waiting: boolean; // hay una intención enviada sin respuesta
  send: (type: "draw" | "pass" | "challenge" | "accept" | "last" | "catch" | "next_round" | "restart") => void;
  onConfigure?: () => void;
  /** En una sala: las rondas siguen solas y no hay botones para ellas. */
  room?: boolean;
}

/**
 * El panel de decisiones: lo que puedo hacer ahora mismo. "¡Última!" y
 * "¡Pillado!" no esperan a la animación: hay que ser rápido.
 */
export function Controls({ state, settled, waiting, send, onConfigure, room = false }: Props) {
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
          {room && state.game_over
            ? won
              ? "¡Has ganado la partida!"
              : `${winner.name} gana la partida`
            : won
              ? "¡Has ganado la ronda!"
              : `${winner.name} gana la ronda`}
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
        {room && !state.game_over && <p className="text-sm text-amber-100/70">La ronda siguiente empieza enseguida…</p>}
        {!room && (
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
        )}
      </div>
    );
  }

  if (legal.challenge && settled) {
    const wild = CHALLENGES[state.top.kind] ?? CHALLENGES.camaleon4;
    return (
      <div className="flex flex-col gap-3">
        <p className="text-sm text-amber-100">
          Te han echado un <strong>{wild.name}</strong>. Si crees que era un farol (que tenían cartas del
          color de antes), desafíalo: si aciertas, {wild.win}; si fallas, {wild.lose}.
        </p>
        <div className="flex gap-2">
          <button className="btn-red h-12 flex-1 px-4" disabled={waiting} onClick={() => send("challenge")}>
            Desafiar
          </button>
          <button className="btn-dark h-12 flex-1 px-4" disabled={waiting} onClick={() => send("accept")}>
            {wild.accept}
          </button>
        </div>
        {quick}
      </div>
    );
  }

  if (me.out && state.phase !== "roulette") {
    return (
      <p className="text-center text-amber-100/80">
        Te has desbordado: quedas fuera de esta ronda. Tus cartas esperan apartadas hasta que se rebaraje.
      </p>
    );
  }

  const myTurn = settled && (legal.play.length > 0 || legal.draw || legal.pass);
  const relentless = state.mode === "sin_tregua";
  // Lo que me toca hacer, en una frase.
  let prompt: string;
  if (state.drawn !== null) prompt = "Has robado una carta que sirve: juégala o pásate.";
  else if (state.pending_draw > 0 && relentless)
    prompt =
      legal.play.length > 0
        ? `Te llegan ${state.pending_draw} cartas acumuladas: responde con una carga de +${state.pending_min} o más para pasarlas, o róbalas.`
        : `Te llegan ${state.pending_draw} cartas acumuladas y no tienes con qué responder: te toca robarlas.`;
  else if (state.pending_draw > 0)
    prompt =
      legal.play.length > 0
        ? `Te llegan ${state.pending_draw} cartas acumuladas: suma otra igual o róbalas.`
        : `Te llegan ${state.pending_draw} cartas acumuladas: te toca robarlas.`;
  else if (legal.play.length > 0)
    prompt = relentless
      ? "Te toca: juega una carta resaltada o roba hasta sacar una que sirva."
      : "Te toca: juega una carta resaltada o roba del mazo.";
  else
    prompt = relentless
      ? "Te toca: no tienes ninguna carta que case. Roba hasta sacar una que sirva."
      : "Te toca: no tienes ninguna carta que case. Roba del mazo.";
  return (
    <div className="flex flex-col items-center gap-3 text-center">
      {myTurn ? (
        <>
          <p className="text-sm text-amber-100">
            {prompt}
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
                {state.pending_draw ? `Robar ${state.pending_draw}` : relentless ? "Robar hasta poder" : "Robar"}
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
          {settled && current && !current.is_human && !(room && current.person) ? `Turno de ${current.name}…` : " "}
        </p>
      )}
      {me.count === 2 && legal.declare && (
        <p className="text-xs text-stone-400">Vas a quedarte con una carta: avisa con «¡Última!».</p>
      )}
      {quick}
    </div>
  );
}
