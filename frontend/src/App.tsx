import { useEffect, useLayoutEffect, useState } from "react";
import { audio } from "./audio/engine";
import { tableSounds, useAudio } from "./audio/useAudio";
import { Controls } from "./components/Controls";
import { preloadFaces } from "./components/cards/CardFace";
import { Wordmark } from "./components/Emblem";
import { HandLog } from "./components/HandLog";
import { ResultPanel } from "./components/ResultPanel";
import { SettingsMenu } from "./components/SettingsMenu";
import { StartScreen } from "./components/StartScreen";
import { Table } from "./components/Table";
import { streetName } from "./format";
import { tableMotion } from "./motion/director";
import { motion } from "./motion/motion";
import type { PlaybackListener } from "./timeline/playback";
import { useGame } from "./useGame";
import { usePlayback } from "./usePlayback";
import { usePrefersReducedMotion, useSettings } from "./useSettings";

const NOTICE = "Solo para entretenimiento. Sin dinero real.";

// Lo que acompaña a cada paso de la mano: primero el movimiento y después su sonido.
const tableEffects: PlaybackListener = {
  onStep(step, speed) {
    tableMotion.onStep?.(step, speed);
    tableSounds.onStep?.(step, speed);
  },
  onJump: tableMotion.onJump,
  onSkip: tableSounds.onSkip,
};

export default function App() {
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
  const { connected, options, error, waiting, send } = useGame(push);
  const [configuring, setConfiguring] = useState(false);
  const showStart = options !== null && (server === null || configuring);

  const settled = !busy;
  const myTurn = settled && server?.legal_actions != null;
  const handOver = settled && server !== null && !server.hand_in_progress;
  const actor = frame?.seats.find((seat) => seat.seat === frame.actingSeat);

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
        <div className="flex items-center gap-2">
          <p className="rounded-lg border border-amber-400/60 px-3 py-1.5 text-sm font-semibold text-amber-300">
            {NOTICE}
          </p>
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
          options={options}
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

          <footer className="flex items-center justify-between text-xs text-stone-400">
            <span>Las fichas son virtuales y no tienen valor fuera del juego.</span>
            <button className="underline" onClick={() => setConfiguring(true)}>
              Nueva partida
            </button>
          </footer>
        </>
      )}
    </div>
  );
}
