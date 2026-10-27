import { Fragment, type CSSProperties } from "react";
import type { Frame, SeatFrame } from "../timeline/frame";
import { Avatar } from "../../../shared/components/Avatar";
import { ChipPile } from "../../../shared/chips/ChipPile";
import { Emblem } from "../../../shared/components/Emblem";
import { PlayingCard } from "../../../shared/cards/PlayingCard";
import { usePlatformSettings } from "../../../shared/SettingsContext";
import type { Camera } from "../../../shared/stage/camera";
import { Stage, stageHeight, usePlacement, type Placement } from "../../../shared/stage/Stage";
import { useFit } from "../../../shared/useFit";
import { tableChips, type TableChips } from "../chips";

// La mesa se dibuja sobre un lienzo de tamaño fijo y se escala entera para
// ocupar el sitio disponible, como un tablero: así nada se descoloca al cambiar
// el tamaño de la ventana. Hay dos lienzos: apaisado y vertical (móvil).

interface Point {
  x: number;
  y: number;
}

interface SeatSize {
  width: number; // de la placa
  height: number;
  avatar: number; // diámetro
  card: number; // ancho de sus cartas
  gap: number; // hueco entre la placa y las cartas, que van encima de ella
}

interface Layout {
  width: number;
  height: number;
  center: Point; // donde van las cartas comunitarias
  radius: Point; // elipse sobre la que se sientan los jugadores
  boardCard: number;
  bot: SeatSize;
  human: SeatSize;
  humanDrop: number; // cuánto baja mi placa de su sitio, para que no quede pegada a mis cartas
}

const LANDSCAPE: Layout = {
  width: 1120,
  height: 640,
  center: { x: 560, y: 320 },
  radius: { x: 440, y: 220 },
  boardCard: 68,
  bot: { width: 196, height: 56, avatar: 48, card: 38, gap: 4 },
  human: { width: 240, height: 64, avatar: 56, card: 78, gap: 8 },
  humanDrop: 26,
};

const PORTRAIT: Layout = {
  width: 500,
  height: 800,
  center: { x: 250, y: 400 },
  radius: { x: 170, y: 310 },
  boardCard: 52,
  bot: { width: 148, height: 48, avatar: 40, card: 32, gap: 3 },
  human: { width: 196, height: 56, avatar: 48, card: 62, gap: 6 },
  humanDrop: 22,
};

const FULL_ART_FROM = 44; // ancho en pantalla (px) desde el que una carta luce su dibujo completo
const REST_FLOAT = 0.15; // flotación de las cartas en reposo: apenas un respiro
// Lienzo vertical por debajo de 620 px; en apaisado, como mucho el 68 % del alto de
// la ventana; y nunca más pequeño que el 72 %, para que el texto se pueda leer.
const FIT = { portraitBelow: 620, maxHeightShare: 0.68, minScale: 0.72 };

// Cámara de la vista 3D: el tapete se inclina hacia atrás y lo lejano se ve
// más pequeño. En vertical (móvil) se inclina menos, para que todo se lea.
const CAMERA: Camera = { tilt: 42, distance: 1500, eye: 0.55, top: 18, bottom: 40 };
const CAMERA_PORTRAIT: Camera = { tilt: 34, distance: 1500, eye: 0.55, top: 16, bottom: 34 };
const cameraFor = (layout: { width: number }) => (layout.width === PORTRAIT.width ? CAMERA_PORTRAIT : CAMERA);
const FIT_3D = { ...FIT, heightOf: stageHeight(cameraFor) };
const GAP_3D = 6; // en 3D, algo más de aire entre las cartas y la placa, que va por encima
const BOARD_3D = 1.12; // en 3D las comunitarias, al fondo y tumbadas, se dibujan algo más grandes

/** Sitio de cada jugador: `index` 0 abajo y los demás en el sentido de las agujas del reloj. */
function seatPoint(layout: Layout, index: number, count: number, human: boolean): Point {
  const angle = ((90 + (360 * index) / count) * Math.PI) / 180; // 90° = abajo en pantalla
  return {
    x: layout.center.x + layout.radius.x * Math.cos(angle),
    y: layout.center.y + layout.radius.y * Math.sin(angle) + (human ? layout.humanDrop : 0),
  };
}

/** Dónde deja un jugador sus apuestas y hacia dónde crecen al apilarse. */
interface BetSpot {
  point: Point;
  className: string; // por qué borde se cuelga el bloque de su punto
}

