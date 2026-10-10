import { useLayoutEffect, useRef, useState, type CSSProperties, type PointerEvent } from "react";
import { audio } from "../audio/engine";
import { cardLabel, cardRank } from "../format";
import { EASE, JUICE, animate, motion, offsetFrom } from "../motion/motion";

interface Props {
  card: string | null; // null = boca abajo
  /** Cómo entra en la mesa cuando aparece durante la reproducción de una mano. */
  enter?: "deal" | "board";
  /** "tilt": se inclina al pasar el ratón. "select": además se levanta al pulsarla. */
  interactive?: "tilt" | "select";
  /** Cuánto flota mientras está quieta (0 = nada). */
  float?: number;
  /** Inclinación fija, en grados, para abrir las cartas en abanico. */
  fan?: number;
}

/** Palo dibujado como SVG propio, para que se vea igual en cualquier sistema. */
function Suit({ suit }: { suit: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-[0.95em] w-[0.95em]" fill="currentColor" aria-hidden>
      {suit === "h" && (
        <path d="M12 20.5C5 15.5 2 12 2 8.5 2 5.5 4.3 3.5 7 3.5c2 0 3.8 1.1 5 3 1.2-1.9 3-3 5-3 2.7 0 5 2 5 5 0 3.5-3 7-10 12z" />
      )}
      {suit === "d" && <path d="M12 2l8 10-8 10-8-10z" />}
      {suit === "s" && (
        <path d="M12 2.5c7 5.5 10 8.5 10 12 0 2.8-2.1 4.5-4.5 4.5-1.7 0-3.3-.8-4.3-2.2.3 2.2 1.1 3.8 2.3 4.7h-7c1.2-.9 2-2.5 2.3-4.7C9.8 18.2 8.2 19 6.5 19 4.1 19 2 17.3 2 14.5c0-3.5 3-6.5 10-12z" />
      )}
      {suit === "c" && (
        <>
          <circle cx="12" cy="7" r="4.6" />
          <circle cx="6.6" cy="14" r="4.6" />
          <circle cx="17.4" cy="14" r="4.6" />
          <path d="M12 11l-2.6 10.5h5.2z" />
        </>
      )}
    </svg>
  );
}

// Giro 3D de dorso a cara. La perspectiva va dentro del propio transform.
const FLIP: Keyframe[] = [
  { transform: "perspective(700px) rotateY(180deg)" },
  { transform: "perspective(700px) rotateY(0deg)" },
];

const FLIGHT_MS = 360; // del mazo a un jugador
const BOARD_MS = 440; // del mazo a la mesa, girando en el aire
const TURN_MS = 300; // voltear una carta

/**
 * Una carta. Su tamaño lo fija quien la contiene con la variable CSS
 * `--card-w` (el ancho); el alto, las esquinas y la letra salen de ahí.
 *
 * Se mueve al estilo de Balatro, cada movimiento en su propia capa para que no
 * se pisen: flota en reposo, se inclina con el ratón, vuela desde el mazo y
 * gira en 3D. Solo se animan `transform` y `opacity`.
 */
