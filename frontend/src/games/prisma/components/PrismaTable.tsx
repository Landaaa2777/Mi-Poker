import type { CSSProperties } from "react";
import { Avatar } from "../../../shared/components/Avatar";
import { usePlatformSettings } from "../../../shared/SettingsContext";
import type { Camera } from "../../../shared/stage/camera";
import { Stage, stageHeight, usePlacement } from "../../../shared/stage/Stage";
import { useFit } from "../../../shared/useFit";
import { DECK_ZONE, HAND_ZONE, PrismaCard, seatZone } from "../PrismaCard";
import { SUITS, SuitSymbol } from "../shapes";
import type { Frame, PlayerFrame } from "../timeline";

// La mesa se dibuja en un lienzo de tamaño fijo que se escala entero, como las
// demás. En el centro, el mazo y el descarte; alrededor, los rivales en el
// orden en que juegan; abajo, yo (mis cartas van debajo de la mesa, en grande).

interface Point {
  x: number;
  y: number;
}

interface Layout {
  width: number;
  height: number;
  center: Point;
  card: number; // ancho de las cartas del centro
  rivals: (count: number) => Point[]; // centro de la placa de cada rival
  me: Point;
}

/** Los rivales en arco por arriba, de izquierda a derecha en el orden en que juegan. */
function arc(center: Point, radius: Point) {
  return (count: number): Point[] =>
    Array.from({ length: count }, (_, index) => {
      const share = count === 1 ? 0.5 : index / (count - 1);
      const spread = Math.min(150, 40 * count);
      const angle = ((270 - spread / 2 + spread * share) * Math.PI) / 180;
      return { x: center.x + radius.x * Math.cos(angle), y: center.y + radius.y * Math.sin(angle) };
    });
}

const LANDSCAPE: Layout = {
  width: 1120,
  height: 520,
  center: { x: 560, y: 268 },
  card: 92,
  rivals: arc({ x: 560, y: 300 }, { x: 440, y: 230 }),
  me: { x: 560, y: 468 },
};

const PORTRAIT: Layout = {
  width: 500,
  height: 700,
  center: { x: 250, y: 380 },
  card: 76,
  rivals: arc({ x: 250, y: 330 }, { x: 205, y: 250 }),
  me: { x: 250, y: 640 },
};

const CENTERED = "absolute -translate-x-1/2 -translate-y-1/2";
const BOTTOM_CENTERED = "absolute -translate-x-1/2 -translate-y-full"; // colgado de su borde de abajo
const TOP_CENTERED = "absolute -translate-x-1/2"; // colgado de su borde de arriba
const cardWidth = (width: number) => ({ "--card-w": `${width}px` }) as CSSProperties;
const MAX_BACKS = 7; // dorsos dibujados por rival; si tiene más, se ve el número
const FIT = { maxHeightShare: 0.56 };

// Cámara de la vista 3D: los rivales al fondo y el mazo y el descarte en medio.
const CAMERA: Camera = { tilt: 40, distance: 1400, eye: 0.55, top: 16, bottom: 36 };
const CAMERA_PORTRAIT: Camera = { tilt: 32, distance: 1500, eye: 0.55, top: 14, bottom: 30 };
const cameraFor = (layout: { width: number }) => (layout.width === PORTRAIT.width ? CAMERA_PORTRAIT : CAMERA);
const FIT_3D = { ...FIT, heightOf: stageHeight(cameraFor) };

interface SeatProps {
  player: PlayerFrame;
  turn: boolean;
  thinking: boolean;
  compact: boolean;
  withBacks?: boolean; // en 2D, los dorsos van con la placa; en 3D, tumbados en el tapete
}

