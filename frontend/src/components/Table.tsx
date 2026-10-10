import { streetName } from "../format";
import type { GameState, Seat } from "../types";
import { PlayingCard } from "./PlayingCard";

const STATUS_LABEL: Record<string, string> = {
  folded: "Retirado",
  all_in: "All-in",
  out: "Sin fichas",
};

function blindSeats(state: GameState) {
  const small = state.events.find((event) => event.kind === "small_blind")?.seat;
  const big = state.events.find((event) => event.kind === "big_blind")?.seat;
  return { small, big };
}

function SeatBox({ seat, state }: { seat: Seat; state: GameState }) {
  const toAct = state.hand_in_progress && state.to_act_seat === seat.seat;
  const { small, big } = blindSeats(state);
  const won = state.result?.payouts[String(seat.seat)];
  const handName = state.result?.hand_names?.[String(seat.seat)];
  const inHand = seat.status === "active" || seat.status === "all_in";
  const faded = seat.status === "folded" || seat.status === "out";

  const marks = [
    state.button_seat === seat.seat && "D",
    small === seat.seat && "CP",
    big === seat.seat && "CG",
  ].filter(Boolean);

  return (
    <div
      className={`rounded-lg border-2 p-3 ${toAct ? "border-amber-400 bg-slate-700" : "border-slate-700 bg-slate-800"} ${faded ? "opacity-50" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold">
            {seat.name}
            {seat.is_human && <span className="ml-1 text-xs text-emerald-400">(tú)</span>}
          </div>
          {!seat.is_human && (
            <div className="text-xs text-slate-400">
              {seat.level} · {seat.style}
            </div>
          )}
        </div>
        <div className="flex gap-1">
          {marks.map((mark) => (
            <span
              key={String(mark)}
              className="rounded bg-slate-200 px-1.5 text-xs font-bold text-slate-900"
              title={mark === "D" ? "Botón de dealer" : mark === "CP" ? "Ciega pequeña" : "Ciega grande"}
            >
              {mark}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-2 flex items-center gap-1">
        {seat.hole_cards
          ? seat.hole_cards.map((card) => <PlayingCard key={card} card={card} small />)
          : inHand && (
              <>
                <PlayingCard small />
                <PlayingCard small />
              </>
            )}
        {handName && <span className="ml-2 text-sm text-sky-300">{handName}</span>}
      </div>

      <div className="mt-2 flex items-center justify-between text-sm">
        <span>Fichas: {seat.stack}</span>
        {seat.bet > 0 && <span className="text-amber-300">Apuesta: {seat.bet}</span>}
        {STATUS_LABEL[seat.status] && (
          <span className="text-slate-300">{STATUS_LABEL[seat.status]}</span>
        )}
      </div>
      {toAct && !seat.is_human && <div className="mt-1 text-xs text-amber-300">Pensando…</div>}
      {won ? <div className="mt-1 text-sm font-semibold text-emerald-400">Gana {won}</div> : null}
    </div>
  );
}

export function Table({ state }: { state: GameState }) {
  const hidden = Array.from({ length: 5 - state.board.length });
  return (
    <section className="space-y-4">
      <div className="rounded-lg bg-emerald-900 p-4 text-center">
        <div className="text-sm text-emerald-200">
          Mano {state.hand_number} · {streetName(state.phase)} · Ciegas {state.small_blind}/
          {state.big_blind}
        </div>
        <div className="my-3 flex justify-center gap-2">
          {state.board.map((card) => (
            <PlayingCard key={card} card={card} />
          ))}
          {hidden.map((_, index) => (
            <span
              key={index}
              className="inline-block h-14 w-10 rounded border border-dashed border-emerald-700"
            />
          ))}
        </div>
        <div className="text-lg font-semibold">Bote: {state.pot}</div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {state.seats.map((seat) => (
          <SeatBox key={seat.seat} seat={seat} state={state} />
        ))}
      </div>
    </section>
  );
}
