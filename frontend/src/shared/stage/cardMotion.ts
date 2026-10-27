// Piezas comunes de las cartas que se mueven en una mesa 3D (las clásicas y las de Prisma).

import { animate } from "../motion";

/** ¿Está la carta tumbada en una mesa en 3D? */
export function inTable3D(element: Element): boolean {
  return element.closest("[data-plane]") !== null;
}

/** Lanza a la vez los fotogramas de una carta y los de su sombra en el tapete. */
export function animatePair(
  card: Element,
  shadow: Element | null,
  frames: { card: Keyframe[]; shadow: Keyframe[] },
  options: KeyframeAnimationOptions,
): Animation {
  if (shadow) animate(shadow, frames.shadow, options);
  return animate(card, frames.card, options);
}
