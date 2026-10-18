import { useEffect, useRef, useState } from "react";
import { useAccount } from "../../shared/AccountContext";
import { audio } from "../../shared/audio/engine";
import { preloadFaces } from "../../shared/cards/CardFace";
import { EventLog } from "../../shared/components/EventLog";
import { TurnClock } from "../../shared/components/TurnClock";
import { formatChips } from "../../shared/format";
import { HeaderContent } from "../../shared/Layout";
import type { RoomViewProps } from "../../shared/room";
import { usePlatformSettings } from "../../shared/SettingsContext";
import { usePlayback } from "../../shared/timeline/usePlayback";
import { BlackjackTable } from "./components/BlackjackTable";
import { ActionControls, BetControls, InsurancePrompt, RoundSummary } from "./components/Controls";
import { logLines } from "./describe";
import { tableEffects } from "./effects";
import { BLACKJACK_TIMELINE } from "./timeline";
import type { GameState } from "./types";

/**
 * La mesa de blackjack de una sala: varias personas contra el crupier. Para
 * empezar cada ronda apuestan todas; desde la primera apuesta, las demás
 * tienen su cuenta atrás.
 */
export default function BlackjackRoom({ play }: RoomViewProps) {
  const { animations } = usePlatformSettings();
  const { setTableBalance } = useAccount();
  // Mi asiento, para los sonidos (el de ganar solo suena con lo mío).
  const myself = useRef(0);
  const [effects] = useState(() => tableEffects(() => myself.current));
  const { frame, server, busy, push } = usePlayback(BLACKJACK_TIMELINE, animations, effects);
  const { subscribe, send, waiting } = play;

  useEffect(() => subscribe((state, instant) => push(state as GameState, instant)), [subscribe, push]);
  useEffect(() => {
    if (server) myself.current = server.human_seat;
  }, [server]);
  useEffect(preloadFaces, []);

  // La última apuesta: la siguiente ronda empieza con ella.
  const [lastBet, setLastBet] = useState(0);

  // El saldo de la cabecera va al ritmo de la mesa.
  const [balance, setBalance] = useState<number | null>(null);
  useEffect(() => {
    if (!busy && server) setBalance(server.balance);
  }, [busy, server]);
  useEffect(() => {
    if (balance !== null) setTableBalance(balance);
  }, [balance, setTableBalance]);
  useEffect(() => () => setTableBalance(undefined), [setTableBalance]);

  const settled = !busy;
  const myTurn = settled && server?.legal_actions != null && server.legal_actions.length > 0;
  const insurance = settled && server?.insurance_offered === true;
  const canBet =
    settled &&
    server !== null &&
    !server.round_in_progress &&
    !server.human_out &&
    !server.game_over &&
    server.my_bet == null;
  useEffect(() => {
    if (myTurn || insurance || canBet) audio.play("turn");
  }, [myTurn, insurance, canBet]);

  if (!frame || !server) {
    return <p className="panel px-3 py-2 text-sm">Preparando la mesa…</p>;
  }

  const me = server.seats[server.human_seat];
  const acting = frame.acting ? frame.seats[frame.acting.seat] : null;
  const timer = server.timer ?? null;
  // Quién más falta por apostar para que empiece la ronda.
  const missing = server.seats
    .filter((seat) => seat.person && !seat.is_human && !seat.gone && seat.can_bet && !seat.bet_ready)
    .map((seat) => seat.name);
  const betting = !server.round_in_progress && !server.game_over;

  function bet(amount: number) {
    setLastBet(amount);
    send({ type: "bet", amount });
  }

  return (
    <>
      <HeaderContent
        info={
          <span className="text-sm text-amber-100/60">
            Ronda {server.round_number} · Apuestas {server.rules.min_bet}–{server.rules.max_bet}
          </span>
        }
      />
      <BlackjackTable
        frame={frame}
        rules={server.rules}
        shoe={{ remaining: server.shoe.remaining, total: server.shoe.total, cutReached: server.shoe.cut_reached }}
        settled={settled}
      />

      <div className="grid gap-3 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <section className="panel flex min-h-48 flex-col items-center justify-center gap-3 p-3 lg:order-2" aria-live="polite">
          {server.phase === "complete" && settled && <RoundSummary state={server} />}
          {insurance && (
            <>
              <TurnClock timer={timer} label="Decide el seguro" />
              <InsurancePrompt
                cost={(me?.hands[0]?.bet ?? 0) / 2}
                disabled={waiting}
                onDecide={(take) => send({ type: "insurance", take })}
              />
            </>
          )}
          {myTurn && (
            <>
              <TurnClock timer={timer} label="Te toca" />
              <div className="w-full">
                <ActionControls
                  legal={server.legal_actions!}
                  disabled={waiting}
                  onAction={(action) => send({ type: "action", action })}
                />
              </div>
            </>
          )}
          {canBet && (
            <>
              <TurnClock timer={timer} label="Apuesta para la siguiente ronda" />
              <div className="w-full">
                <BetControls
                  key={server.round_number}
                  state={server}
                  lastBet={lastBet || server.rules.min_bet}
                  disabled={waiting}
                  onBet={bet}
                  label="Apostar"
                />
              </div>
            </>
          )}
          {settled && betting && server.my_bet != null && (
            <div className="flex w-full flex-col items-center gap-2 text-center">
              <p className="text-amber-100">
                Has apostado <strong>{formatChips(server.my_bet)}</strong>.
                {missing.length > 0 && ` Falta que apueste: ${missing.join(", ")}.`}
              </p>
              <TurnClock timer={timer} label="Apuestas" />
            </div>
          )}
          {settled && server.human_out && !server.round_in_progress && (
            <p className="text-center font-semibold text-amber-100">
              {me.gone ? " " : `Te has quedado sin fichas para la apuesta mínima (${formatChips(server.rules.min_bet)}): la mesa sigue sin ti.`}
            </p>
          )}
          {!myTurn && !insurance && !canBet && !(betting && server.my_bet != null) && !server.human_out && (
            <div className="flex min-h-32 flex-col items-center justify-center gap-2 text-center text-amber-100/60">
              {settled && acting && !acting.isHuman && acting.person && timer ? (
                <TurnClock timer={timer} label={`Turno de ${acting.name}`} />
              ) : (
                <p>
                  {!settled
                    ? " "
                    : acting && !acting.isHuman
                      ? `Turno de ${acting.name}…`
                      : server.round_in_progress
                        ? "Juega el crupier…"
                        : " "}
                </p>
              )}
            </div>
          )}
        </section>
        <EventLog lines={logLines(frame, server.human_seat)} />
      </div>
    </>
  );
}
