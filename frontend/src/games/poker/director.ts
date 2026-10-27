// Acompaña la reproducción de la mano con las animaciones que cruzan la mesa:
// fichas del jugador al bote y del bote al ganador, y cartas que se retiran.
// Las piezas que vuelan son elementos sueltos en la capa de efectos de la mesa;
// las cartas que entran (reparto, flop...) se animan ellas mismas al dibujarse.

import type { PlaybackListener } from "./timeline/playback";
import type { HandEvent } from "./types";
import { EASE, JUICE, animate, motion, type Offset } from "../../shared/motion";
import { canvasOf, onTableAt, stageOf } from "../../shared/stage/measure";
import { hopFrames, slideFrames } from "../../shared/stage/physics";

const CHIP_MS = 400;
const CHIP_GAP_MS = 55; // entre una ficha y la siguiente
const MUCK_MS = 320;

function find(selector: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(selector);
}

/** Centro de un elemento en las coordenadas de la capa de efectos (que va escalada con la mesa). */
function pointIn(layer: HTMLElement, element: Element): Offset {
  const box = layer.getBoundingClientRect();
  const target = element.getBoundingClientRect();
  const scale = layer.offsetWidth > 0 ? box.width / layer.offsetWidth : 1;
  return {
    x: (target.left + target.width / 2 - box.left) / scale,
    y: (target.top + target.height / 2 - box.top) / scale,
  };
}

/** Varias fichas, una tras otra, de un punto de la mesa a otro, con un poco de arco. */
function slideChips(layer: HTMLElement, from: Offset, to: Offset, count: number): void {
  for (let index = 0; index < count; index++) {
    const chip = document.createElement("span");
    chip.className = "fx-chip";
    layer.append(chip);
    // Cada ficha sale y llega algo desplazada, para que no vayan en fila india.
    const jitter = () => (Math.random() - 0.5) * 16;
    const start = { x: from.x + jitter(), y: from.y + jitter() };
    const end = { x: to.x + jitter(), y: to.y + jitter() };
    const middle = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 - 22 };
    const place = (point: Offset, scale: number) =>
      `translate(${point.x}px, ${point.y}px) scale(${scale})`;
    const remove = () => chip.remove();
    animate(
      chip,
      [
        { transform: place(start, 0.6), opacity: 0 },
        { transform: place(start, 1), opacity: 1, offset: 0.12 },
        { transform: place(middle, 1.1), opacity: 1, offset: 0.55 },
        { transform: place(end, 0.9), opacity: 1, offset: 0.9 },
        { transform: place(end, 0.6), opacity: 0 },
      ],
      { duration: CHIP_MS, delay: index * CHIP_GAP_MS, fill: "both", easing: EASE.inOut },
    ).finished.then(remove, remove);
  }
}

function seatChips(seat: number | null): HTMLElement | null {
  return find(`[data-seat="${seat}"] [data-anchor="chips"]`);
}

function chipsToPot(seat: number | null, count: number): void {
  const layer = find('[data-zone="fx"]');
  const origin = seatChips(seat);
  const pot = find('[data-zone="pot"]');
  if (layer && origin && pot) slideChips(layer, pointIn(layer, origin), pointIn(layer, pot), count);
}

function chipsFromPot(seat: number | null, count: number): void {
  const layer = find('[data-zone="fx"]');
  const target = seatChips(seat);
  const pot = find('[data-zone="pot"]');
  if (layer && target && pot) slideChips(layer, pointIn(layer, pot), pointIn(layer, target), count);
}

/**
 * Fold en 3D: las cartas, tumbadas en el tapete, se deslizan hacia el centro
 * frenando por el rozamiento, giran un poco y se desvanecen.
 */
function muckCards3D(seat: number | null, layer: HTMLElement, center: HTMLElement): void {
  const canvas = canvasOf(layer);
  if (!canvas) return;
  const middle = onTableAt(canvas, center);
  for (const card of document.querySelectorAll<HTMLElement>(`[data-seat="${seat}"] .card-slot`)) {
    const at = onTableAt(canvas, card);
    const ghost = card.cloneNode(true) as HTMLElement;
    ghost.classList.add("fx-ghost");
    ghost.style.setProperty("--card-w", `${card.offsetWidth}px`);
    ghost.style.left = `${at.x - card.offsetWidth / 2}px`;
    ghost.style.top = `${at.y - card.offsetHeight / 2}px`;
    layer.append(ghost);
    const remove = () => ghost.remove();
    const to = { x: (middle.x - at.x) * 0.45, y: (middle.y - at.y) * 0.45 };
    animate(ghost, slideFrames(to, (Math.random() - 0.5) * 70), {
      duration: MUCK_MS + 80,
      fill: "both",
      easing: "linear",
    }).finished.then(remove, remove);
  }
}