/**
 * Dónde deja cada jugador sus apuestas: delante de él, hacia el centro de la
 * mesa. El bloque (jugada, fichas y cantidad) se cuelga por el borde que mira
 * a su placa, así que al crecer la pila crece hacia la mesa, nunca encima de
 * la placa ni de las cartas.
 */
function betSpot(layout: Layout, seat: Point, size: SeatSize, human: boolean): BetSpot {
  // Las mías van a la derecha de mis cartas, a media altura: delante las taparían al levantarlas.
  if (human) {
    const cardsBottom = seat.y - size.height / 2 - size.gap;
    return {
      point: { x: seat.x + size.width / 2, y: cardsBottom - size.card * 0.62 },
      className: "absolute -translate-y-1/2 origin-left",
    };
  }
  const dx = layout.center.x - seat.x;
  const dy = layout.center.y - seat.y;
  const length = Math.hypot(dx, dy) || 1;
  // Quien se sienta arriba del todo las deja a su derecha: debajo de él va el bote.
  if (Math.abs(dx) < 80 && dy > 0) {
    return { point: { x: seat.x + size.width / 2 + 22, y: seat.y }, className: "absolute -translate-y-1/2 origin-left" };
  }
  // A los lados, en cuanto se sale de la placa, hacia el centro.
  if (Math.abs(dx) > 120) {
    const toward = Math.sign(dx);
    return {
      point: { x: seat.x + toward * (size.width / 2 + 16), y: seat.y + (dy / length) * 24 },
      className: toward > 0 ? "absolute -translate-y-1/2 origin-left" : "absolute -translate-x-full -translate-y-1/2 origin-right",
    };
  }
  // Arriba o abajo: hacia el centro, saltando también sus cartas si están en medio.
  const cardsAbove = size.card * 1.4 + size.gap;
  const reachY = dy < 0 ? size.height / 2 + cardsAbove + 6 : size.height / 2 + 30;
  return {
    point: { x: seat.x + (dx / length) * (size.width / 2 + 44), y: seat.y + Math.sign(dy) * reachY },
    className: dy > 0 ? "absolute -translate-x-1/2 origin-top" : "absolute -translate-x-1/2 -translate-y-full origin-bottom",
  };
}

const cardWidth = (width: number) => ({ "--card-w": `${width}px` }) as CSSProperties;

const CENTERED = "absolute -translate-x-1/2 -translate-y-1/2";
const BOTTOM_CENTERED = "absolute -translate-x-1/2 -translate-y-full"; // colgado de su borde de abajo
const CARD_GAP = 4; // entre las dos cartas de un jugador
const DECK_CARD = 26; // ancho de las cartas del mazo

/** Dónde empiezan las cartas, desde el lado del avatar, para quedar centradas sobre el nombre. */
function cardsOffset(size: SeatSize): number {
  const nameStart = size.avatar + 6;
  const cards = 2 * size.card + CARD_GAP;
  return nameStart + (size.width - nameStart - cards) / 2;
}

const STATUS_LABEL: Record<string, string> = {
  folded: "Retirado",
  all_in: "All-in",
  out: "Sin fichas",
};

interface SeatProps {
  seat: SeatFrame;
  frame: Frame;
  size: SeatSize;
  scale: number; // escala a la que se dibuja la mesa
  avatarSide: "left" | "right"; // el avatar va en el extremo que mira al centro de la mesa
  thinking: boolean; // el servidor está esperando a que este bot juegue
  withCards: boolean; // en 2D las cartas y el mazo van con la placa; en 3D, tumbados en el tapete
}

/** Las dos cartas de un jugador. */
function SeatCards({ seat, size, scale }: { seat: SeatFrame; size: SeatSize; scale: number }) {
  return (
    <>
      {seat.cards.map((card, index) => (
        <PlayingCard
          key={index}
          card={card}
          enter="deal"
          // Mis cartas están vivas: se inclinan con el ratón y se levantan al pulsarlas.
          interactive={seat.isHuman ? "select" : undefined}
          float={seat.isHuman ? REST_FLOAT : 0}
          fan={seat.isHuman ? (index === 0 ? -4 : 4) : 0}
          detail={size.card * scale >= FULL_ART_FROM ? "full" : "compact"}
          held={seat.isHuman}
        />
      ))}
    </>
  );
}

/** El mazo, junto a quien reparte. De aquí salen las cartas. */
function Deck() {
  return (
    <span
      className="card-float deck-stack keep-3d relative block"
      style={{ "--float": REST_FLOAT } as CSSProperties}
      title="Mazo"
    >
      <span className="card card-back absolute -left-1 -top-1 inline-block" />
      <span className="card card-back absolute -left-0.5 -top-0.5 inline-block" />
      <span data-zone="deck" className="card card-back relative block" />
    </span>
  );
}

