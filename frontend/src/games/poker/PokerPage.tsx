import { useEffect, useState } from "react";
import { useAccount } from "../../shared/AccountContext";
import { audio } from "../../shared/audio/engine";
import { preloadFaces } from "../../shared/cards/CardFace";
import { HeaderContent } from "../../shared/Layout";
import { usePlatformSettings } from "../../shared/SettingsContext";
import { useWhenDue } from "../../shared/useClock";
import { useConnection } from "../../shared/useConnection";
import { useDocumentTitle } from "../../shared/useDocumentTitle";
import { useLeaveGuard } from "../../shared/useLeaveGuard";
import { tableSounds } from "./audio/tableSounds";
import { Controls } from "./components/Controls";
import { HandLog } from "./components/HandLog";
import { ResultPanel } from "./components/ResultPanel";
import { StartScreen } from "./components/StartScreen";
import { Table } from "./components/Table";
import { tableMotion } from "./director";
import { streetName } from "./format";
import type { PlaybackListener } from "./timeline/playback";
import type { ClientMessage, GameState, Options } from "./types";
import { usePlayback } from "./usePlayback";

// Lo que acompaña a cada paso de la mano: primero el movimiento y después su sonido.
const tableEffects: PlaybackListener = {
  onStep(step, speed) {
    tableMotion.onStep?.(step, speed);
    tableSounds.onStep?.(step, speed);
  },
  onJump: tableMotion.onJump,
  onSkip: tableSounds.onSkip,
};

/** La mesa de poker, con su pantalla de inicio y su panel de acciones. */
export default function PokerPage() {
  const { animations } = usePlatformSettings();
  const account = useAccount();
  useDocumentTitle("Poker Hold'em · mi-poker");

  // `frame` es lo que se dibuja; `server`, lo último que dijo el servidor. Mientras
  // `busy`, la mesa todavía está reproduciendo pasos y no se puede actuar.
  const { frame, server, busy, push } = usePlayback(animations, tableEffects);
  // El servidor me identifica por la cuenta y me da mi partida de poker.
  const { connected, options, user, elsewhere, error, waiting, send, reconnect } = useConnection<
    GameState,
    Options,
    ClientMessage
  >("poker", push);
  const [configuring, setConfiguring] = useState(false);
  useEffect(() => setConfiguring(false), [account.identity]);

  // El saldo se enseña al ritmo de la mesa: el servidor ya sabe cómo acabó la
  // mano, pero en pantalla no cambia hasta que se ha visto el final.
  const latestBalance = user ? (server?.balance ?? user.balance) : null;
  const [balance, setBalance] = useState<number | null>(null);
  useEffect(() => {
    if (!busy) setBalance(latestBalance);
  }, [busy, latestBalance]);
  const { setTableBalance } = account;
  useEffect(() => {
    if (user) setTableBalance(balance);
  }, [user, balance, setTableBalance]);
  // Al salir de la mesa, la cabecera vuelve a enseñar el saldo de la cuenta.
  useEffect(() => () => setTableBalance(undefined), [setTableBalance]);

  const showStart = options !== null && (server === null || configuring);
  // En la pantalla de inicio, al llegar las fichas diarias se vuelve a conectar:
  // el servidor las entrega al mirar el saldo y la pantalla enseña el nuevo.
  useWhenDue(showStart ? user?.next_chips_at : null, reconnect);

  const settled = !busy;
  const myTurn = settled && server?.legal_actions != null;
  const handOver = settled && server !== null && !server.hand_in_progress;
  const actor = frame?.seats.find((seat) => seat.seat === frame.actingSeat);
  // Lo que llevo apostado en la mano en curso: se pierde si la dejo a medias.
  const atStake =
    server?.hand_in_progress === true
      ? (server.seats.find((seat) => seat.seat === server.viewer_seat)?.contributed ?? 0)
      : 0;
  // Salir al menú con una partida viva pide confirmación (la partida queda en pausa).
  const leaveGuard = useLeaveGuard(server !== null && !server.game_over && !server.human_out);

  // Las caras de la baraja se descargan al entrar, para que ninguna tarde al repartirla.
  useEffect(preloadFaces, []);

  // Aviso suave cada vez que me toca jugar.
  useEffect(() => {
    if (myTurn) audio.play("turn");
  }, [myTurn]);

  return (
    <>
      <HeaderContent
        info={
          frame &&
          !showStart && (
            <span className="text-sm text-amber-100/60">
              Mano {frame.handNumber} · {streetName(frame.phase)} · Ciegas {frame.smallBlind}/
              {frame.bigBlind}
            </span>
          )
        }
        actions={
          server &&
          !showStart && (
            <button
              className="btn-gold h-9 whitespace-nowrap px-4 text-sm"
              onClick={() => setConfiguring(true)}
            >
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
          // Otra identidad, otra configuración: la pantalla empieza de cero.
          key={user?.username ?? ""}
          options={options}
          accountName={user?.username}
          balance={user ? latestBalance : null}
          atStake={atStake}
          elsewhere={elsewhere}
          nextChipsAt={user?.next_chips_at ?? null}
          initial={server?.config ?? options.defaults}
          onStart={(config) => {
            send({ type: "new_game", config });
            setConfiguring(false);
          }}
          onCancel={server ? () => setConfiguring(false) : undefined}
        />
      )}

      {frame && server && !showStart && (
        <>
          <Table frame={frame} settled={settled} />

          <div className="grid gap-3 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
            {/* Zona de acción: altura fija para que la página no salte en cada turno. */}
            <section className="panel min-h-48 p-3 lg:order-2" aria-live="polite">
              {myTurn && (
                <Controls
                  state={server}
                  disabled={waiting}
                  onAction={(action, amount) =>
                    send({ type: "action", action, amount: amount ?? 0 })
                  }
                />
              )}
              {handOver && (
                <ResultPanel
                  state={server}
                  balance={user ? latestBalance : null}
                  disabled={waiting}
                  onNextHand={() => send({ type: "next_hand" })}
                  onRestart={() => send({ type: "restart" })}
                  onConfigure={() => setConfiguring(true)}
                />
              )}
              {!myTurn && !handOver && (
                <p className="flex h-full min-h-40 items-center justify-center text-amber-100/60">
                  {settled && actor ? `Turno de ${actor.name}…` : " "}
                </p>
              )}
            </section>
            <HandLog frame={frame} />
          </div>
        </>
      )}

      {leaveGuard}
    </>
  );
}