/** Los dorsos de las cartas de un rival, solapados. */
function Backs({ player, compact }: { player: PlayerFrame; compact: boolean }) {
  const backs = Math.min(player.count, MAX_BACKS);
  return (
    <div className="keep-3d flex" style={{ ...cardWidth(compact ? 22 : 28), minHeight: (compact ? 22 : 28) * 1.4 }}>
      {Array.from({ length: backs }, (_, index) => (
        <span key={index} className="keep-3d" style={{ marginLeft: index === 0 ? 0 : (compact ? -15 : -19) }}>
          <PrismaCard card={null} enter="deal" />
        </span>
      ))}
    </div>
  );
}

/** Un rival (o yo): placa con avatar, nombre y cuántas cartas tiene, y sus avisos. */
function Seat({ player, turn, thinking, compact, withBacks = true }: SeatProps) {
  const ring = player.vulnerable ? "ring-rose-400" : turn ? "ring-amber-300" : "ring-white/25";
  return (
    <div className="flex flex-col items-center gap-1.5" data-prisma-seat={player.seat}>
      {!player.isHuman && withBacks && <Backs player={player} compact={compact} />}
      <div
        className={`relative flex items-center gap-2 rounded-full bg-[#0c0709]/90 p-1 pr-3 shadow-lg shadow-black/50 ring-1 ring-amber-400/35 ${player.vulnerable ? "vulnerable-pulse" : ""}`}
      >
        <Avatar name={player.name} size={compact ? 32 : 40} ring={ring} />
        <div className="leading-tight">
          <div className="max-w-[7.5rem] truncate text-sm font-semibold">{player.name}</div>
          <div className="text-xs font-bold tabular-nums text-amber-300">
            {player.count} {player.count === 1 ? "carta" : "cartas"}
          </div>
        </div>
        {player.saidLast && player.count === 1 && (
          <span className="pop-in absolute -right-2 -top-3 rounded-full bg-gradient-to-b from-amber-200 to-amber-500 px-2 py-0.5 text-[11px] font-black text-stone-900 shadow">
            ¡Última!
          </span>
        )}
        {player.vulnerable && (
          <span
            className="pop-in absolute -right-2 -top-3 rounded-full bg-rose-600 px-2 py-0.5 text-[11px] font-black text-white shadow"
            title="Tiene una carta y no ha dicho «¡Última!»"
          >
            ¡Sin avisar!
          </span>
        )}
      </div>
      <div
        key={player.action ?? (thinking ? "pensando" : player.level)}
        className={`h-4 text-center text-[11px] ${player.action || thinking ? "pop-in font-semibold text-amber-200" : "text-emerald-50/55"}`}
      >
        {player.action ?? (thinking ? "Pensando…" : player.isHuman || player.person ? "" : player.level)}
      </div>
    </div>
  );
}

/** Flechas en círculo: el sentido en que va el juego. */
function DirectionRing({ direction, size }: { direction: 1 | -1; size: number }) {
  return (
    <svg
      key={direction}
      viewBox="0 0 200 120"
      className="pop-in pointer-events-none text-amber-100/25"
      style={{ width: size, height: size * 0.6, transform: direction === 1 ? undefined : "scaleX(-1)" }}
      aria-hidden
    >
      <path d="M24 60 A76 46 0 0 1 176 60" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
      <path d="M176 60 A76 46 0 0 1 24 60" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeDasharray="10 12" />
      <path d="M168 44 L178 62 L160 62 Z" fill="currentColor" />
      <path d="M32 76 L22 58 L40 58 Z" fill="currentColor" />
    </svg>
  );
}

interface Props {
  frame: Frame;
  me: number;
  pendingDraw: number;
  canDraw: boolean; // puedo robar ahora: el mazo se puede pulsar
  onDraw: () => void;
  settled: boolean;
}