function SeatPlaque({ seat, frame, size, scale, avatarSide, thinking, withCards }: SeatProps) {
  const acting = frame.actingSeat === seat.seat;
  const dealer = frame.buttonSeat === seat.seat;
  const faded = seat.status === "folded" || seat.status === "out";
  const blind =
    frame.smallBlindSeat === seat.seat ? "CP" : frame.bigBlindSeat === seat.seat ? "CG" : null;
  const ring = seat.won > 0 ? "ring-emerald-400" : acting ? "ring-amber-300" : "ring-white/25";

  // Línea pequeña bajo la placa: lo más importante que haya que saber del jugador.
  let note = seat.isHuman || seat.person ? "" : `${seat.level} · ${seat.style}`;
  let noteColor = "text-emerald-50/55";
  if (seat.gone) {
    note = "Se ha ido";
    noteColor = "text-white/50";
  } else if (seat.handName) {
    note = seat.handName;
    noteColor = "font-semibold text-amber-200";
  } else if (STATUS_LABEL[seat.status]) {
    note = STATUS_LABEL[seat.status];
    noteColor = seat.status === "all_in" ? "font-semibold text-amber-200" : "text-white/50";
  } else if (thinking) {
    note = "Pensando…";
    noteColor = "text-amber-200";
  }

  return (
    <div className="relative" style={{ width: size.width }}>
      {/* Sus cartas van encima de la placa, enteras, sobre el nombre. */}
      {withCards && (
        <div
          data-zone="hand"
          className="absolute flex"
          style={{
            bottom: size.height + size.gap,
            [avatarSide]: cardsOffset(size),
            gap: CARD_GAP,
            ...cardWidth(size.card),
          }}
        >
          <SeatCards seat={seat} size={size} scale={scale} />
        </div>
      )}

      {/* El mazo está junto a quien tiene el botón, encima de su avatar. */}
      {withCards && dealer && (
        <span
          className="absolute"
          style={{ bottom: size.height + size.gap, [avatarSide]: 8, ...cardWidth(DECK_CARD) }}
        >
          <Deck />
        </span>
      )}

      <div
        className={`relative flex items-center gap-2.5 rounded-full bg-[#0c0709]/90 p-1 shadow-lg shadow-black/50 ring-1 ring-amber-400/35 ${avatarSide === "right" ? "flex-row-reverse" : ""} ${faded ? "opacity-60" : ""}`}
        style={{ height: size.height }}
      >
        {/* De aquí salen sus fichas al apostar y aquí llegan las que gana. */}
        <span data-anchor="chips" className="shrink-0 rounded-full">
          <Avatar name={seat.name} size={size.avatar} ring={ring} />
        </span>
        <div className={`min-w-0 flex-1 leading-tight ${avatarSide === "right" ? "pl-4" : "pr-4"}`}>
          <div className="flex items-center gap-1.5">
            <span className="truncate text-sm font-semibold">{seat.name}</span>
            {blind && (
              <span
                className="rounded bg-white/15 px-1 text-[10px] font-bold"
                title={blind === "CP" ? "Ciega pequeña" : "Ciega grande"}
              >
                {blind}
              </span>
            )}
          </div>
          <div className="text-[15px] font-semibold tabular-nums text-amber-300">{seat.stack}</div>
        </div>
      </div>

      {dealer && (
        <span
          className="absolute flex h-[22px] w-[22px] items-center justify-center rounded-full bg-white text-xs font-black text-rose-600 shadow"
          style={{ bottom: -5, [avatarSide]: -5 }}
          title="Botón de dealer"
        >
          D
        </span>
      )}

      <div className={`absolute inset-x-0 top-full mt-1 truncate text-center text-[11px] ${noteColor}`}>
        {note}
      </div>
    </div>
  );
}

const CHIP = { bet: 30, mine: 34, pot: 34 }; // diámetro de las fichas, en px

/**
 * Lo que el jugador tiene delante: su jugada y sus fichas apostadas, o lo que
 * gana. El sitio de sus fichas existe siempre, aunque esté vacío: allí llegan
 * las que apuesta y las que cobra.
 */
