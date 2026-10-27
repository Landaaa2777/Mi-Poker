import { useLayoutEffect, useRef, useState, type CSSProperties, type PointerEvent } from "react";
import { audio } from "../audio/engine";
import { cardLabel } from "../format";
import { EASE, JUICE, animate, motion, offsetFrom } from "../motion";
import { animatePair, inTable3D } from "../stage/cardMotion";
import { offsetOnTable } from "../stage/measure";
import { flipFrames, hopFrames, throwFrames } from "../stage/physics";
import { CardFace, CompactFace } from "./CardFace";
import { Emblem } from "../components/Emblem";

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
  /** "full": la carta con todo su dibujo. "compact": solo valor y palo, para cartas pequeñas. */
  detail?: "full" | "compact";
  /** En 3D, la carta se sostiene un poco levantada hacia quien mira (mis cartas). */
  held?: boolean;
}

// Giro 3D de dorso a cara. La perspectiva va dentro del propio transform.
const FLIP: Keyframe[] = [
  { transform: "perspective(700px) rotateY(180deg)" },
  { transform: "perspective(700px) rotateY(0deg)" },
];

const FLIGHT_MS = 360; // del mazo a un jugador
const BOARD_MS = 440; // del mazo a la mesa, girando en el aire
const TURN_MS = 300; // voltear una carta

// En 3D las cartas se mueven con física (ver stage/physics): vuelan algo más,
// porque recorren un arco, aterrizan y frenan deslizando por el tapete.
const THROW_MS = 480; // del mazo a un jugador
const BOARD_THROW_MS = 560; // del mazo a la mesa, dándose la vuelta en el aire
const TURN_3D_MS = 340; // darle la vuelta a una carta que está en la mesa

/**
 * Una carta. Su tamaño lo fija quien la contiene con la variable CSS
 * `--card-w` (el ancho); el alto, las esquinas y la letra salen de ahí.
 *
 * Se mueve al estilo de Balatro, cada movimiento en su propia capa para que no
 * se pisen: flota en reposo, se inclina con el ratón, vuela desde el mazo y
 * gira en 3D. Solo se animan `transform` y `opacity`.
 */
export function PlayingCard({
  card,
  enter,
  interactive,
  float = 0,
  fan = 0,
  detail = "full",
  held = false,
}: Props) {
  const slot = useRef<HTMLSpanElement>(null);
  const tilt = useRef<HTMLSpanElement>(null);
  const flight = useRef<HTMLSpanElement>(null);
  const sides = useRef<HTMLSpanElement>(null);
  const shadow = useRef<HTMLSpanElement>(null);
  const shown = useRef(card);
  const [selected, setSelected] = useState(false);
  // Cada carta flota a su ritmo: empieza en un punto distinto del vaivén.
  const [phase] = useState(() => -Math.random() * 4);

  // Entrada: la carta llega volando desde el mazo.
  useLayoutEffect(() => {
    if (!motion.enabled || !enter || motion.entering !== enter) return;
    const deck = document.querySelector('[data-zone="deck"]');
    if (!deck || !slot.current || !flight.current || !sides.current) return;

    if (inTable3D(slot.current)) {
      // En 3D: lanzada desde el mazo con un arco, girando, y frena en el tapete.
      const width = slot.current.offsetWidth;
      const from = offsetOnTable(deck, slot.current);
      const board = enter === "board";
      const frames = throwFrames({
        from,
        height: board ? 70 : 46 + Math.random() * 14,
        spin: (Math.random() - 0.5) * (board ? 50 : 70),
        width,
        flip: board, // las comunitarias caen ya boca arriba
      });
      const duration = board ? BOARD_THROW_MS : THROW_MS;
      animatePair(flight.current, shadow.current, frames, { duration, easing: "linear" });
      // Mis cartas viajan boca abajo; al llegar se levantan por un borde y se voltean.
      if (!board && card !== null) {
        animatePair(sides.current, shadow.current?.firstElementChild ?? null, flipFrames(width), {
          duration: TURN_3D_MS,
          delay: duration - 40,
          fill: "backwards",
          easing: "linear",
        });
      }
      return;
    }

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
    if (before !== null || card === null || !motion.enabled || !motion.revealing) return;
    if (slot.current && sides.current && inTable3D(slot.current)) {
      // En 3D se levanta por un borde, gira y vuelve a caer en el tapete.
      animatePair(sides.current, shadow.current?.firstElementChild ?? null, flipFrames(slot.current.offsetWidth), {
        duration: 420,
        easing: "linear",
      });
      return;
    }
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
    if (!motion.enabled || !flight.current) return;
    if (slot.current && inTable3D(slot.current)) animate(flight.current, hopFrames(26), { duration: 420, easing: "linear" });
    else animate(flight.current, JUICE, { duration: 320, easing: EASE.out });
  }

  const style = {
    "--float": float,
    "--float-delay": `${phase.toFixed(2)}s`,
    "--fan": `${fan}deg`,
    "--lift": selected ? "-26%" : "0%",
  } as CSSProperties;

  return (
    <span
      ref={slot}
      className={`card-slot ${interactive ? "cursor-pointer" : ""} ${held ? "held" : ""} ${selected ? "selected" : ""}`}
      style={style}
      onPointerMove={interactive ? onPointerMove : undefined}
      onPointerLeave={interactive ? onPointerLeave : undefined}
      onClick={interactive === "select" ? onClick : undefined}
      aria-label={card === null ? "Carta boca abajo" : cardLabel(card)}
    >
      {/* Su sombra en el tapete (solo en 3D): se separa de la carta cuando esta se levanta. */}
      <span ref={shadow} className="card-shadow" aria-hidden>
        <span className="card-shadow-blob" />
      </span>
      <span className={`card-layer ${float > 0 ? "card-float" : ""}`}>
        <span ref={tilt} className="card-layer card-tilt">
          <span ref={flight} className="card-layer card-flight">
            <span className="card-layer card-pose">
              <span ref={sides} className={`card card-3d ${card === null ? "face-down" : ""}`}>
                <span className="card-side card-face select-none overflow-hidden">
                  {card !== null &&
                    (detail === "full" ? <CardFace card={card} /> : <CompactFace card={card} />)}
                  {/* Brillo de la cartulina: se mueve al inclinar la carta (solo en 3D). */}
                  <span className="card-gloss" aria-hidden />
                </span>
                {/* El canto: el grosor de la carta, que se ve al inclinarla (solo en 3D). */}
                <span className="card-edge" aria-hidden />
                <span className="card-side card-back">
                  <Emblem className="card-back-emblem" />
                </span>
              </span>
            </span>
          </span>
        </span>
      </span>
    </span>
  );
}