/** La mesa de Prisma. */
export function PrismaTable({ frame, me, pendingDraw, canDraw, onDraw, settled }: Props) {
  const { view } = usePlatformSettings();
  const { ref, layout, scale, height } = useFit(LANDSCAPE, PORTRAIT, view === "3d" ? FIT_3D : FIT);
  const place = usePlacement(view, layout, cameraFor(layout));
  const flat = place.view === "2d";
  const compact = layout === PORTRAIT;
  const rivals = frame.players.filter((player) => player.seat !== me);
  // Los rivales, en el orden en que juegan empezando por el siguiente a mí.
  rivals.sort((a, b) => ((a.seat - me + 100) % 100) - ((b.seat - me + 100) % 100));
  const points = layout.rivals(rivals.length);
  const mine = frame.players[me];
  const origin = frame.lastPlayer === null ? DECK_ZONE : frame.lastPlayer === me ? HAND_ZONE : seatZone(frame.lastPlayer);
  const suit = frame.color ? SUITS[frame.color] : null;
  const deck = { x: layout.center.x - layout.card * 0.95, y: layout.center.y };
  const discard = { x: layout.center.x + layout.card * 0.6, y: layout.center.y };
  const backHeight = (compact ? 22 : 28) * 1.4;

  const ring = (
    <div className={CENTERED} style={place.onTable(layout.center)}>
      <DirectionRing direction={frame.direction} size={layout.card * 5.2} />
    </div>
  );

  // El mazo: se pulsa para robar.
  const deckButton = (
    <button
      type="button"
      disabled={!canDraw}
      onClick={onDraw}
      className={`deck-stack keep-3d relative rounded-lg ${canDraw ? "deck-ready cursor-pointer" : "cursor-default"}`}
      style={cardWidth(layout.card * 0.86)}
      aria-label={canDraw ? `Robar una carta (quedan ${frame.drawCount})` : `Mazo: ${frame.drawCount} cartas`}
    >
      <span className="card absolute -left-1.5 -top-1.5 block"><PrismaCard card={null} /></span>
      <span className="card absolute -left-0.5 -top-0.5 block"><PrismaCard card={null} /></span>
      <span data-zone="prisma-deck" className="card keep-3d relative block"><PrismaCard card={null} /></span>
    </button>
  );
  const deckLabel = (
    <span className="text-[11px] font-semibold tabular-nums text-amber-100/75">
      {canDraw ? "Pulsa para robar" : `Mazo · ${frame.drawCount}`}
    </span>
  );

  // El descarte, con el color que hay que seguir alrededor.
  const discardPile = (
    <div
      className="keep-3d relative rounded-2xl p-1.5"
      style={{ boxShadow: suit ? `0 0 0 4px ${suit.color}, 0 0 28px 4px ${suit.color}` : undefined }}
    >
      <div className="keep-3d" style={cardWidth(layout.card)}>
        {frame.top && <PrismaCard key={frame.top.id} card={frame.top} enter="play" from={origin} />}
      </div>
    </div>
  );
  const colorLabel = suit && (
    <span key={frame.color} className="pop-in flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-0.5 text-xs font-bold">
      <SuitSymbol suit={frame.color!} className="h-3.5 w-3.5" />
      <span style={{ color: suit.color }}>{suit.name}</span>
    </span>
  );

  const notices = (
    <>
      {pendingDraw > 0 && (
        <div className={`${CENTERED} pop-in rounded-full bg-rose-700 px-3 py-1 text-sm font-black text-white shadow`} style={place.overTable({ x: layout.center.x, y: layout.center.y + layout.card * 0.95 })}>
          +{pendingDraw} acumuladas
        </div>
      )}

      {frame.note && (
        <div
          key={frame.note}
          className={`${CENTERED} pop-in rounded-full bg-black/65 px-4 py-1 text-sm font-semibold text-amber-100 shadow`}
          style={place.overTable({ x: layout.center.x, y: layout.center.y - layout.card * 1.05 })}
        >
          {frame.note}
        </div>
      )}
    </>
  );

  const glows = rivals.map((player, index) =>
    frame.turn === player.seat ? (
      <div
        key={player.seat}
        className={`${CENTERED} glow-turn h-[220px] w-[220px] rounded-full bg-[radial-gradient(closest-side,rgb(254_249_195/0.2),transparent)]`}
        style={place.onTable(points[index])}
      />
    ) : null,
  );

  if (flat) {
    return (
      <Stage
        sectionRef={ref}
        placement={place}
        layout={layout}
        scale={scale}
        height={height}
        label="Mesa de Prisma"
        shape="rounded-[1.75rem]"
        shade="bg-[radial-gradient(ellipse_at_center,transparent_50%,rgb(0_0_0/0.4))]"
        table={
          <>
            {ring}
            <div className={`${CENTERED} flex flex-col items-center gap-1`} style={place.onTable(deck)}>
              {deckButton}
              {deckLabel}
            </div>
            <div className={`${CENTERED} flex flex-col items-center gap-1.5`} style={place.onTable(discard)}>
              {discardPile}
              {colorLabel}
            </div>
            {notices}
            {rivals.map((player, index) => (
              <div key={player.seat} className={CENTERED} style={place.onTable(points[index])}>
                {glows[index] && (
                  <div className={`${CENTERED} glow-turn left-1/2 top-1/2 h-[220px] w-[220px] rounded-full bg-[radial-gradient(closest-side,rgb(254_249_195/0.2),transparent)]`} />
                )}
                <div className="relative">
                  <Seat player={player} turn={frame.turn === player.seat} thinking={settled && frame.turn === player.seat} compact={compact} />
                </div>
              </div>
            ))}
            <div className={CENTERED} style={place.onTable(layout.me)}>
              <Seat player={mine} turn={frame.turn === me} thinking={false} compact={compact} />
            </div>
          </>
        }
      />
    );
  }

  // En 3D: mazo, descarte y dorsos tumbados en el tapete; placas y avisos, encima.
  // Cada rival se dibujaba como una columna centrada: dorsos, placa y aviso.
  const seatTop = (point: Point) => point.y - (backHeight + 6 + 48 + 6 + 16) / 2;
  const cardHalf = place.lying(layout.card * 1.4) / 2;
  return (
    <Stage
      sectionRef={ref}
      placement={place}
      layout={layout}
      scale={scale}
      height={height}
      label="Mesa de Prisma"
      shape="rounded-[1.75rem]"
      shade="bg-[radial-gradient(ellipse_at_center,transparent_50%,rgb(0_0_0/0.4))]"
      table={
        <>
          {ring}
          {glows}
          <div className={`${CENTERED} keep-3d`} style={place.onTable(deck)}>
            {deckButton}
          </div>
          <div className={`${CENTERED} keep-3d`} style={place.onTable(discard)}>
            {discardPile}
          </div>
          {rivals.map((player, index) => (
            <div
              key={player.seat}
              className={`${BOTTOM_CENTERED} keep-3d`}
              style={place.onTable({ x: points[index].x, y: seatTop(points[index]) + backHeight })}
            >
              <Backs player={player} compact={compact} />
            </div>
          ))}
        </>
      }
      hud={
        <>
          <div className={CENTERED} style={place.overTable({ x: deck.x, y: deck.y + cardHalf * 0.86 + 16 })}>
            {deckLabel}
          </div>
          <div className={CENTERED} style={place.overTable({ x: discard.x, y: discard.y + cardHalf + 22 })}>
            {colorLabel}
          </div>
          {notices}
          {rivals.map((player, index) => (
            <div
              key={player.seat}
              className={TOP_CENTERED}
              style={place.overTable({ x: points[index].x, y: seatTop(points[index]) + backHeight + 8 })}
            >
              <Seat
                player={player}
                turn={frame.turn === player.seat}
                thinking={settled && frame.turn === player.seat}
                compact={compact}
                withBacks={false}
              />
            </div>
          ))}
          <div className={CENTERED} style={place.overTable(layout.me)}>
            <Seat player={mine} turn={frame.turn === me} thinking={false} compact={compact} />
          </div>
        </>
      }
    />
  );
}
