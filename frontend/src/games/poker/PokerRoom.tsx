import { useEffect, useState } from "react";
import { useAccount } from "../../shared/AccountContext";
import { audio } from "../../shared/audio/engine";
import { preloadFaces } from "../../shared/cards/CardFace";
import { TurnClock } from "../../shared/components/TurnClock";
import { HeaderContent } from "../../shared/Layout";
import type { RoomViewProps } from "../../shared/room";
import { usePlatformSettings } from "../../shared/SettingsContext";
import { Controls } from "./components/Controls";
import { HandLog } from "./components/HandLog";
import { ResultPanel } from "./components/ResultPanel";
import { Table } from "./components/Table";
import { tableEffects } from "./effects";
import { streetName } from "./format";
import type { GameState } from "./types";
import { usePlayback } from "./usePlayback";

/**
 * La mesa de poker de una sala: la misma de siempre, con varias personas. Las
 * manos se reparten solas y cada decisión tiene su cuenta atrás.
 */
export default function PokerRoom({ play }: RoomViewProps) {
  const { animations } = usePlatformSettings();
  const { setTableBalance } = useAccount();
  const { frame, server, busy, push } = usePlayback(animations, tableEffects);
  const { subscribe, send, waiting } = play;

  useEffect(() => subscribe((state, instant) => push(state as GameState, instant)), [subscribe, push]);
  useEffect(preloadFaces, []);

  // El saldo de la cabecera va al ritmo de la mesa: cambia cuando se ve cómo acabó la mano.
  const [balance, setBalance] = useState<number | null>(null);
  useEffect(() => {
    if (!busy && server) setBalance(server.balance);
  }, [busy, server]);
  useEffect(() => {
    if (balance !== null) setTableBalance(balance);
  }, [balance, setTableBalance]);
  useEffect(() => () => setTableBalance(undefined), [setTableBalance]);

  const settled = !busy;
  const myTurn = settled && server?.legal_actions != null;
  useEffect(() => {
    if (myTurn) audio.play("turn");
  }, [myTurn]);

  if (!frame || !server) {
    return <p className="panel px-3 py-2 text-sm">Repartiendo las cartas…</p>;
  }

  const handOver = settled && !server.hand_in_progress;
  const actor = frame.seats.find((seat) => seat.seat === frame.actingSeat);
  const timer = server.timer ?? null;

  return (
    <>
      <HeaderContent
        info={
          <span className="text-sm text-amber-100/60">
            Mano {frame.handNumber} · {streetName(frame.phase)} · Ciegas {frame.smallBlind}/{frame.bigBlind}
          </span>
        }
      />
      <Table frame={frame} settled={settled} />

      <div className="grid gap-3 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        {/* Zona de acción: altura fija para que la página no salte en cada turno. */}
        <section className="panel min-h-48 p-3 lg:order-2" aria-live="polite">
          {myTurn && (
            <div className="flex flex-col items-center gap-3">
              <TurnClock timer={timer} label="Te toca" />
              <div className="w-full">
                <Controls
                  state={server}
                  disabled={waiting}
                  onAction={(action, amount) => send({ type: "action", action, amount: amount ?? 0 })}
                />
              </div>
            </div>
          )}
          {handOver && <ResultPanel state={server} balance={server.balance} disabled room />}
          {!myTurn && !handOver && (
            <div className="flex h-full min-h-40 flex-col items-center justify-center gap-3 text-center text-amber-100/60">
              {settled && actor && timer ? (
                <TurnClock timer={timer} label={`Turno de ${actor.name}`} />
              ) : (
                <p>{settled && actor ? `Turno de ${actor.name}…` : " "}</p>
              )}
              {server.human_out && <p className="text-sm">Te has quedado sin fichas: la partida sigue sin ti.</p>}
            </div>
          )}
        </section>
        <HandLog frame={frame} />
      </div>
    </>
  );
}
