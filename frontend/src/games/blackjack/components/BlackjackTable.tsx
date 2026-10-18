import type { CSSProperties } from "react";
import { PlayingCard } from "../../../shared/cards/PlayingCard";
import { Avatar } from "../../../shared/components/Avatar";
import { ChipStack } from "../../../shared/components/Chips";
import { useFit } from "../../../shared/useFit";
import { DONE_LABEL, handProfit, resultLabel, totalLabel } from "../describe";
import type { Frame, HandFrame, SeatFrame } from "../timeline";
import type { Rules } from "../types";

// Mesa de media luna: el crupier arriba, con el zapato a su derecha, y los
// jugadores en arco abajo. El primero en jugar se sienta a la izquierda del
// crupier, que desde nuestro lado es la derecha. Como en el poker, la mesa se
// dibuja en un lienzo de tamaño fijo que se escala entero.

interface Point {
  x: number;
  y: number;
}

interface SeatSize {
  width: number; // de la placa
  height: number;
  avatar: number;
  card: number; // ancho de sus cartas
}

interface Layout {
  width: number;
  height: number;
  dealer: Point; // centro de las cartas del crupier
  dealerCard: number;
  shoe: Point;
  rules: Point; // donde va el texto impreso en el tapete
  bot: SeatSize;
  human: SeatSize;
  seats: (count: number, human: number) => Point[]; // centro de la placa de cada asiento
}

/** Asientos en arco: el primero a la derecha y el último a la izquierda. */
function arc(center: Point, radius: Point, from: number, to: number) {
  return (count: number): Point[] =>
    Array.from({ length: count }, (_, index) => {
      const share = count === 1 ? 0.5 : index / (count - 1);
      const angle = ((from + (to - from) * share) * Math.PI) / 180;
      return { x: center.x + radius.x * Math.cos(angle), y: center.y + radius.y * Math.sin(angle) };
    });
}

const LANDSCAPE: Layout = {
  width: 1120,
  height: 620,
  dealer: { x: 560, y: 108 },
  dealerCard: 66,
  shoe: { x: 950, y: 96 },
  rules: { x: 560, y: 236 },
  bot: { width: 172, height: 50, avatar: 40, card: 46 },
  human: { width: 224, height: 58, avatar: 50, card: 62 },
  seats: (count) => {
    const spread = Math.min(136, 34 * count + 2); // con pocos jugadores, más juntos
    return arc({ x: 560, y: 150 }, { x: 440, y: 345 }, 90 - spread / 2, 90 + spread / 2)(count);
  },
};

const PORTRAIT: Layout = {
  width: 500,
  height: 900,
  dealer: { x: 250, y: 104 },
  dealerCard: 54,
  shoe: { x: 432, y: 92 },
  rules: { x: 250, y: 236 },
  bot: { width: 112, height: 42, avatar: 30, card: 34 },
  human: { width: 214, height: 54, avatar: 46, card: 58 },
  // En vertical, los bots en una fila (el primero a la derecha) y yo debajo, en grande.
  seats: (count, human) => {
    const bots = count - 1;
    const points: Point[] = [];
    let slot = 0;
    for (let seat = 0; seat < count; seat++) {
      if (seat === human) {
        points.push({ x: 250, y: 790 });
      } else {
        const x = bots === 1 ? 250 : 440 - (380 * slot) / (bots - 1);
        points.push({ x, y: 500 });
        slot += 1;
      }
    }
    return points;
  },
};

const CENTERED = "absolute -translate-x-1/2 -translate-y-1/2";
const FULL_ART_FROM = 44; // ancho en pantalla (px) desde el que una carta luce su dibujo completo
const REST_FLOAT = 0.15;
const at = (point: Point): CSSProperties => ({ left: point.x, top: point.y });
const cardWidth = (width: number) => ({ "--card-w": `${width}px` }) as CSSProperties;

