import { useEffect, useRef, useState } from "react";
import { useAccount } from "../../shared/AccountContext";
import { audio } from "../../shared/audio/engine";
import { preloadFaces } from "../../shared/cards/CardFace";
import { formatChips } from "../../shared/format";
import { HeaderContent } from "../../shared/Layout";
import { usePlatformSettings } from "../../shared/SettingsContext";
import { usePlayback } from "../../shared/timeline/usePlayback";
import { useWhenDue } from "../../shared/useClock";
import { useConnection } from "../../shared/useConnection";
import { useDocumentTitle } from "../../shared/useDocumentTitle";
import { useLeaveGuard } from "../../shared/useLeaveGuard";
import { BlackjackTable } from "./components/BlackjackTable";
import { ActionControls, BetControls, InsurancePrompt, RoundSummary } from "./components/Controls";
import { EventLog } from "../../shared/components/EventLog";
import { describeEvent } from "./describe";
import type { Frame } from "./timeline";
import { StartScreen } from "./components/StartScreen";
import { tableEffects } from "./effects";
import { BLACKJACK_TIMELINE } from "./timeline";
import type { ClientMessage, GameState, Options } from "./types";

/** Las líneas del registro de la ronda que se ve ahora en la mesa. */
function logLines(frame: Frame, me: number) {
  return frame.events.flatMap((event, index) => {
    const text = describeEvent(index, frame, me);
    if (text === null) return [];
    const tone = event.kind === "settle" ? "highlight" : event.seat === me ? "mine" : "others";
    return [{ text, tone } as const];
  });
}

