import { useEffect, useRef, useState } from "react";
import { audio } from "../../shared/audio/engine";
import { EventLog } from "../../shared/components/EventLog";
import { TurnClock } from "../../shared/components/TurnClock";
import { HeaderContent } from "../../shared/Layout";
import type { RoomViewProps } from "../../shared/room";
import { usePlatformSettings } from "../../shared/SettingsContext";
import { usePlayback } from "../../shared/timeline/usePlayback";
import { ColorPicker } from "./components/ColorPicker";
import { Controls } from "./components/Controls";
import { Hand } from "./components/Hand";
import { PrismaTable } from "./components/PrismaTable";
import { logLines } from "./describe";
import { tableEffects } from "./effects";
import { PRISMA_TIMELINE } from "./timeline";
import type { Card, GameState } from "./types";

/**
 * La mesa de Prisma de una sala: varias personas, cada una con su mano. Cada
 * decisión tiene su cuenta atrás y, jugando a puntos, las rondas siguen solas.
 */
export default function PrismaRoom({ play }: RoomViewProps) {
  const { animations } = usePlatformSettings();
  const myself = useRef(0);
  const [effects] = useState(() => tableEffects(() => myself.current));
  const { frame, server, busy, push } = usePlayback(PRISMA_TIMELINE, animations, effects);
  const { subscribe, send, waiting } = play;

  useEffect(() => subscribe((state, instant) => push(state as GameState, instant)), [subscribe, push]);
  useEffect(() => {
    if (server) myself.current = server.human_seat;
  }, [server]);

  const [wild, setWild] = useState<Card | null>(null); // comodín elegido: falta decir el color
  const settled = !busy;
  const legal = server?.legal;
  const myTurn = settled && legal !== undefined && (legal.play.length > 0 || legal.draw || legal.pass);
  const mustChoose = settled && legal?.choose_color === true;
  const challenged = settled && legal?.challenge === true;
  useEffect(() => {
    if (myTurn || mustChoose || challenged) audio.play("turn");
  }, [myTurn, mustChoose, challenged]);

  if (!frame || !server) {
    return <p className="panel px-3 py-2 text-sm">Repartiendo las cartas…</p>;
  }

  const timer = server.timer ?? null;
  const current = server.players[server.turn];
  const mine = timer !== null && timer.seat === server.human_seat;

  function playCard(card: Card) {
    if (card.color === null) setWild(card);
    else send({ type: "play", card: card.id });
  }

  return (
    <>
      <HeaderContent
        info={
          <span className="text-sm text-amber-100/60">
            Ronda {server.round_number}
            {server.rules.scoring && ` · A ${server.rules.target} puntos`}
          </span>
        }
      />
      <PrismaTable
        frame={frame}
        me={server.human_seat}
        pendingDraw={server.pending_draw}
        canDraw={myTurn && server.legal.draw && !waiting}
        onDraw={() => send({ type: "draw" })}
        settled={settled}
      />
      <Hand
        cards={frame.hand}
        playable={myTurn ? server.legal.play : []}
        drawn={server.drawn}
        disabled={waiting || !myTurn}
        onPlay={playCard}
      />
      <div className="grid gap-3 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <section className="panel flex min-h-40 flex-col items-center justify-center gap-3 p-3 lg:order-2" aria-live="polite">
          {settled && timer && server.phase !== "round_over" && (
            <TurnClock timer={timer} label={mine ? "Te toca" : `Turno de ${current?.name ?? ""}`} />
          )}
          <div className="w-full">
            <Controls state={server} settled={settled} waiting={waiting} send={(type) => send({ type })} room />
          </div>
        </section>
        <EventLog lines={logLines(frame, server.human_seat)} />
      </div>

      {wild && (
        <ColorPicker
          title={`¿Qué color eliges con el ${wild.kind === "camaleon4" ? "Camaleón +4" : "Camaleón"}?`}
          onPick={(color) => {
            send({ type: "play", card: wild.id, color });
            setWild(null);
          }}
          onCancel={() => setWild(null)}
        />
      )}
      {mustChoose && !wild && (
        <ColorPicker
          title="La ronda empieza con un Camaleón: elige el color"
          onPick={(color) => send({ type: "color", color })}
        />
      )}
    </>
  );
}
