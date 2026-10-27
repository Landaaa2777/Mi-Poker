import { useLayoutEffect, useRef, type CSSProperties } from "react";
import { animatePair, inTable3D } from "../../shared/stage/cardMotion";
import { EASE, animate, motion, offsetFrom } from "../../shared/motion";
import { offsetOnTable } from "../../shared/stage/measure";
import { flipFrames, throwFrames } from "../../shared/stage/physics";
import { CardBackArt, CardFaceArt } from "./cardArt";
import type { Card } from "./types";

// Sitios de la mesa desde los que salen las cartas.
export const DECK_ZONE = '[data-zone="prisma-deck"]';
export const HAND_ZONE = '[data-zone="prisma-hand"]';
export const seatZone = (seat: number) => `[data-prisma-seat="${seat}"]`;

// Giro 3D de dorso a cara. La perspectiva va dentro del propio transform.
const FLIP: Keyframe[] = [
  { transform: "perspective(700px) rotateY(180deg)" },
  { transform: "perspective(700px) rotateY(0deg)" },
];
const FLIGHT_MS = 380;
const TURN_MS = 300;
const THROW_MS = 500; // en 3D: con arco, rebote y frenada en el tapete
const TURN_3D_MS = 340;

interface Props {
  card: Card | null; // null = boca abajo
  /** Cómo entra al aparecer durante la reproducción: "deal" desde el mazo, "play" hasta el descarte. */
  enter?: "deal" | "play";
  /** Para "play": de dónde viene la carta (el sitio de quien la juega). */
  from?: string;
  float?: number; // cuánto flota mientras está quieta (0 = nada)
}

/**
 * Una carta de Prisma. Su tamaño lo fija quien la contiene con `--card-w`.
 * Va en capas, como las cartas clásicas, para que los movimientos no se pisen:
 * flotación > vuelo > giro 3D con sus dos caras. Solo se animan transform y opacity.
 */
export function PrismaCard({ card, enter, from, float = 0 }: Props) {
  const slot = useRef<HTMLSpanElement>(null);
  const flight = useRef<HTMLSpanElement>(null);
  const sides = useRef<HTMLSpanElement>(null);
  const shadow = useRef<HTMLSpanElement>(null);

  // Al aparecer, vuela desde su origen (el mazo o quien la juega).
  useLayoutEffect(() => {
    if (!motion.enabled || !enter || motion.entering !== enter) return;
    const origin = document.querySelector(enter === "deal" ? DECK_ZONE : (from ?? DECK_ZONE));
    if (!origin || !slot.current || !flight.current || !sides.current) return;

    if (inTable3D(slot.current)) {
      // En 3D, sobre el tapete: lanzada con arco y giro, frena deslizando. La que
      // se juega desde una mano ajena se da la vuelta en el aire.
      const width = slot.current.offsetWidth;
      const play = enter === "play";
      const flip = card !== null && play && from !== HAND_ZONE;
      const frames = throwFrames({
        from: offsetOnTable(origin, slot.current),
        height: play ? 64 : 40,
        spin: (Math.random() - 0.5) * (play ? 80 : 50),
        width,
        flip,
      });
      animatePair(flight.current, shadow.current, frames, { duration: THROW_MS, easing: "linear" });
      if (card !== null && !play) {
        animatePair(sides.current, shadow.current?.firstElementChild ?? null, flipFrames(width), {
          duration: TURN_3D_MS,
          delay: THROW_MS - 40,
          fill: "backwards",
          easing: "linear",
        });
      }
      return;
    }

    const offset = offsetFrom(origin, slot.current);
    const tilt = (Math.random() - 0.5) * 40;
    animate(
      flight.current,
      [
        { transform: `translate(${offset.x}px, ${offset.y}px) rotate(${tilt}deg) scale(0.8)`, opacity: 0 },
        { opacity: 1, offset: 0.15 },
        { transform: "translate(0px, 0px) rotate(0deg) scale(1.08)", opacity: 1, offset: 0.8 },
        { transform: "translate(0px, 0px) rotate(0deg) scale(1)", opacity: 1 },
      ],
      { duration: FLIGHT_MS, easing: EASE.out },
    );
    // Las mías (y la que se juega desde una mano ajena) se voltean por el camino.
    if (card !== null && (enter === "deal" || from !== HAND_ZONE)) {
      animate(sides.current, FLIP, {
        duration: TURN_MS,
        delay: enter === "deal" ? FLIGHT_MS - 80 : 60,
        fill: "backwards",
        easing: EASE.back,
      });
    }
    // Solo al aparecer: una carta que ya está en su sitio no vuelve a volar.
  }, []);

  return (
    <span ref={slot} className="card-slot" aria-hidden={card === null || undefined}>
      {/* Su sombra en el tapete (solo en 3D). */}
      <span ref={shadow} className="card-shadow" aria-hidden>
        <span className="card-shadow-blob" />
      </span>
      <span
        className={`card-layer ${float > 0 ? "card-float" : ""}`}
        style={{ "--float": float } as CSSProperties}
      >
        <span ref={flight} className="card-layer card-flight">
          <span className="card-layer card-pose">
            <span ref={sides} className={`card card-3d ${card === null ? "face-down" : ""}`}>
              <span className="card-side card-face select-none overflow-hidden">
                {card && <CardFaceArt card={card} />}
                <span className="card-gloss" aria-hidden />
              </span>
              <span className="card-edge" aria-hidden />
              <span className="card-side prisma-back overflow-hidden">
                <CardBackArt />
              </span>
            </span>
          </span>
        </span>
      </span>
    </span>
  );
}