export function PlayingCard({ card, enter, interactive, float = 0, fan = 0 }: Props) {
  const slot = useRef<HTMLSpanElement>(null);
  const tilt = useRef<HTMLSpanElement>(null);
  const flight = useRef<HTMLSpanElement>(null);
  const sides = useRef<HTMLSpanElement>(null);
  const shown = useRef(card);
  const [selected, setSelected] = useState(false);
  // Cada carta flota a su ritmo: empieza en un punto distinto del vaivén.
  const [phase] = useState(() => -Math.random() * 4);

  // Entrada: la carta llega volando desde el mazo.
  useLayoutEffect(() => {
    if (!motion.enabled || !enter || motion.step?.kind !== enter) return;
    const deck = document.querySelector('[data-zone="deck"]');
    if (!deck || !slot.current || !flight.current || !sides.current) return;

    const from = offsetFrom(deck, slot.current);
    const start = `translate(${from.x}px, ${from.y}px) rotate(${(Math.random() - 0.5) * 36}deg) scale(0.72)`;
    // Mientras vuela pasa por encima de las placas de los demás jugadores.
    const seat = slot.current.closest<HTMLElement>("[data-seat]");
    if (seat) seat.style.zIndex = "20";
    const landed = () => {
      if (seat) seat.style.zIndex = "";
    };

    if (enter === "deal") {
      animate(
        flight.current,
        [
          { transform: start, opacity: 0 },
          { opacity: 1, offset: 0.18 },
          { transform: "translate(0px, 0px) rotate(0deg) scale(1.08)", opacity: 1, offset: 0.8 },
          { transform: "translate(0px, 0px) rotate(0deg) scale(1)", opacity: 1 },
        ],
        { duration: FLIGHT_MS, easing: EASE.out },
      ).finished.then(landed, landed);
      // Mis cartas viajan boca abajo y se voltean al llegar.
      if (card !== null) {
        animate(sides.current, FLIP, {
          duration: TURN_MS,
          delay: FLIGHT_MS - 80,
          fill: "backwards",
          easing: EASE.back,
        });
      }
    } else {
      // Carta comunitaria: gira en el aire y aterriza con un pequeño rebote.
      animate(
        flight.current,
        [
          { transform: start, opacity: 0 },
          { opacity: 1, offset: 0.15 },
          { transform: "translate(0px, 0px) rotate(0deg) scale(1.12)", opacity: 1, offset: 0.78 },
          { transform: "translate(0px, 0px) rotate(0deg) scale(1)", opacity: 1 },
        ],
        { duration: BOARD_MS, easing: EASE.out },
      ).finished.then(landed, landed);
      animate(sides.current, FLIP, {
        duration: TURN_MS,
        delay: 90,
        fill: "backwards",
        easing: EASE.inOut,
      });
    }
    // Solo al aparecer: una carta que ya está en la mesa no vuelve a volar.
  }, []);

  // Showdown: una carta que estaba boca abajo se voltea y da una sacudida.
  useLayoutEffect(() => {
    const before = shown.current;
    shown.current = card;
    if (before !== null || card === null || !motion.enabled) return;
    const step = motion.step;
    if (step?.kind !== "event" || step.event.kind !== "show") return;
    if (sides.current) animate(sides.current, FLIP, { duration: 380, easing: EASE.back });
    if (flight.current) animate(flight.current, JUICE, { duration: 380, easing: EASE.out });
  }, [card]);

  function onPointerMove(event: PointerEvent<HTMLSpanElement>) {
    if (!motion.enabled || event.pointerType !== "mouse" || !tilt.current) return;
    const box = event.currentTarget.getBoundingClientRect();
    tilt.current.classList.add("tracking");
    tilt.current.style.setProperty("--tilt-x", ((event.clientX - box.left) / box.width - 0.5).toFixed(3));
    tilt.current.style.setProperty("--tilt-y", ((event.clientY - box.top) / box.height - 0.5).toFixed(3));
    tilt.current.style.setProperty("--zoom", "1.08");
  }

  function onPointerLeave() {
    if (!tilt.current) return;
    tilt.current.classList.remove("tracking");
    for (const name of ["--tilt-x", "--tilt-y", "--zoom"]) tilt.current.style.removeProperty(name);
  }

  // Seleccionar una carta es solo un adorno: se levanta con un rebote. No cambia el juego.
  function onClick() {
    setSelected((current) => !current);
    audio.play("select");
    if (motion.enabled && flight.current) animate(flight.current, JUICE, { duration: 320, easing: EASE.out });
  }

  const red = card !== null && (card[1] === "h" || card[1] === "d");
  const style = {
    "--float": float,
    "--float-delay": `${phase.toFixed(2)}s`,
    "--fan": `${fan}deg`,
    "--lift": selected ? "-26%" : "0%",
  } as CSSProperties;

  return (
    <span
      ref={slot}
      className={`card-slot ${interactive ? "cursor-pointer" : ""}`}
      style={style}
      onPointerMove={interactive ? onPointerMove : undefined}
      onPointerLeave={interactive ? onPointerLeave : undefined}
      onClick={interactive === "select" ? onClick : undefined}
      aria-label={card === null ? "Carta boca abajo" : cardLabel(card)}
    >
      <span className={`card-layer ${float > 0 ? "card-float" : ""}`}>
        <span ref={tilt} className="card-layer card-tilt">
          <span ref={flight} className="card-layer">
            <span ref={sides} className={`card card-3d ${card === null ? "face-down" : ""}`}>
              <span
                className={`card-side card-face flex select-none flex-col items-center bg-white font-bold leading-none ${red ? "text-red-600" : "text-slate-900"}`}
              >
                {card !== null && (
                  <>
                    <span>{cardRank(card)}</span>
                    <Suit suit={card[1]} />
                  </>
                )}
              </span>
              <span className="card-side card-back" />
            </span>
          </span>
        </span>
      </span>
    </span>
  );
}