/** La mesa de blackjack, con su pantalla de inicio y su panel de jugadas. */
export default function BlackjackPage() {
  const { animations } = usePlatformSettings();
  const account = useAccount();
  useDocumentTitle("Blackjack · mi-poker");

  // Mi asiento, para los sonidos (el de ganar solo suena con lo mío).
  const myself = useRef(0);
  const [effects] = useState(() => tableEffects(() => myself.current));
  const { frame, server, busy, push } = usePlayback(BLACKJACK_TIMELINE, animations, effects);
  const { connected, options, user, elsewhere, error, waiting, send, reconnect } = useConnection<
    GameState,
    Options,
    ClientMessage
  >("blackjack", push);
  useEffect(() => {
    if (server) myself.current = server.human_seat;
  }, [server]);

  const [configuring, setConfiguring] = useState(false);
  useEffect(() => setConfiguring(false), [account.identity]);
  // La última apuesta: la siguiente ronda empieza con ella.
  const [lastBet, setLastBet] = useState(0);

  // El saldo se enseña al ritmo de la mesa: no cambia hasta que se ve cómo acabó la ronda.
  const latestBalance = user ? (server?.balance ?? user.balance) : null;
  const [balance, setBalance] = useState<number | null>(null);
  useEffect(() => {
    if (!busy) setBalance(latestBalance);
  }, [busy, latestBalance]);
  const { setTableBalance } = account;
  useEffect(() => {
    if (user) setTableBalance(balance);
  }, [user, balance, setTableBalance]);
  useEffect(() => () => setTableBalance(undefined), [setTableBalance]);

  const showStart = options !== null && (server === null || configuring);
  // En la pantalla de inicio, al llegar las fichas diarias se vuelve a conectar
  // para enseñar el saldo nuevo.
  useWhenDue(showStart ? user?.next_chips_at : null, reconnect);
  const settled = !busy;
  const me = server?.seats[server.human_seat];
  const myTurn = settled && server?.legal_actions != null && server.legal_actions.length > 0;
  const insurance = settled && server?.insurance_offered === true;
  const canBet = settled && server !== null && !server.round_in_progress && !server.human_out;
  const atStake = server?.round_in_progress
    ? (me?.hands.reduce((sum, hand) => sum + (hand.result === null ? hand.bet : 0), 0) ?? 0) + (me?.insurance ?? 0)
    : 0;
  const acting = frame?.acting ? frame.seats[frame.acting.seat] : null;
  const leaveGuard = useLeaveGuard(server !== null && !server.human_out);

  useEffect(preloadFaces, []);
  useEffect(() => {
    if (myTurn || insurance) audio.play("turn");
  }, [myTurn, insurance]);

  function bet(amount: number) {
    setLastBet(amount);
    send({ type: "bet", amount });
  }

  return (
    <>
      <HeaderContent
        info={
          server &&
          !showStart && (
            <span className="text-sm text-amber-100/60">
              Ronda {server.round_number} · Apuestas {server.rules.min_bet}–{server.rules.max_bet}
            </span>
          )
        }
        actions={
          server &&
          !showStart && (
            <button className="btn-gold h-9 whitespace-nowrap px-4 text-sm" onClick={() => setConfiguring(true)}>
              Nueva partida
            </button>
          )
        }
      />

      {!connected && <p className="panel px-3 py-2 text-sm">Conectando con el servidor…</p>}
      {error && (
        <p role="alert" className="rounded-lg bg-rose-800 px-3 py-2 text-sm">
          {error}
        </p>
      )}

      {showStart && (
        <StartScreen
          key={user?.username ?? ""}
          options={options}
          initial={server?.config ?? options.defaults}
          accountName={user?.username}
          balance={user ? latestBalance : null}
          atStake={atStake}
          elsewhere={elsewhere}
          nextChipsAt={user?.next_chips_at ?? null}
          onStart={(config) => {
            send({ type: "new_game", config });
            setConfiguring(false);
            setLastBet(config.min_bet);
          }}
          onCancel={server ? () => setConfiguring(false) : undefined}
        />
      )}

      {frame && server && !showStart && (
        <>
          <BlackjackTable
            frame={frame}
            rules={server.rules}
            shoe={{ remaining: server.shoe.remaining, total: server.shoe.total, cutReached: server.shoe.cut_reached }}
            settled={settled}
          />

          <div className="grid gap-3 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
            <section className="panel flex min-h-48 flex-col justify-center gap-3 p-3 lg:order-2" aria-live="polite">
              {server.phase === "complete" && settled && <RoundSummary state={server} />}
              {insurance && (
                <InsurancePrompt
                  cost={(me?.hands[0]?.bet ?? 0) / 2}
                  disabled={waiting}
                  onDecide={(take) => send({ type: "insurance", take })}
                />
              )}
              {myTurn && (
                <ActionControls
                  legal={server.legal_actions!}
                  disabled={waiting}
                  onAction={(action) => send({ type: "action", action })}
                />
              )}
              {canBet && (
                <BetControls
                  key={server.round_number}
                  state={server}
                  lastBet={lastBet || server.rules.min_bet}
                  disabled={waiting}
                  onBet={bet}
                />
              )}
              {settled && server.human_out && (
                <div className="flex flex-col gap-3 text-center">
                  <p className="font-semibold text-amber-100">
                    Te has quedado sin fichas para la apuesta mínima ({formatChips(server.rules.min_bet)}).
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    <button className="btn-green h-12 px-5" disabled={waiting} onClick={() => send({ type: "restart" })}>
                      Reiniciar partida
                    </button>
                    <button className="btn-dark h-12 px-5" onClick={() => setConfiguring(true)}>
                      Cambiar configuración
                    </button>
                  </div>
                </div>
              )}
              {!myTurn && !insurance && !canBet && !server.human_out && (
                <p className="flex min-h-40 items-center justify-center text-amber-100/60">
                  {!settled
                    ? " "
                    : acting && !acting.isHuman
                      ? `Turno de ${acting.name}…`
                      : server.round_in_progress
                        ? "Juega el crupier…"
                        : " "}
                </p>
              )}
            </section>
            <EventLog lines={logLines(frame, server.human_seat)} />
          </div>
        </>
      )}

      {leaveGuard}
    </>
  );
}
