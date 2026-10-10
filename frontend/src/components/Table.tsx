import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import type { Frame, SeatFrame } from "../timeline/frame";
import { Avatar } from "./Avatar";
import { ChipStack } from "./Chips";
import { Emblem } from "./Emblem";
import { PlayingCard } from "./PlayingCard";

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
  overlap: number; // cuánto tapa la placa a las cartas
}

interface Layout {
  width: number;
  height: number;
  center: Point; // donde van las cartas comunitarias
  radius: Point; // elipse sobre la que se sientan los jugadores
  boardCard: number;
  bot: SeatSize;
  human: SeatSize;
}

const LANDSCAPE: Layout = {
  width: 1120,
  height: 640,
  center: { x: 560, y: 312 },
  radius: { x: 440, y: 224 },
  boardCard: 58,
  bot: { width: 196, height: 56, avatar: 48, card: 38, overlap: 12 },
  human: { width: 224, height: 64, avatar: 56, card: 64, overlap: 20 },
};

const PORTRAIT: Layout = {
  width: 500,
  height: 780,
  center: { x: 250, y: 365 },
  radius: { x: 170, y: 305 },
  boardCard: 46,
  bot: { width: 148, height: 48, avatar: 40, card: 32, overlap: 10 },
  human: { width: 190, height: 56, avatar: 48, card: 54, overlap: 16 },
};

const PORTRAIT_BELOW = 620; // ancho disponible por debajo del cual se usa el lienzo vertical
const MAX_HEIGHT_SHARE = 0.68; // en apaisado, parte del alto de la ventana que puede ocupar
const MIN_SCALE = 0.72; // por debajo, el texto se vuelve ilegible: mejor desplazar la página

/** Elige el lienzo y la escala para el ancho disponible. */
function useFit() {
  const ref = useRef<HTMLElement>(null);
  const [fit, setFit] = useState({ layout: LANDSCAPE, scale: 1 });

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => {
      const width = element.clientWidth;
      const layout = width < PORTRAIT_BELOW ? PORTRAIT : LANDSCAPE;
      const byWidth = width / layout.width;
      const byHeight =
        layout === LANDSCAPE ? (window.innerHeight * MAX_HEIGHT_SHARE) / layout.height : byWidth;
      const scale = Math.min(byWidth, Math.max(byHeight, MIN_SCALE));
      setFit((current) =>
        current.layout === layout && current.scale === scale ? current : { layout, scale },
      );
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  }, []);

  return { ref, ...fit };
}

/** Sitio de cada jugador: tú abajo y los demás en el sentido de las agujas del reloj. */
function seatPoint(layout: Layout, index: number, count: number): Point {
  const angle = ((90 + (360 * index) / count) * Math.PI) / 180; // 90° = abajo en pantalla
  return {
    x: layout.center.x + layout.radius.x * Math.cos(angle),
    y: layout.center.y + layout.radius.y * Math.sin(angle),
  };
}

/** Dónde deja cada jugador sus apuestas: delante de él, hacia el centro de la mesa. */
function betPoint(layout: Layout, seat: Point, size: SeatSize, human: boolean): Point {
  // Las mías van a la derecha de mis cartas: delante las taparían al levantarlas.
  if (human) return { x: seat.x + size.width / 2 + 34, y: seat.y - size.height / 2 - 26 };
  const dx = layout.center.x - seat.x;
  const dy = layout.center.y - seat.y;
  const length = Math.hypot(dx, dy) || 1;
  // Hacia los lados basta con salir de la placa; hacia arriba hay que saltar también sus cartas.
  const cardsAbove = size.card * 1.4 - size.overlap;
  const reachX = size.width / 2 + 44;
  const reachY = dy < 0 ? size.height / 2 + cardsAbove + 30 : size.height / 2 + 44;
  return { x: seat.x + (dx / length) * reachX, y: seat.y + (dy / length) * reachY };
}

const at = (point: Point): CSSProperties => ({ left: point.x, top: point.y });
const cardWidth = (width: number) => ({ "--card-w": `${width}px` }) as CSSProperties;

const CENTERED = "absolute -translate-x-1/2 -translate-y-1/2";

const STATUS_LABEL: Record<string, string> = {
  folded: "Retirado",
  all_in: "All-in",
  out: "Sin fichas",
};

