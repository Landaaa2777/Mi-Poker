// Medir dónde está algo en la mesa con el navegador, también en 3D.
//
// En 2D la mesa es un lienzo plano escalado: basta con deshacer la escala. En
// 3D, lo que se mide en la pantalla está en perspectiva: con la cámara de la
// mesa se averigua en qué punto del tapete cae. Así las cartas y las fichas
// saben de dónde tienen que salir para parecer que vienen del mazo o del bote.

import { onPlane, unproject, type Point, type Stage3D } from "./camera";

// Lienzo de cada mesa en 3D → sus medidas. Lo apunta el componente Stage.
const stages = new WeakMap<Element, Stage3D>();

export function registerStage(canvas: Element, stage: Stage3D): void {
  stages.set(canvas, stage);
}

/** El lienzo de la mesa a la que pertenece `element` (o la de la página, si no está en ninguna). */
export function canvasOf(element: Element): HTMLElement | null {
  return (
    element.closest<HTMLElement>("[data-canvas]") ?? document.querySelector<HTMLElement>("[data-canvas]")
  );
}

/** ¿Está la mesa de `element` en 3D? Devuelve sus medidas, o null si es plana. */
export function stageOf(element: Element): Stage3D | null {
  const canvas = canvasOf(element);
  return canvas ? (stages.get(canvas) ?? null) : null;
}

function center(element: Element): Point {
  const box = element.getBoundingClientRect();
  return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
}

/** Un punto de la pantalla en las unidades del lienzo (que va escalado entero). */
function inCanvas(canvas: HTMLElement, point: Point): Point {
  const box = canvas.getBoundingClientRect();
  const scale = canvas.offsetWidth > 0 ? box.width / canvas.offsetWidth : 1;
  return { x: (point.x - box.left) / scale, y: (point.y - box.top) / scale };
}

/**
 * Centro de `element` en el lienzo de `canvas`, tal como se ve: en 3D, ya en
 * perspectiva. Es donde hay que poner algo plano (una ficha que vuela) encima.
 */
export function seenAt(canvas: HTMLElement, element: Element): Point {
  return inCanvas(canvas, center(element));
}

/**
 * Centro de `element` sobre el tapete de la mesa de `canvas`: en 3D, el punto
 * del tapete estirado (el sistema de coordenadas de lo que está tumbado en él).
 */
export function onTableAt(canvas: HTMLElement, element: Element): Point {
  const seen = seenAt(canvas, element);
  const stage = stages.get(canvas);
  return stage ? onPlane(stage, unproject(stage, seen)) : seen;
}

/**
 * De dónde tiene que salir `target` para parecer que viene de `origin`: el
 * vector entre sus centros en las unidades en que se mueve `target`. En 3D,
 * medido sobre el tapete, porque `target` está tumbado en él.
 */
export function offsetOnTable(origin: Element, target: HTMLElement): Point {
  const canvas = canvasOf(target);
  if (!canvas) return { x: 0, y: 0 };
  const from = onTableAt(canvas, origin);
  const to = onTableAt(canvas, target);
  return { x: from.x - to.x, y: from.y - to.y };
}

/** Escala a la que se ve, por la perspectiva, lo que está en el punto de pantalla de `element`. */
export function depthOf(canvas: HTMLElement, element: Element): number {
  const stage = stages.get(canvas);
  if (!stage) return 1;
  const point = unproject(stage, seenAt(canvas, element));
  const lift = (stage.height - point.y) * Math.tan((stage.tilt * Math.PI) / 180);
  return stage.distance / (stage.distance + lift);
}
