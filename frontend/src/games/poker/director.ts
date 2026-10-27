// Acompaña la reproducción de la mano con las animaciones que cruzan la mesa:
// fichas del jugador a su apuesta, de las apuestas al bote, del bote al
// ganador y de lo ganado a su placa; y cartas que se retiran. Las piezas que
// vuelan son copias sueltas en la capa de efectos de la mesa; las cartas que
// entran (reparto, flop...) y las fichas que llegan a una pila se animan ellas
// mismas al dibujarse.

import type { PlaybackListener } from "./timeline/playback";
import type { Frame } from "./timeline/frame";
import type { Step } from "./timeline/steps";
import type { HandEvent } from "./types";
import { tableChips } from "./chips";
import { total, type Denomination } from "../../shared/chips/chips";
import { flyChips, slidePile } from "../../shared/chips/flight";
import { EASE, JUICE, animate, motion, type Offset } from "../../shared/motion";
import { canvasOf, onTableAt, stageOf } from "../../shared/stage/measure";
import { hopFrames, slideFrames } from "../../shared/stage/physics";

const MUCK_MS = 320;
const CHIP_SIZE = 30; // las que vuelan

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

/** De dónde salen las fichas de un jugador y adónde llegan las que cobra: su avatar. */
function seatChips(seat: number | null): HTMLElement | null {
  return find(`[data-seat="${seat}"] [data-anchor="chips"]`);
}

/** Las fichas de `after` que no estaban en `before` (las de arriba de la pila). */
function added(before: readonly Denomination[], after: readonly Denomination[]): Denomination[] {
  return after.slice(before.length);
}

/**
 * Las fichas que se mueven entre lo dibujado (`before`) y el paso que va a
 * dibujarse. Devuelve cuándo llegan a su pila (ms), o null si no se mueve nada.
 */
function moveChips(before: Frame, step: Step): number | null {
  const was = tableChips(before);
  const now = tableChips(step.frame);
  const pot = find('[data-pile="pot"]');
  const potChips = find('[data-pile="pot-chips"]');
  let landing: number | null = null;
  const land = (ms: number) => (landing = Math.max(landing ?? 0, ms));
  const refund = step.kind === "event" && step.event.kind === "refund";
  let collected = 0; // cuándo acaban de llegar al bote las apuestas recogidas en este paso

  for (const seat of step.frame.seats) {
    const spot = find(`[data-pile="bet-${seat.seat}"]`);
    const plaque = seatChips(seat.seat);
    if (!spot || !plaque) continue;
    const betBefore = was.bets.get(seat.seat) ?? [];
    const betAfter = now.bets.get(seat.seat) ?? [];

    if (total(betAfter) > total(betBefore)) {
      // Apuesta: sus fichas van de su placa a su sitio en la mesa.
      land(flyChips(plaque, spot, added(betBefore, betAfter), CHIP_SIZE));
    } else if (total(betAfter) < total(betBefore)) {
      const pile = find(`[data-pile="bet-${seat.seat}-chips"]`);
      if (refund) flyChips(spot, plaque, betBefore.slice(betAfter.length), CHIP_SIZE);
      // Se cierra la ronda: su pila se desliza al bote.
      else if (pile && pot) collected = Math.max(collected, land(slidePile(pile, pot)));
    }
  }

  // El bote va a quien gana, después de recoger las apuestas que quedaran.
  for (const seat of step.frame.seats) {
    const spot = find(`[data-pile="bet-${seat.seat}"]`);
    const wonBefore = was.won.get(seat.seat) ?? [];
    const wonAfter = now.won.get(seat.seat) ?? [];
    if (!spot || !pot || total(wonAfter) <= total(wonBefore)) continue;
    // Entero, si el bote se queda vacío y ya tenía fichas; si no, unas cuantas.
    if (now.pot.length === 0 && potChips) land(slidePile(potChips, spot, collected));
    else land(flyChips(pot, spot, added(wonBefore, wonAfter), CHIP_SIZE, collected));
  }

  for (const seat of step.frame.seats) {
    const plaque = seatChips(seat.seat);
    const wonBefore = was.won.get(seat.seat) ?? [];
    if (step.kind === "new_hand" && wonBefore.length > 0 && plaque) {
      // Mano nueva: lo que ganó en la anterior se lo lleva a su sitio.
      const pile = find(`[data-pile="won-${seat.seat}"]`);
      if (pile) slidePile(pile, plaque);
    }
  }
  return landing;
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
  if (event.kind === "action" && event.action === "fold") muckCards(event.seat);
  if (event.kind === "win") celebrate(event.seat);
}

let shown: Frame | null = null; // lo último que se ha dibujado, para ver qué cambia en cada paso

/** Animaciones de la mesa, enganchadas a la cola de reproducción. */
export const tableMotion: PlaybackListener = {
  onStep(step, speed) {
    // Las cartas leen esto al dibujarse: las del reparto vuelan desde el mazo, las
    // comunitarias giran hasta la mesa y en el showdown se voltean las tapadas.
    motion.entering = step.kind === "deal" || step.kind === "board" ? step.kind : null;
    motion.revealing = step.kind === "event" && step.event.kind === "show";
    motion.speed = speed;
    motion.chipLanding = 0;
    if (motion.enabled) {
      // La cola acelerada también acelera la caída de las fichas (playbackRate).
      if (shown) motion.chipLanding = moveChips(shown, step) ?? 0;
      if (step.kind === "event") animateEvent(step.event);
    }
    shown = step.frame;
  },
  onJump() {
    // La mesa salta sin reproducir: nada debe entrar volando ni quedar a medias.
    motion.entering = null;
    motion.revealing = false;
    motion.speed = 1;
    motion.chipLanding = null;
    shown = null;
    find('[data-zone="fx"]')?.replaceChildren();
    find('[data-zone="fx-table"]')?.replaceChildren();
  },
};
