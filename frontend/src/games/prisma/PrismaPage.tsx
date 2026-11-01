import { useEffect, useRef, useState } from "react";
import { useAccount } from "../../shared/AccountContext";
import { audio } from "../../shared/audio/engine";
import { EventLog } from "../../shared/components/EventLog";
import { HeaderContent } from "../../shared/Layout";
import { usePlatformSettings } from "../../shared/SettingsContext";
import { usePlayback } from "../../shared/timeline/usePlayback";
import { useConnection } from "../../shared/useConnection";
import { useDocumentTitle } from "../../shared/useDocumentTitle";
import { useLeaveGuard } from "../../shared/useLeaveGuard";
import { Controls } from "./components/Controls";
import { Hand } from "./components/Hand";
import { PrismaTable } from "./components/PrismaTable";
import { StartScreen } from "./components/StartScreen";
import { MODE_NAMES, logLines } from "./describe";
import { tableEffects } from "./effects";
import { seatZone } from "./PrismaCard";
import { PRISMA_TIMELINE } from "./timeline";
import type { ClientMessage, GameState, Options } from "./types";
import { usePlayFlow } from "./usePlayFlow";

/** La mesa de Prisma, con su pantalla de inicio, mi mano y el panel de decisiones. */
export default function PrismaPage() {
  const { animations } = usePlatformSettings();
  const account = useAccount();
  useDocumentTitle("Prisma · mi-poker");

  const myself = useRef(0);
  const [effects] = useState(() => tableEffects(() => myself.current));
  const { frame, server, busy, push } = usePlayback(PRISMA_TIMELINE, animations, effects);
  const { connected, options, user, error, waiting, send } = useConnection<GameState, Options, ClientMessage>(
    "prisma",
    push,
  );
  useEffect(() => {
    if (server) myself.current = server.human_seat;
  }, [server]);

  const [configuring, setConfiguring] = useState(false);
  useEffect(() => setConfiguring(false), [account.identity]);
  const showStart = options !== null && (server === null || configuring);
  const settled = !busy;
  const legal = server?.legal;
  const myTurn = settled && legal !== undefined && (legal.play.length > 0 || legal.draw || legal.pass);
  const mustDecide = settled && (legal?.choose_color === true || legal?.challenge === true || legal?.roulette === true);
  const leaveGuard = useLeaveGuard(server !== null && !server.game_over);
  const { play, dialogs } = usePlayFlow(showStart ? null : server, settled, send);

  useEffect(() => {
    if (myTurn || mustDecide) audio.play("turn");
  }, [myTurn, mustDecide]);

  return (
    <>
      <HeaderContent
        info={
          server &&
          !showStart && (
            <span className="text-sm text-amber-100/60">
              {server.mode !== "clasico" && `${MODE_NAMES[server.mode]} · `}Ronda {server.round_number}
              {server.rules.scoring && ` · A ${server.rules.target} puntos`}
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
          onStart={(config) => {
            send({ type: "new_game", config });
            setConfiguring(false);
          }}
          onCancel={server ? () => setConfiguring(false) : undefined}
        />
      )}

      {frame && server && !showStart && (
        <>
          <PrismaTable
            frame={frame}
            me={server.human_seat}
            canDraw={myTurn && server.legal.draw && !waiting}
            onDraw={() => send({ type: "draw" })}
            settled={settled}
          />
          <Hand
            cards={frame.hand}
            playable={myTurn ? server.legal.play : []}
            drawn={server.drawn}
            disabled={waiting || !myTurn}
            onPlay={play}
            night={frame.side === "sombra"}
            from={frame.handFrom !== null ? seatZone(frame.handFrom) : undefined}
          />
          <div className="grid gap-3 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
            <section className="panel flex min-h-40 flex-col justify-center gap-3 p-3 lg:order-2" aria-live="polite">
              <Controls
                state={server}
                settled={settled}
                waiting={waiting}
                send={(type) => send({ type })}
                onConfigure={() => setConfiguring(true)}
              />
            </section>
            <EventLog lines={logLines(frame, server.human_seat)} />
          </div>
        </>
      )}

      {dialogs}

      {leaveGuard}
    </>
  );
}