function Total({ hand }: { hand: HandFrame }) {
  if (hand.total === null) return null;
  const bust = hand.total > 21;
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-black tabular-nums shadow ${bust ? "bg-rose-800 text-rose-50" : "bg-black/70 text-amber-100"}`}
    >
      {bust ? `Se pasa (${hand.total})` : totalLabel(hand.total, hand.soft)}
    </span>
  );
}

function Result({ hand }: { hand: HandFrame }) {
  if (hand.result === null) return null;
  const profit = handProfit(hand);
  const good = hand.result === "win" || hand.result === "blackjack";
  const style = good
    ? "bg-gradient-to-b from-amber-200 to-amber-500 text-stone-900"
    : hand.result === "push"
      ? "bg-white/20 text-white"
      : "bg-black/65 text-rose-200";
  return (
    <span className={`pop-in whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-black shadow ${style}`}>
      {resultLabel(hand.result)}
      {profit !== 0 && ` ${profit > 0 ? "+" : "−"}${Math.abs(profit)}`}
    </span>
  );
}

interface HandProps {
  hand: HandFrame;
  card: number;
  scale: number;
  mine: boolean;
  active: boolean; // le toca decidir a esta mano
}

/** Una mano: su total (o su resultado), sus cartas abiertas y su apuesta. */
function HandView({ hand, card, scale, mine, active }: HandProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex h-6 items-end">{hand.result ? <Result hand={hand} /> : <Total hand={hand} />}</div>
      <div
        className={`flex rounded-lg p-0.5 ${active ? "ring-2 ring-amber-300/80" : ""}`}
        style={{ ...cardWidth(card), minHeight: card * 1.4 }}
      >
        {hand.cards.map((text, index) => (
          <span key={index} style={{ marginLeft: index === 0 ? 0 : -card * 0.45 }}>
            <PlayingCard
              card={text}
              enter="deal"
              interactive={mine ? "tilt" : undefined}
              float={mine ? REST_FLOAT : 0}
              detail={card * scale >= FULL_ART_FROM ? "full" : "compact"}
            />
          </span>
        ))}
      </div>
      {hand.bet > 0 && (
        <span className="flex items-center gap-1">
          <ChipStack className="h-5 w-5" />
          <span className="rounded-full bg-black/60 px-2 py-0.5 text-xs font-bold tabular-nums">
            {hand.bet}
            {hand.doubled && <span className="ml-1 text-amber-300">×2</span>}
          </span>
        </span>
      )}
    </div>
  );
}

interface SeatProps {
  seat: SeatFrame;
  size: SeatSize;
  scale: number;
  acting: Frame["acting"];
  thinking: boolean;
}

function SeatView({ seat, size, scale, acting, thinking }: SeatProps) {
  const myTurn = acting?.seat === seat.seat;
  const won = seat.hands.some((hand) => hand.result === "win" || hand.result === "blackjack");
  const ring = won ? "ring-emerald-400" : myTurn ? "ring-amber-300" : "ring-white/25";
  // Con varias manos (tras dividir), cartas un poco más pequeñas para que quepan.
  const card = seat.hands.length > 2 ? size.card * 0.72 : seat.hands.length === 2 ? size.card * 0.86 : size.card;
  const note = seat.gone
    ? "Se ha ido"
    : thinking
      ? "Pensando…"
      : seat.action
        ? DONE_LABEL[seat.action] ?? seat.action
        : seat.isHuman || seat.person
          ? ""
          : seat.level;

  return (
    <div className="relative" style={{ width: size.width }}>
      <div
        data-zone="hand"
        className="absolute left-1/2 flex -translate-x-1/2 items-end gap-2"
        style={{ bottom: size.height + 6 }}
      >
        {seat.hands.map((hand, index) => (
          <HandView
            key={index}
            hand={hand}
            card={card}
            scale={scale}
            mine={seat.isHuman}
            active={myTurn && acting?.hand === index && seat.hands.length > 1}
          />
        ))}
      </div>
      <div
        className="relative flex items-center gap-2.5 rounded-full bg-[#0c0709]/90 p-1 shadow-lg shadow-black/50 ring-1 ring-amber-400/35"
        style={{ height: size.height }}
      >
        <span className="shrink-0 rounded-full">
          <Avatar name={seat.name} size={size.avatar} ring={ring} />
        </span>
        <div className="min-w-0 flex-1 pr-3 leading-tight">
          <div className="truncate text-sm font-semibold">{seat.name}</div>
          <div className="text-[15px] font-semibold tabular-nums text-amber-300">{seat.stack}</div>
        </div>
        {seat.insurance > 0 && (
          <span className="absolute -right-1 -top-2 rounded-full bg-sky-900 px-1.5 text-[10px] font-bold text-sky-100" title="Seguro">
            S {seat.insurance}
          </span>
        )}
      </div>
      <div
        key={note}
        className={`absolute inset-x-0 top-full mt-1 truncate text-center text-[11px] ${seat.action || thinking ? "pop-in font-semibold text-amber-200" : "text-emerald-50/55"}`}
      >
        {note}
      </div>
    </div>
  );
}

function FeltRules({ rules, width }: { rules: Rules; width: number }) {
  return (
    <div className="flex select-none flex-col items-center text-center text-amber-100/30" style={{ width }}>
      <svg viewBox="0 0 520 70" className="w-full" aria-hidden>
        <defs>
          <path id="felt-arc" d="M20 62 Q260 -6 500 62" />
        </defs>
        <text fill="currentColor" fontSize="26" fontWeight="900" letterSpacing="5">
          <textPath href="#felt-arc" startOffset="50%" textAnchor="middle">
            BLACKJACK PAGA 3 A 2
          </textPath>
        </text>
      </svg>
      <p className="text-sm font-bold uppercase tracking-[0.18em]">
        {rules.dealer_hits_soft_17 ? "El crupier pide con 17 blando" : "El crupier se planta con 17"}
      </p>
      <p className="mt-1 text-xs font-semibold uppercase tracking-[0.2em]">El seguro paga 2 a 1</p>
    </div>
  );
}

interface Props {
  frame: Frame;
  rules: Rules;
  shoe: { remaining: number; total: number; cutReached: boolean };
  settled: boolean; // lo dibujado ya es el estado del servidor
}

/** La mesa de blackjack: crupier, zapato, reglas en el tapete y los asientos. */
export function BlackjackTable({ frame, rules, shoe, settled }: Props) {
  const { ref, layout, scale } = useFit(LANDSCAPE, PORTRAIT, { maxHeightShare: 0.64 });
  const human = frame.seats.findIndex((seat) => seat.isHuman);
  const points = layout.seats(frame.seats.length, human);
  const dealerCount = Math.max(frame.dealer.cards.length, 2);
  const spot = frame.acting ? points[frame.acting.seat] : null;
  const hidden = frame.dealer.cards.includes(null);

  return (
    <section
      ref={ref}
      className="felt rim relative w-full overflow-hidden"
      style={{
        height: layout.height * scale,
        borderRadius: "2rem 2rem 50% 50% / 2rem 2rem 14% 14%",
      }}
      aria-label="Mesa de blackjack"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_20%,transparent_45%,rgb(0_0_0/0.38))]" />
      <div
        className="absolute left-1/2 top-0 origin-top"
        style={{ width: layout.width, height: layout.height, transform: `translateX(-50%) scale(${scale})` }}
      >
        {spot && (
          <div
            key={frame.acting!.seat}
            className={`${CENTERED} glow-turn h-[340px] w-[340px] rounded-full bg-[radial-gradient(closest-side,rgb(254_249_195/0.2),transparent)]`}
            style={at({ x: spot.x, y: spot.y - 60 })}
          />
        )}

        <div className={CENTERED} style={at(layout.rules)}>
          <FeltRules rules={rules} width={layout.width < 600 ? 360 : 520} />
        </div>

        {/* El crupier. */}
        <div className={`${CENTERED} flex flex-col items-center gap-1.5`} style={at(layout.dealer)}>
          <span className="text-[11px] font-bold uppercase tracking-[0.24em] text-amber-100/80">Crupier</span>
          <div className="flex gap-1.5" style={{ ...cardWidth(layout.dealerCard), minHeight: layout.dealerCard * 1.4 }}>
            {frame.dealer.cards.map((card, index) => (
              <PlayingCard
                key={index}
                card={card}
                enter="deal"
                detail={layout.dealerCard * scale >= FULL_ART_FROM ? "full" : "compact"}
              />
            ))}
            {Array.from({ length: dealerCount - frame.dealer.cards.length }, (_, index) => (
              <span key={`empty-${index}`} className="card invisible inline-block" />
            ))}
          </div>
          <span className="h-6">
            {frame.dealer.total !== null && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-sm font-black tabular-nums shadow ${frame.dealer.total > 21 ? "bg-rose-800 text-rose-50" : "bg-black/70 text-amber-100"}`}
              >
                {frame.dealer.total > 21
                  ? `Se pasa (${frame.dealer.total})`
                  : hidden
                    ? `${frame.dealer.total} + ?`
                    : totalLabel(frame.dealer.total, frame.dealer.soft)}
              </span>
            )}
          </span>
        </div>

        {/* El zapato: de aquí salen todas las cartas. */}
        <div className={`${CENTERED} flex flex-col items-center gap-1`} style={at(layout.shoe)}>
          <span className="relative block" style={cardWidth(layout.dealerCard * 0.72)} title="Zapato">
            <span className="card card-back absolute -left-1.5 -top-1.5 inline-block" />
            <span className="card card-back absolute -left-0.5 -top-0.5 inline-block" />
            <span data-zone="deck" className="card card-back relative block" />
          </span>
          <span className="whitespace-nowrap text-[11px] font-semibold text-amber-100/75 tabular-nums">
            Zapato · {shoe.remaining}
          </span>
          {shoe.cutReached && (
            <span className="whitespace-nowrap rounded-full bg-rose-900/80 px-2 text-[10px] font-bold text-rose-100">
              Se baraja al acabar
            </span>
          )}
        </div>

        {frame.note && (
          <div
            key={frame.note}
            className={`${CENTERED} pop-in rounded-full bg-black/60 px-4 py-1 text-sm font-semibold text-amber-100 shadow`}
            style={at({ x: layout.dealer.x, y: layout.dealer.y + layout.dealerCard * 0.7 + 52 })}
          >
            {frame.note}
          </div>
        )}

        {frame.seats.map((seat, index) => (
          <div key={seat.seat} className={CENTERED} style={at(points[index])} data-seat={seat.seat}>
            <SeatView
              seat={seat}
              size={seat.isHuman ? layout.human : layout.bot}
              scale={scale}
              acting={frame.acting}
              thinking={settled && frame.acting?.seat === seat.seat && !seat.isHuman}
            />
          </div>
        ))}

        <div data-zone="fx" className="pointer-events-none absolute inset-0 z-40" />
      </div>
    </section>
  );
}
