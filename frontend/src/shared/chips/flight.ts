// Fichas que cruzan la mesa: del jugador a su apuesta, de las apuestas al
// bote, del bote al ganador, del crupier a la mano que gana...
//
// Las que vuelan son copias sueltas en la capa de efectos plana de la mesa
// (encima de todo), en las unidades del lienzo. En 3D se ven más pequeñas
// cuanto más lejos están, y suben más en el arco. Solo transform y opacity.

import { EASE, animate } from "../motion";
import { canvasOf, depthOf, seenAt, stageOf } from "../stage/measure";
import type { Denomination } from "./chips";

const FLY_MS = 420; // una ficha, de su origen a su destino
const GAP_MS = 45; // entre una ficha y la siguiente
const SLIDE_MS = 480; // una pila entera deslizándose por el tapete
const MOST = 8; // fichas que vuelan como mucho (las demás se dan por llegadas)

interface Point {
  x: number;
  y: number;
}

/** La capa de efectos de la mesa a la que pertenece `element`. */
function fxLayer(canvas: HTMLElement): HTMLElement | null {
  return canvas.querySelector<HTMLElement>(':scope > [data-zone="fx"]');
}

/** A qué escala se ve `element` en el lienzo: en 3D, lo lejano se ve más pequeño. */
function seenScale(canvas: HTMLElement, element: Element): number {
  const box = element.getBoundingClientRect();
  const width = (element as HTMLElement).offsetWidth;
  const canvasScale = canvas.offsetWidth > 0 ? canvas.getBoundingClientRect().width / canvas.offsetWidth : 1;
  return width > 0 && canvasScale > 0 ? box.width / width / canvasScale : depthOf(canvas, element);
}

const place = (point: Point, scale: number) =>
  `translate(${point.x.toFixed(1)}px, ${point.y.toFixed(1)}px) scale(${scale.toFixed(3)})`;

/**
 * Unas cuantas fichas vuelan, una tras otra, de `from` a `to`, con un poco de
 * arco. Devuelve cuándo llega la última (ms), para que la pila de destino las
 * reciba entonces.
 */
export function flyChips(
  from: Element,
  to: Element,
  chips: readonly Denomination[],
  size: number,
  delay = 0, // ms antes de salir (por ejemplo, a que se recojan las apuestas)
): number {
  const canvas = canvasOf(to);
  const layer = canvas && fxLayer(canvas);
  if (!canvas || !layer || chips.length === 0) return 0;
  const start = seenAt(canvas, from);
  const end = seenAt(canvas, to);
  const near = depthOf(canvas, from);
  const far = seenScale(canvas, to);
  const deep = stageOf(canvas) !== null;
  const flying = chips.slice(-MOST);
  flying.forEach((value, index) => {
    const chip = document.createElement("span");
    chip.className = "chip fx-chip-flying";
    chip.dataset.v = String(value);
    chip.style.setProperty("--chip-d", `${size}px`);
    layer.append(chip);
    // Cada ficha sale y llega algo desplazada, para que no vayan en fila india.
    const jitter = () => (Math.random() - 0.5) * size * 0.5;
    const from = { x: start.x + jitter(), y: start.y + jitter() };
    const middle = { x: (from.x + end.x) / 2, y: (from.y + end.y) / 2 - (deep ? 46 : 26) };
    const remove = () => chip.remove();
    animate(
      chip,
      [
        { transform: place(from, near * 0.7), opacity: 0 },
        { transform: place(from, near), opacity: 1, offset: 0.12 },
        { transform: place(middle, (near + far) / 2 * 1.08), opacity: 1, offset: 0.55 },
        { transform: place(end, far), opacity: 1, offset: 0.92 },
        { transform: place(end, far), opacity: 0 },
      ],
      { duration: FLY_MS, delay: delay + index * GAP_MS, fill: "both", easing: EASE.inOut },
    ).finished.then(remove, remove);
  });
  return delay + FLY_MS * 0.9 + (flying.length - 1) * GAP_MS;
}

/**
 * Una pila entera se desliza por el tapete hasta `to` (las apuestas al bote,
 * el bote al ganador...) y allí se funde con lo que haya. Se mueve una copia:
 * la mesa todavía no se ha redibujado. Devuelve cuándo llega (ms).
 */
export function slidePile(pile: Element, to: Element, delay = 0): number {
  const canvas = canvasOf(to);
  const layer = canvas && fxLayer(canvas);
  if (!canvas || !layer || !(pile instanceof HTMLElement) || pile.offsetWidth === 0) return 0;
  const start = seenAt(canvas, pile);
  const end = seenAt(canvas, to);
  const near = seenScale(canvas, pile);
  const far = seenScale(canvas, to);
  const ghost = pile.cloneNode(true) as HTMLElement;
  ghost.removeAttribute("data-pile");
  ghost.classList.add("fx-pile");
  ghost.style.left = `${-pile.offsetWidth / 2}px`;
  ghost.style.top = `${-pile.offsetHeight / 2}px`;
  layer.append(ghost);
  // Frena al final, como algo que se arrastra por el paño, y da un pequeño salto al juntarse.
  const frames: Keyframe[] = Array.from({ length: 14 }, (_, index) => {
    const time = index / 13;
    const along = 1 - (1 - time) ** 2.4;
    const hop = Math.sin(Math.PI * time) * 10;
    const point = { x: start.x + (end.x - start.x) * along, y: start.y + (end.y - start.y) * along - hop };
    return {
      offset: time,
      transform: place(point, near + (far - near) * along),
      opacity: time > 0.82 ? 1 - (time - 0.82) / 0.18 : 1,
    };
  });
  const remove = () => ghost.remove();
  animate(ghost, frames, { duration: SLIDE_MS, delay, fill: "both", easing: "linear" }).finished.then(remove, remove);
  return delay + SLIDE_MS * 0.82;
}