function SeatBets({ seat, chips }: { seat: SeatFrame; chips: TableChips }) {
  const action = seat.status === "folded" ? null : seat.action;
  const bet = chips.bets.get(seat.seat) ?? [];
  const won = chips.won.get(seat.seat) ?? [];
  const size = seat.isHuman ? CHIP.mine : CHIP.bet;
  return (
    <div className="flex flex-col items-center gap-1 whitespace-nowrap">
      {action && (
        <span
          key={action}
          className="pop-in rounded-full bg-black/45 px-2.5 py-0.5 text-xs font-medium text-white/90"
        >
          {action}
        </span>
      )}
      <span data-pile={`bet-${seat.seat}`} className="flex items-end gap-1.5">
        {bet.length > 0 && (
          <>
            <ChipPile chips={bet} pile={`bet-${seat.seat}-chips`} size={size} tallest={5} />
            <span className="rounded-full bg-black/60 px-2.5 py-0.5 text-sm font-bold tabular-nums">{seat.bet}</span>
          </>
        )}
        {won.length > 0 && (
          <>
            <ChipPile chips={won} pile={`won-${seat.seat}`} size={size} tallest={5} />
            <span className="pop-in rounded-full bg-gradient-to-b from-amber-200 to-amber-500 px-3 py-0.5 text-sm font-black text-stone-900 shadow">
              +{seat.won}
            </span>
          </>
        )}
      </span>
    </div>
  );
}

interface Props {
  frame: Frame;
  settled: boolean; // lo dibujado ya es el estado del servidor (no quedan pasos)
}

/** Dónde van, en el lienzo 2D, las cartas y el mazo de un jugador: encima de su placa. */
function seatTop(point: Point, size: SeatSize, avatarSide: "left" | "right", gap: number) {
  const bottom = point.y - size.height / 2 - size.gap - gap; // borde de abajo de sus cartas
  const cards = 2 * size.card + CARD_GAP;
  const toward = avatarSide === "left" ? 1 : -1; // desde el lado del avatar hacia el otro
  const edge = point.x - (toward * size.width) / 2; // el extremo del avatar
  return {
    cards: { x: edge + toward * (cardsOffset(size) + cards / 2), y: bottom },
    deck: { x: edge + toward * (8 + DECK_CARD / 2), y: bottom },
  };
}

interface Props {
  frame: Frame;
  settled: boolean; // lo dibujado ya es el estado del servidor (no quedan pasos)
}