/** Fold: las cartas del jugador se deslizan hacia el centro y se desvanecen. */
function muckCards(seat: number | null): void {
  const layer = find('[data-zone="fx"]');
  const center = find('[data-zone="board"]');
  if (!layer || !center) return;
  const table = find('[data-zone="fx-table"]');
  if (table && stageOf(table)) {
    muckCards3D(seat, table, center);
    return;
  }
  const middle = pointIn(layer, center);
  // La mesa todavía no se ha redibujado: las cartas siguen en su sitio. Se
  // deja una copia de cada una en la capa de efectos y es la copia la que se va.
  for (const card of document.querySelectorAll<HTMLElement>(`[data-seat="${seat}"] .card-slot`)) {
    const at = pointIn(layer, card);
    const ghost = card.cloneNode(true) as HTMLElement;
    ghost.classList.add("fx-ghost");
    ghost.style.setProperty("--card-w", `${card.offsetWidth}px`);
    ghost.style.left = `${at.x - card.offsetWidth / 2}px`;
    ghost.style.top = `${at.y - card.offsetHeight / 2}px`;
    layer.append(ghost);
    const remove = () => ghost.remove();
    const drift = `translate(${(middle.x - at.x) * 0.45}px, ${(middle.y - at.y) * 0.45}px)`;
    animate(
      ghost,
      [
        { transform: "translate(0px, 0px) rotate(0deg) scale(1)", opacity: 1 },
        { transform: `${drift} rotate(${(Math.random() - 0.5) * 50}deg) scale(0.8)`, opacity: 0 },
      ],
      { duration: MUCK_MS, fill: "both", easing: EASE.inOut },
    ).finished.then(remove, remove);
  }
}

/** Las cartas del ganador dan una sacudida (en 3D, un saltito sobre el tapete). */
function celebrate(seat: number | null): void {
  const cards = document.querySelectorAll(`[data-seat="${seat}"] .card-flight`);
  const lying = cards.length > 0 && stageOf(cards[0]) !== null;
  cards.forEach((layer, index) => {
    const delay = 180 + index * 90;
    if (lying) animate(layer, hopFrames(30), { duration: 460, delay, easing: "linear" });
    else animate(layer, JUICE, { duration: 420, delay, easing: EASE.out });
  });
}

function animateEvent(event: HandEvent): void {
  switch (event.kind) {
    case "small_blind":
    case "big_blind":
      chipsToPot(event.seat, 2);
      break;
    case "action":
      if (event.action === "fold") muckCards(event.seat);
      else if (event.action === "call") chipsToPot(event.seat, event.all_in ? 6 : 3);
      else if (event.action === "raise") chipsToPot(event.seat, event.all_in ? 7 : 4);
      break;
    case "refund":
      chipsFromPot(event.seat, 2);
      break;
    case "win":
      chipsFromPot(event.seat, 6);
      celebrate(event.seat);
      break;
  }
}

/** Animaciones de la mesa, enganchadas a la cola de reproducción. */
export const tableMotion: PlaybackListener = {
  onStep(step, speed) {
    // Las cartas leen esto al dibujarse: las del reparto vuelan desde el mazo, las
    // comunitarias giran hasta la mesa y en el showdown se voltean las tapadas.
    motion.entering = step.kind === "deal" || step.kind === "board" ? step.kind : null;
    motion.revealing = step.kind === "event" && step.event.kind === "show";
    motion.speed = speed;
    if (motion.enabled && step.kind === "event") animateEvent(step.event);
  },
  onJump() {
    // La mesa salta sin reproducir: nada debe entrar volando ni quedar a medias.
    motion.entering = null;
    motion.revealing = false;
    motion.speed = 1;
    find('[data-zone="fx"]')?.replaceChildren();
    find('[data-zone="fx-table"]')?.replaceChildren();
  },
};
