// La cámara de la vista 3D: cómo se ve la mesa cuando el tapete se inclina
// hacia atrás. Son cuentas puras (sin el navegador) para poder probarlas.
//
// La mesa se dibuja siempre en un lienzo plano de W × H (el de la vista 2D).
// En 3D, ese lienzo es el tapete: se estira en profundidad (`stretch`) y se
// inclina `tilt` grados sobre su borde cercano, el de abajo. El navegador lo
// dibuja en perspectiva con la propiedad CSS `perspective`; aquí se repiten
// sus cuentas para saber dónde cae en la pantalla cada punto de la mesa (y al
// revés), y así colocar encima, planos, los nombres y los avisos.
//
// Al estirar el tapete en la misma proporción en que la inclinación lo acorta
// (1 / cos), las distancias en la mesa se ven casi como en 2D: lo que cambia
// es la perspectiva (lo lejano, más pequeño y más junto) y que lo que está
// tumbado en el tapete, como las cartas, se ve tumbado.

export interface Camera {
  tilt: number; // grados que se inclina el tapete hacia atrás
  distance: number; // distancia del ojo a la pantalla (perspectiva), en px del lienzo
  eye: number; // a qué altura mira el ojo, en partes del alto de la mesa (0 = borde cercano)
  top: number; // margen por encima del borde lejano, en px del lienzo
  bottom: number; // margen por debajo del borde cercano (el canto de la mesa)
}

export interface Point {
  x: number;
  y: number;
}

/** Un punto de la mesa visto en la pantalla: dónde cae y a qué escala se ve. */
export interface Projected extends Point {
  depth: number; // 1 en el borde cercano; menos de 1 cuanto más lejos
}

/** Todo lo que hace falta para dibujar y medir una mesa en 3D. */
export interface Stage3D {
  width: number; // ancho del lienzo
  height: number; // alto del lienzo 2D
  stageHeight: number; // alto que ocupa la mesa ya inclinada, con sus márgenes
  planeHeight: number; // alto del tapete estirado
  planeTop: number; // dónde empieza el tapete en el lienzo, antes de inclinarlo
  base: number; // dónde queda el borde cercano en el lienzo
  stretch: number;
  tilt: number; // en grados
  distance: number;
  originY: number; // punto de fuga (perspective-origin), en px del lienzo
}

const radians = (degrees: number) => (degrees * Math.PI) / 180;

/** Escala de la perspectiva a una altura `y` del lienzo 2D (0 arriba, H abajo). */
function depthAt(stage: Stage3D, y: number): number {
  const lift = (stage.height - y) * Math.tan(radians(stage.tilt)); // cuánto se aleja
  return stage.distance / (stage.distance + lift);
}

/** Las medidas de la mesa en 3D para un lienzo de `width` × `height`. */
export function stageFor(width: number, height: number, camera: Camera): Stage3D {
  const stretch = 1 / Math.cos(radians(camera.tilt));
  const eye = camera.eye * height;
  const partial = { width, height, tilt: camera.tilt, distance: camera.distance } as Stage3D;
  // El borde lejano (y = 0) sube hasta aquí desde el cercano, ya en perspectiva.
  const rise = eye + (height - eye) * depthAt(partial, 0);
  const base = camera.top + rise;
  return {
    ...partial,
    stretch,
    stageHeight: base + camera.bottom,
    planeHeight: height * stretch,
    planeTop: base - height * stretch,
    base,
    originY: base - eye,
  };
}

/** Dónde cae en el tapete estirado un punto del lienzo 2D. */
export function onPlane(stage: Stage3D, point: Point): Point {
  return { x: point.x, y: point.y * stage.stretch };
}

/** Dónde se ve en el lienzo (y a qué escala) un punto del lienzo 2D, ya en 3D. */
export function project(stage: Stage3D, point: Point): Projected {
  const depth = depthAt(stage, point.y);
  const eye = stage.base - stage.originY;
  const up = stage.height - point.y; // altura sobre el borde cercano, sin perspectiva
  return {
    x: stage.width / 2 + (point.x - stage.width / 2) * depth,
    y: stage.base - eye - (up - eye) * depth,
    depth,
  };
}

/**
 * Al revés que `project`: qué punto del lienzo 2D se ve en un punto del
 * lienzo 3D. Sirve para medir con el navegador dónde está algo en la mesa.
 */
export function unproject(stage: Stage3D, point: Point): Point {
  const tilt = radians(stage.tilt);
  const d = stage.distance;
  const eye = stage.base - stage.originY;
  const screenY = point.y - stage.base; // negativo por encima del borde cercano
  // Altura sobre el borde cercano dentro del tapete inclinado (negativa hacia el fondo).
  const along = (screenY * d) / (d * Math.cos(tilt) + (screenY + eye) * Math.sin(tilt));
  const depth = d / (d - along * Math.sin(tilt));
  return {
    x: stage.width / 2 + (point.x - stage.width / 2) / depth,
    y: stage.height + along / stage.stretch,
  };
}