/** La mesa: tapete, cartas comunitarias, bote y los jugadores alrededor. */
export function Table({ frame, settled }: Props) {
  const { view } = usePlatformSettings();
  const { ref, layout, scale, height } = useFit(LANDSCAPE, PORTRAIT, view === "3d" ? FIT_3D : FIT);
  const place = usePlacement(view, layout, cameraFor(layout));
  const flat = place.view === "2d";
  const count = frame.seats.length;
  const emptySlots = Array.from({ length: 5 - frame.board.length });
  const boardHeight = layout.boardCard * 1.4;
  // Yo siempre abajo; los demás, en el orden de la mesa a partir de mí. Contra
  // bots soy el asiento 0, pero en una sala puedo estar en cualquiera.
  const mine = Math.max(0, frame.seats.findIndex((seat) => seat.isHuman));
  const seats = frame.seats.map((seat, index) => {
    const point = seatPoint(layout, (index - mine + count) % count, count, seat.isHuman);
    return {
      seat,
      point,
      size: seat.isHuman ? layout.human : layout.bot,
      avatarSide: (point.x < layout.center.x - 1 ? "right" : "left") as "left" | "right",
    };
  });
  const spotlight = seats.find(({ seat }) => seat.won > 0 || seat.seat === frame.actingSeat);
  const chips = tableChips(frame);
  // El contorno de la mesa, dibujado en el tapete.
  const outline = {
    from: place.onTable({ x: layout.center.x - layout.radius.x * 0.82, y: layout.center.y - layout.radius.y }),
    to: place.onTable({ x: layout.center.x + layout.radius.x * 0.82, y: layout.center.y + layout.radius.y }),
  };

  const potLabel = potLabelAt(place.overTable);
  const players = seatViews(place.overTable);

  const table = (
    <>
      {/* Línea que dibuja el contorno de la mesa. */}
      <div
        className="absolute rounded-[999px] border-2 border-amber-200/20"
        style={{
          left: outline.from.left,
          top: outline.from.top,
          width: Number(outline.to.left) - Number(outline.from.left),
          height: Number(outline.to.top) - Number(outline.from.top),
        }}
      />

      {/* Luz sobre quien tiene el turno o acaba de ganar. */}
      {spotlight && (
        <div
          // Con otra clave por jugador, la luz se apaga en uno y se enciende en el siguiente.
          key={`${spotlight.seat.seat}-${spotlight.seat.won > 0}`}
          className={`${CENTERED} h-[420px] w-[420px] rounded-full ${spotlight.seat.won > 0 ? "glow-in bg-[radial-gradient(closest-side,rgb(110_231_183/0.28),transparent)]" : "glow-turn bg-[radial-gradient(closest-side,rgb(254_249_195/0.2),transparent)]"}`}
          style={place.onTable(spotlight.point)}
        />
      )}

      {/* Marca del juego, estampada en el tapete. */}
      <div
        className={`${CENTERED} flex select-none flex-col items-center text-black/[0.13]`}
        style={place.onTable({ x: layout.center.x, y: layout.center.y - 4 })}
      >
        <Emblem className="h-28 w-28" />
        <span className="mt-1 text-3xl font-black tracking-[0.14em]">MI-POKER</span>
      </div>

      {flat && potLabel}

      <div
        data-zone="board"
        className={`${CENTERED} keep-3d flex gap-2`}
        style={{ ...place.onTable(layout.center), ...cardWidth(layout.boardCard * (flat ? 1 : BOARD_3D)) }}
      >
        {frame.board.map((card) => (
          <PlayingCard
            key={card}
            card={card}
            enter="board"
            interactive="tilt"
            float={REST_FLOAT}
            detail={layout.boardCard * scale >= FULL_ART_FROM ? "full" : "compact"}
          />
        ))}
        {emptySlots.map((_, index) => (
          <span key={index} className="card invisible inline-block" />
        ))}
      </div>

      {/* En 3D, las cartas y el mazo de cada jugador van tumbados en el tapete. */}
      {!flat &&
        seats.map(({ seat, point, size, avatarSide }) => {
          const top = seatTop(point, size, avatarSide, GAP_3D);
          return (
            <Fragment key={seat.seat}>
              <div
                data-seat={seat.seat}
                data-zone="hand"
                className={`${BOTTOM_CENTERED} keep-3d flex`}
                style={{ ...place.onTable(top.cards), gap: CARD_GAP, ...cardWidth(size.card) }}
              >
                <SeatCards seat={seat} size={size} scale={scale} />
              </div>
              {frame.buttonSeat === seat.seat && (
                <span className={BOTTOM_CENTERED} style={{ ...place.onTable(top.deck), ...cardWidth(DECK_CARD) }}>
                  <Deck />
                </span>
              )}
            </Fragment>
          );
        })}

      {flat && players}
    </>
  );

  // Lo que hay que leer: el bote, las apuestas y las placas de los jugadores.
  function seatViews(placeOver: Placement["overTable"]) {
    return seats.map(({ seat, point, size, avatarSide }) => {
      const spot = betSpot(layout, point, size, seat.isHuman);
      return (
        <div key={seat.seat}>
          <div className={spot.className} style={placeOver(spot.point, "full")}>
            <SeatBets seat={seat} chips={chips} />
          </div>
          <div className={CENTERED} style={placeOver(point)} data-seat={seat.seat}>
            <SeatPlaque
              seat={seat}
              frame={frame}
              size={size}
              scale={scale}
              avatarSide={avatarSide}
              thinking={settled && frame.actingSeat === seat.seat && !seat.isHuman}
              withCards={flat}
            />
          </div>
        </div>
      );
    });
  }

  // El bote: sus fichas en el centro de la mesa, y al lado lo que suma con las apuestas de la ronda.
  function potLabelAt(placeOver: Placement["overTable"]) {
    return (
      // Colgado de su borde de abajo: si la pila crece, crece hacia arriba, sin pisar las cartas.
      <div
        className={`${BOTTOM_CENTERED} flex items-end gap-2.5`}
        style={placeOver({ x: layout.center.x, y: layout.center.y - boardHeight / 2 - 12 }, "full")}
      >
        <span data-pile="pot" className="flex min-h-1 min-w-1 items-end">
          {chips.pot.length > 0 && <ChipPile chips={chips.pot} pile="pot-chips" size={CHIP.pot} tallest={5} />}
        </span>
        <span className="flex flex-col items-center">
          <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-amber-100/85">Bote</span>
          <span
            data-zone="pot"
            className="rounded-full border border-amber-400/55 bg-black/60 px-4 py-0.5 text-lg font-black tabular-nums text-amber-200"
          >
            {frame.pot}
          </span>
        </span>
      </div>
    );
  }

  return (
    <Stage
      sectionRef={ref}
      placement={place}
      layout={layout}
      scale={scale}
      height={height}
      label="Mesa de poker"
      shape="rounded-[1.75rem]"
      shade="bg-[radial-gradient(ellipse_at_center,transparent_55%,rgb(0_0_0/0.38))]"
      table={table}
      hud={
        flat ? null : (
          <>
            {potLabel}
            {players}
          </>
        )
      }
    />
  );
}
