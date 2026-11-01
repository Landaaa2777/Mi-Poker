import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { animatePair, inTable3D } from "../../shared/stage/cardMotion";
import { EASE, animate, motion, offsetFrom } from "../../shared/motion";
import { offsetOnTable } from "../../shared/stage/measure";
import { flipFrames, throwFrames, type ThrowFrames } from "../../shared/stage/physics";
import { CardBackArt, CardFaceArt } from "./cardArt";
import type { Card, Face } from "./types";

// Sitios de la mesa desde los que salen las cartas.
export const DECK_ZONE = '[data-zone="prisma-deck"]';
export const HAND_ZONE = '[data-zone="prisma-hand"]';
export const seatZone = (seat: number) => `[data-prisma-seat="${seat}"]`;

// Giro 3D de dorso a cara. La perspectiva va dentro del propio transform.
const FLIP: Keyframe[] = [
  { transform: "perspective(700px) rotateY(180deg)" },
  { transform: "perspective(700px) rotateY(0deg)" },
];
// Y de cara a dorso: la carta que se ve por detrás (Doble cara) se da la vuelta.
const FLIP_DOWN: Keyframe[] = [
  { transform: "perspective(700px) rotateY(0deg)" },
  { transform: "perspective(700px) rotateY(180deg)" },
];
const FLIGHT_MS = 380;
const TURN_MS = 300;
const ECLIPSE_MS = 420; // el Eclipse: la carta se da la vuelta en su sitio
const THROW_MS = 500; // en 3D: con arco, rebote y frenada en el tapete
const TURN_3D_MS = 340;

/** Los fotogramas de la física al revés: la carta acaba boca abajo. */
function reversed(frames: ThrowFrames): ThrowFrames {
  const flip = (list: Keyframe[]) =>
    [...list].reverse().map((frame) => ({ ...frame, offset: 1 - Number(frame.offset ?? 0) }));
  return { card: flip(frames.card), shadow: flip(frames.shadow) };
}

const signature = (face: Card | Face | null) => (face ? `${face.kind}|${face.color}|${face.number}` : "");

interface Props {
  card: Card | null; // null = boca abajo
  /** Cómo entra al aparecer durante la reproducción: "deal" desde el mazo, "play" hasta el descarte. */
  enter?: "deal" | "play";
  /** De dónde viene la carta: para "play", el sitio de quien la juega; para "deal", si no es el mazo. */
  from?: string;
  float?: number; // cuánto flota mientras está quieta (0 = nada)
  /** Doble cara: lo que hay en la otra cara (la que se ve de las cartas ajenas y del mazo). */
  back?: Face | null;
  /** Doble cara: la mesa está en la cara de sombra (la otra cara es, entonces, de luz). */
  night?: boolean;
}

/**
 * Una carta de Prisma. Su tamaño lo fija quien la contiene con `--card-w`.
 * Va en capas, como las cartas clásicas, para que los movimientos no se pisen:
 * flotación > vuelo > giro 3D con sus dos caras. Solo se animan transform y opacity.
 *
 * En Doble cara las dos caras de la carta tienen dibujo: lo que se ve al dorso es
 * la otra cara (`back`). Con el Eclipse, la carta se da la vuelta en su sitio:
 * por un momento, la cara que se ve antes del giro es la que había.
 */
export function PrismaCard({ card, enter, from, float = 0, back = null, night = false }: Props) {
  const slot = useRef<HTMLSpanElement>(null);
  const flight = useRef<HTMLSpanElement>(null);
  const sides = useRef<HTMLSpanElement>(null);
  const shadow = useRef<HTMLSpanElement>(null);

  // Al aparecer, vuela desde su origen (el mazo o quien la juega).
  useLayoutEffect(() => {
    if (!motion.enabled || !slot.current || !flight.current || !sides.current) return;
    if (motion.turning && !enter) return;
    if (motion.turning && enter === "play") {
      // La carta que el Eclipse deja arriba del descarte: se da la vuelta en su sitio.
      animate(sides.current, FLIP, { duration: ECLIPSE_MS, easing: EASE.back });
      return;
    }
    if (!enter || motion.entering !== enter) return;
    const origin = document.querySelector(from ?? DECK_ZONE);
    if (!origin) return;

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

  // Doble cara: si lo que se ve de la carta cambia porque se ha dado la vuelta
  // (el Eclipse), gira en su sitio. La cara que había se pinta un momento en el
  // lado que queda escondido, para que el giro la lleve de una a otra.
  const visible = card ?? back;
  const key = signature(visible);
  const seen = useRef({ key, face: visible });
  const [ghost, setGhost] = useState<Card | Face | null>(null);
  useLayoutEffect(() => {
    if (seen.current.key === key) return;
    const before = seen.current.face;
    seen.current = { key, face: visible };
    if (!motion.enabled || !motion.turning || !before || !visible || !sides.current || !slot.current) {
      setGhost(null);
      return;
    }
    setGhost(before);
    const faceUp = card !== null;
    let turn: Animation;
    if (inTable3D(slot.current)) {
      const frames = flipFrames(slot.current.offsetWidth);
      turn = animatePair(sides.current, shadow.current?.firstElementChild ?? null, faceUp ? frames : reversed(frames), {
        duration: ECLIPSE_MS,
        easing: "linear",
      });
    } else {
      turn = animate(sides.current, faceUp ? FLIP : FLIP_DOWN, { duration: ECLIPSE_MS, easing: EASE.back });
    }
    turn.onfinish = () => setGhost(null);
    // Solo cuando cambia la cara: el resto de cosas no la hacen girar.
  }, [key]);

  // Lo que se pinta en cada lado. Boca arriba, la cara va delante; boca abajo, se
  // ve el dorso (o la otra cara, en Doble cara).
  const front = card ?? (ghost && card === null ? ghost : null);
  const behind = back ?? (ghost && card !== null ? ghost : null);
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
                {front && <CardFaceArt card={front} dark={night} />}
                <span className="card-gloss" aria-hidden />
              </span>
              <span className="card-edge" aria-hidden />
              <span className="card-side prisma-back overflow-hidden">
                {behind && (card === null || ghost) ? <CardFaceArt card={behind} dark={!night} /> : <CardBackArt />}
              </span>
            </span>
          </span>
        </span>
      </span>
    </span>
  );
}