interface SeatProps {
  seat: SeatFrame;
  frame: Frame;
  size: SeatSize;
  avatarSide: "left" | "right"; // el avatar va en el extremo que mira al centro de la mesa
  thinking: boolean; // el servidor está esperando a que este bot juegue
}

function SeatPlaque({ seat, frame, size, avatarSide, thinking }: SeatProps) {
  const acting = frame.actingSeat === seat.seat;
  const dealer = frame.buttonSeat === seat.seat;
  const faded = seat.status === "folded" || seat.status === "out";
  const blind =
    frame.smallBlindSeat === seat.seat ? "CP" : frame.bigBlindSeat === seat.seat ? "CG" : null;
  const ring = seat.won > 0 ? "ring-emerald-400" : acting ? "ring-amber-300" : "ring-white/25";

  // Línea pequeña bajo la placa: lo más importante que haya que saber del jugador.
  let note = seat.isHuman ? "" : `${seat.level} · ${seat.style}`;
  let noteColor = "text-emerald-50/55";
  if (seat.handName) {
    note = seat.handName;
    noteColor = "font-semibold text-sky-200";
  } else if (STATUS_LABEL[seat.status]) {
    note = STATUS_LABEL[seat.status];
    noteColor = seat.status === "all_in" ? "font-semibold text-amber-200" : "text-white/50";
  } else if (thinking) {
    note = "Pensando…";
    noteColor = "text-amber-200";
  }

  return (
    <div className="relative" style={{ width: size.width }}>
      {/* Sus cartas asoman por detrás de la placa, sobre el lado del nombre. */}
      <div
        data-zone="hand"
        className="peek absolute flex gap-1"
        style={{
          bottom: size.height - size.overlap,
          [avatarSide]: size.avatar + 14,
          ...cardWidth(size.card),
        }}
      >
        {seat.cards.map((card, index) => (
          <PlayingCard
            key={index}
            card={card}
            enter="deal"
            // Mis cartas están vivas: flotan, se inclinan y se levantan al pulsarlas.
            interactive={seat.isHuman ? "select" : undefined}
            float={seat.isHuman ? 1 : 0}
            fan={seat.isHuman ? (index === 0 ? -4 : 4) : 0}
          />
        ))}
      </div>

      {/* El mazo está junto a quien tiene el botón. */}
      {dealer && (
        <span
          className="absolute"
          style={{ bottom: size.height - 8, [avatarSide]: 8, ...cardWidth(26) }}
          title="Mazo"
        >
          <span className="card-float relative block" style={{ "--float": 0.6 } as CSSProperties}>
            <span className="card card-back absolute -left-1 -top-1 inline-block" />
            <span className="card card-back absolute -left-0.5 -top-0.5 inline-block" />
            {/* De aquí salen las cartas al repartir. */}
            <span data-zone="deck" className="card card-back relative block" />
          </span>
        </span>
      )}

      <div
        className={`relative flex items-center gap-2.5 rounded-full bg-[#090d15]/90 p-1 shadow-lg shadow-black/40 ${avatarSide === "right" ? "flex-row-reverse" : ""} ${faded ? "opacity-60" : ""}`}
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
          <div className="text-[15px] font-semibold tabular-nums text-emerald-400">{seat.stack}</div>
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

/** Lo que el jugador tiene delante: su jugada, sus fichas apostadas o lo que gana. */
function SeatBets({ seat }: { seat: SeatFrame }) {
  const action = seat.status === "folded" ? null : seat.action;
  if (!action && seat.bet === 0 && seat.won === 0) return null;
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
      {seat.bet > 0 && (
        <span className="flex items-center gap-1">
          <ChipStack className="h-6 w-6" />
          <span className="rounded-full bg-black/60 px-2.5 py-0.5 text-sm font-bold tabular-nums">
            {seat.bet}
          </span>
        </span>
      )}
      {seat.won > 0 && (
        <span className="pop-in rounded-full bg-emerald-400 px-3 py-0.5 text-sm font-black text-emerald-950 shadow">
          +{seat.won}
        </span>
      )}
    </div>
  );
}

interface Props {
  frame: Frame;
  settled: boolean; // lo dibujado ya es el estado del servidor (no quedan pasos)
}

/** La mesa: tapete, cartas comunitarias, bote y los jugadores alrededor. */
export function Table({ frame, settled }: Props) {
  const { ref, layout, scale } = useFit();
  const count = frame.seats.length;
  const emptySlots = Array.from({ length: 5 - frame.board.length });
  const boardHeight = layout.boardCard * 1.4;
  const seats = frame.seats.map((seat, index) => ({ seat, point: seatPoint(layout, index, count) }));
  const spotlight = seats.find(({ seat }) => seat.won > 0 || seat.seat === frame.actingSeat);

  return (
    <section
      ref={ref}
      className="felt relative w-full overflow-hidden rounded-[1.75rem] shadow-xl ring-1 ring-black/50"
      style={{ height: layout.height * scale }}
      aria-label="Mesa de poker"
    >
      {/* Sombra hacia los bordes, para dar profundidad al tapete. */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_55%,rgb(0_0_0/0.38))]" />

      <div
        className="absolute left-1/2 top-0 origin-top"
        style={{
          width: layout.width,
          height: layout.height,
          transform: `translateX(-50%) scale(${scale})`,
        }}
      >
        {/* Línea que dibuja el contorno de la mesa. */}
        <div
          className="absolute rounded-[999px] border-2 border-white/10"
          style={{
            left: layout.center.x - layout.radius.x * 0.82,
            right: layout.width - layout.center.x - layout.radius.x * 0.82,
            top: layout.center.y - layout.radius.y,
            bottom: layout.height - layout.center.y - layout.radius.y,
          }}
        />

        {/* Luz sobre quien tiene el turno o acaba de ganar. */}
        {spotlight && (
          <div
            // Con otra clave por jugador, la luz se apaga en uno y se enciende en el siguiente.
            key={`${spotlight.seat.seat}-${spotlight.seat.won > 0}`}
            className={`${CENTERED} h-[420px] w-[420px] rounded-full ${spotlight.seat.won > 0 ? "glow-in bg-[radial-gradient(closest-side,rgb(110_231_183/0.28),transparent)]" : "glow-turn bg-[radial-gradient(closest-side,rgb(254_249_195/0.2),transparent)]"}`}
            style={at(spotlight.point)}
          />
        )}

        {/* Marca del juego, estampada en el tapete. */}
        <div
          className={`${CENTERED} flex select-none flex-col items-center text-black/[0.13]`}
          style={at({ x: layout.center.x, y: layout.center.y - 4 })}
        >
          <Emblem className="h-28 w-28" />
          <span className="mt-1 text-3xl font-black tracking-[0.14em]">MI-POKER</span>
        </div>

        <div
          className={`${CENTERED} flex flex-col items-center`}
          style={at({ x: layout.center.x, y: layout.center.y - boardHeight / 2 - 34 })}
        >
          <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-white/75">
            Bote
          </span>
          <span
            data-zone="pot"
            className="rounded-full bg-black/55 px-4 py-0.5 text-lg font-black tabular-nums"
          >
            {frame.pot}
          </span>
        </div>

        <div
          data-zone="board"
          className={`${CENTERED} flex gap-2`}
          style={{ ...at(layout.center), ...cardWidth(layout.boardCard) }}
        >
          {frame.board.map((card) => (
            <PlayingCard key={card} card={card} enter="board" interactive="tilt" float={0.5} />
          ))}
          {emptySlots.map((_, index) => (
            <span key={index} className="card invisible inline-block" />
          ))}
        </div>

        {seats.map(({ seat, point }) => {
          const size = seat.isHuman ? layout.human : layout.bot;
          return (
            <div key={seat.seat}>
              <div className={CENTERED} style={at(betPoint(layout, point, size, seat.isHuman))}>
                <SeatBets seat={seat} />
              </div>
              <div className={CENTERED} style={at(point)} data-seat={seat.seat}>
                <SeatPlaque
                  seat={seat}
                  frame={frame}
                  size={size}
                  avatarSide={point.x < layout.center.x - 1 ? "right" : "left"}
                  thinking={settled && frame.actingSeat === seat.seat && !seat.isHuman}
                />
              </div>
            </div>
          );
        })}

        {/* Capa de efectos: por aquí cruzan las fichas y las cartas que se retiran. */}
        <div data-zone="fx" className="pointer-events-none absolute inset-0 z-40" />
      </div>
    </section>
  );
}
