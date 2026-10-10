// Base de las animaciones. Todas mueven solo `transform` y `opacity`, con la
// API de animaciones del navegador, y duran entre 200 y 500 ms.

import type { Step } from "../timeline/steps";

/**
 * Estado compartido: lo fija la reproducción justo antes de dibujar cada paso
 * y lo leen las piezas de la mesa al dibujarse, para saber si deben animarse.
 */
export const motion = {
  enabled: false, // animaciones activadas (ajustes y movimiento reducido del sistema)
  step: null as Step | null, // paso que se está dibujando; null si la mesa saltó sin reproducir
  speed: 1, // mayor que 1 cuando la cola va atrasada
};

export const EASE = {
  out: "cubic-bezier(0.22, 1, 0.36, 1)", // sale rápido y frena con suavidad
  back: "cubic-bezier(0.34, 1.56, 0.64, 1)", // se pasa un poco y vuelve: el rebote
  inOut: "cubic-bezier(0.65, 0, 0.35, 1)",
};

/** Sacudida corta: la pieza crece, se tuerce un poco y vuelve a su sitio. */
export const JUICE: Keyframe[] = [
  { transform: "scale(1) rotate(0deg)" },
  { transform: "scale(1.16) rotate(-4deg)", offset: 0.3 },
  { transform: "scale(0.96) rotate(2.5deg)", offset: 0.62 },
  { transform: "scale(1) rotate(0deg)" },
];

/** Lanza una animación, más deprisa si la cola de pasos va atrasada. */
export function animate(
  element: Element,
  keyframes: Keyframe[],
  options: KeyframeAnimationOptions,
): Animation {
  const animation = element.animate(keyframes, options);
  animation.playbackRate = motion.speed;
  return animation;
}

export interface Offset {
  x: number;
  y: number;
}

/**
 * De dónde tiene que salir `target` para parecer que viene de `origin`: el
 * vector entre sus centros, en las unidades de `target`. La mesa se dibuja
 * escalada, así que los píxeles de pantalla se convierten a los suyos.
 */
export function offsetFrom(origin: Element, target: HTMLElement): Offset {
  const from = origin.getBoundingClientRect();
  const to = target.getBoundingClientRect();
  const scale = target.offsetWidth > 0 ? to.width / target.offsetWidth : 1;
  return {
    x: (from.left + from.width / 2 - (to.left + to.width / 2)) / scale,
    y: (from.top + from.height / 2 - (to.top + to.height / 2)) / scale,
  };
}
