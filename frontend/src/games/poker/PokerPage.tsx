import { useEffect, useLayoutEffect, useState } from "react";
import { logout, refill } from "../../shared/account";
import { audio } from "../../shared/audio/engine";
import { useAudio } from "../../shared/audio/useAudio";
import { tableSounds } from "./audio/tableSounds";
import { AccountDialog } from "../../shared/components/AccountDialog";
import { AccountMenu } from "../../shared/components/AccountMenu";
import { ProfileDialog } from "../../shared/components/ProfileDialog";
import { Controls } from "./components/Controls";
import { preloadFaces } from "../../shared/cards/CardFace";
import { Wordmark } from "../../shared/components/Emblem";
import { HandLog } from "./components/HandLog";
import { ResultPanel } from "./components/ResultPanel";
import { SettingsMenu } from "../../shared/components/SettingsMenu";
import { StartScreen } from "./components/StartScreen";
import { Table } from "./components/Table";
import { streetName } from "./format";
import { tableMotion } from "./director";
import { motion } from "../../shared/motion";
import type { PlaybackListener } from "./timeline/playback";
import { useConnection } from "../../shared/useConnection";
import { usePlayback } from "./usePlayback";
import { usePrefersReducedMotion, useSettings } from "../../shared/useSettings";
import type { ClientMessage, GameState, Options } from "./types";

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
  const [settings, updateSettings] = useSettings();
  const reducedMotion = usePrefersReducedMotion();
  const animations = settings.animations ?? !reducedMotion;
  useAudio(settings);

  // Las piezas de la mesa y las hojas de estilo miran aquí si deben moverse.
  useLayoutEffect(() => {
    motion.enabled = animations;
    document.documentElement.dataset.motion = animations ? "on" : "off";
  }, [animations]);

  // `frame` es lo que se dibuja; `server`, lo último que dijo el servidor. Mientras
  // `busy`, la mesa todavía está reproduciendo pasos y no se puede actuar.
  const { frame, server, busy, push } = usePlayback(animations, tableEffects);
  const { connected, options, user, error, waiting, send, reconnect } = useConnection<
    GameState,
    Options,
    ClientMessage
  >("poker", push);
  const [configuring, setConfiguring] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  // El saldo se enseña al ritmo de la mesa: el servidor ya sabe cómo acabó la
  // mano, pero en pantalla no cambia hasta que se ha visto el final.
  const latestBalance = user ? (server?.balance ?? user.balance) : null;
  const [balance, setBalance] = useState<number | null>(null);
  useEffect(() => {
    if (!busy) setBalance(latestBalance);
  }, [busy, latestBalance]);

  // Recarga gratis. El saldo nuevo llega al volver a conectar.
  async function askRefill(): Promise<string | null> {
    const result = await refill();
    if (!result.ok) return result.message;
    reconnect();
    return null;
  }

  // Al entrar o salir de la cuenta se vuelve a conectar: el servidor me
  // identifica en ese momento y me da la partida de esa identidad.
  function signedIn() {
    setAccountOpen(false);
    setConfiguring(false);
    reconnect();
  }
  async function signOut() {
    setProfileOpen(false);
    setSigningOut(true);
    await logout();
    setSigningOut(false);
    setConfiguring(false);
    reconnect();
  }
  const showStart = options !== null && (server === null || configuring);

  const settled = !busy;
  const myTurn = settled && server?.legal_actions != null;
  const handOver = settled && server !== null && !server.hand_in_progress;
  const actor = frame?.seats.find((seat) => seat.seat === frame.actingSeat);
  // Lo que llevo apostado en la mano en curso: se pierde si la dejo a medias.
  const atStake =
    server?.hand_in_progress === true
      ? (server.seats.find((seat) => seat.seat === server.viewer_seat)?.contributed ?? 0)
      : 0;

  // Las caras de la baraja se descargan al entrar, para que ninguna tarde al repartirla.
  useEffect(preloadFaces, []);

  // Aviso suave cada vez que me toca jugar.
  useEffect(() => {
    if (myTurn) audio.play("turn");
  }, [myTurn]);

  return (
    <div className="mx-auto flex max-w-[1180px] flex-col gap-3 p-3">
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex items-baseline gap-3">
          <Wordmark className="text-2xl" />
          {frame && !showStart && (
            <span className="text-sm text-amber-100/60">
              Mano {frame.handNumber} · {streetName(frame.phase)} · Ciegas {frame.smallBlind}/
              {frame.bigBlind}
            </span>
          )}
        </div>
        {/* En pantallas estrechas los botones bajan a otra fila en vez de salirse. */}
        <div className="flex flex-wrap items-center gap-2">
          {server && !showStart && (
            <button
              className="btn-gold h-9 whitespace-nowrap px-4 text-sm"
              onClick={() => setConfiguring(true)}
            >
              Nueva partida
            </button>
          )}
          <AccountMenu
            user={user}
            balance={balance}
            disabled={signingOut}
            onSignIn={() => setAccountOpen(true)}
            onSignOut={signOut}
            onProfile={() => setProfileOpen(true)}
          />
          <SettingsMenu
            settings={settings}
            animations={animations}
            reducedMotion={reducedMotion}
            onChange={updateSettings}
          />
        </div>
      </header>

      {!connected && (
        <p className="panel px-3 py-2 text-sm">Conectando con el servidor…</p>
      )}
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
          onRefill={askRefill}
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
                  {settled && actor ? `Turno de ${actor.name}…` : " "}
                </p>
              )}
            </section>
            <HandLog frame={frame} />
          </div>
        </>
      )}

      {accountOpen && <AccountDialog onClose={() => setAccountOpen(false)} onSignedIn={signedIn} />}
      {profileOpen && user && (
        <ProfileDialog
          user={user}
          balance={balance}
          onClose={() => setProfileOpen(false)}
          onSignOut={signOut}
        />
      )}
    </div>
  );
}
