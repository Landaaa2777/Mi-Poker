// Física de las cartas para la vista 3D.
//
// Un movimiento real no sigue una curva fija: la carta sale lanzada, el aire
// la frena, cae, rebota un poco y termina deslizando sobre el tapete hasta
// pararse. Aquí se simula ese movimiento paso a paso (60 veces por segundo) y
// se convierte en fotogramas clave para la API de animaciones del navegador.
// El navegador solo interpola entre ellos: todo va en `transform` (y la
// sombra, además, en `opacity`), así que corre a 60 fps sin trabajo extra.
//
// La simulación da la forma del movimiento; la distancia, la altura y la
// duración se ajustan después a cada carta.

export interface Vector {
  x: number;
  y: number;
}

/** Un instante de la trayectoria, con todo normalizado: avance de 0 a 1 y altura de 0 a 1. */
export interface Sample {
  time: number; // de 0 a 1
  along: number; // parte del camino recorrida, de 0 a 1
  height: number; // altura sobre el tapete, de 0 (apoyada) a 1 (lo más alto del arco)
  air: number; // 1 mientras vuela, 0 apoyada; para el aleteo
}

const STEP = 1 / 60; // la simulación va a 60 pasos por segundo
const GRAVITY = 9.8;
const AIR_DRAG = 1.6; // cuánto frena el aire lo que avanza
const FRICTION = 7; // cuánto frena el tapete al deslizar
const BOUNCE = 0.28; // qué parte de la velocidad conserva al rebotar
const LAUNCH = { forward: 4.2, up: 2.2 }; // velocidades de salida

/**
 * La trayectoria de una carta lanzada sobre la mesa: vuela, rebota y desliza
 * hasta pararse. Siempre es la misma forma: se calcula una vez.
 */
function simulate(): Sample[] {
  let along = 0;
  let height = 0.02;
  let forward = LAUNCH.forward;
  let up = LAUNCH.up;
  let peak = 0;
  const raw: { along: number; height: number; air: number }[] = [];
  for (let tick = 0; tick < 600; tick++) {
    raw.push({ along, height, air: height > 0 ? 1 : 0 });
    if (height > 0 || up > 0) {
      // En el aire: cae y el aire la frena.
      up -= GRAVITY * STEP;
      forward -= forward * AIR_DRAG * STEP;
      height += up * STEP;
      if (height <= 0) {
        height = 0;
        up = -up * BOUNCE;
        if (up < 0.35) up = 0; // el rebote ya no la levanta
      }
    } else {
      // En el tapete: el rozamiento la va parando.
      forward = Math.max(0, forward - FRICTION * STEP);
    }
    along += forward * STEP;
    peak = Math.max(peak, height);
    if (forward === 0 && height === 0) break;
  }
  raw.push({ along, height: 0, air: 0 });
  const total = along;
  const last = raw.length - 1;
  return raw.map((sample, index) => ({
    time: index / last,
    along: sample.along / total,
    height: sample.height / peak,
    air: sample.air,
  }));
}

const THROW = simulate();

/** La trayectoria de un lanzamiento, reducida a `count` muestras repartidas en el tiempo. */
export function throwPath(count = 28): Sample[] {
  return Array.from({ length: count }, (_, index) => {
    const time = index / (count - 1);
    const position = time * (THROW.length - 1);
    const before = THROW[Math.floor(position)];
    const after = THROW[Math.min(THROW.length - 1, Math.ceil(position))];
    const mix = position - Math.floor(position);
    return {
      time,
      along: before.along + (after.along - before.along) * mix,
      height: before.height + (after.height - before.height) * mix,
      air: mix < 0.5 ? before.air : after.air,
    };
  });
}

/** Cuándo toca el tapete por primera vez, de 0 a 1. */
export function landingTime(): number {
  const index = THROW.findIndex((sample, i) => i > 0 && sample.height === 0);
  return THROW[index].time;
}

export interface ThrowOptions {
  from: Vector; // de dónde sale, respecto a donde acaba (en px del tapete)
  height: number; // altura máxima del arco, en px
  spin: number; // giro inicial sobre el tapete, en grados (acaba en 0)
  width: number; // ancho de la carta: al voltearse en el aire no debe tocar el tapete
  flip?: boolean; // se da la vuelta en el aire y cae boca arriba
  start?: number; // escala al salir (las cartas salen del mazo algo más pequeñas)
}

export interface ThrowFrames {
  card: Keyframe[];
  shadow: Keyframe[];
}

const LIGHT = { x: 0.35, y: 0.55 }; // la luz viene de arriba: la sombra cae hacia abajo y a la derecha

/** Altura mínima para girar `angle` grados sobre el eje vertical sin atravesar el tapete. */
export function clearance(width: number, angle: number): number {
  return (width / 2 + 2) * Math.abs(Math.sin((angle * Math.PI) / 180));
}

/**
 * Fotogramas de una carta lanzada desde `from` hasta su sitio: la carta y su
 * sombra sobre el tapete. La carta acaba exactamente en su sitio (transform
 * vacío) y la sombra, pegada a ella.
 */
export function throwFrames({ from, height, spin, width, flip = false, start = 0.9 }: ThrowOptions): ThrowFrames {
  const path = throwPath();
  const land = landingTime();
  const card: Keyframe[] = [];
  const shadow: Keyframe[] = [];
  for (const sample of path) {
    const left = 1 - sample.along;
    const x = from.x * left;
    const y = from.y * left;
    const turn = spin * left; // gira mientras avanza y se para con ella
    // Aleteo en el aire: se balancea un poco y se calma al caer.
    const flutter = sample.air * Math.sin(sample.time * Math.PI * 5) * (1 - sample.time) * 7;
    // Al voltearse, gira de 180° a 0° mientras vuela, y termina antes de tocar el tapete.
    const turnover = flip ? 180 * (1 - smooth(Math.min(1, sample.time / (land * 0.92)))) : 0;
    const sideways = turnover - flutter * 0.6;
    // Lo bastante alta para que ni el giro ni el balanceo la metan en el tapete.
    const tipped = clearance(width, sideways) + clearance(width * 1.4, flutter);
    const lift = Math.max(sample.height * height, tipped);
    const grow = start + (1 - start) * Math.min(1, sample.time / 0.35);
    card.push({
      offset: sample.time,
      transform:
        `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, ${lift.toFixed(2)}px) ` +
        `rotateZ(${turn.toFixed(2)}deg) rotateX(${flutter.toFixed(2)}deg) ` +
        `rotateY(${sideways.toFixed(2)}deg) scale(${grow.toFixed(3)})`,
      opacity: sample.time < 0.08 ? sample.time / 0.08 : 1,
    });
    shadow.push({
      offset: sample.time,
      transform:
        `translate(${(x + lift * LIGHT.x).toFixed(2)}px, ${(y + lift * LIGHT.y).toFixed(2)}px) ` +
        `rotate(${turn.toFixed(2)}deg) scale(${(grow * (1 + lift / 160)).toFixed(3)})`,
      opacity: (sample.time < 0.08 ? sample.time / 0.08 : 1) * (1 - Math.min(0.75, lift / 140)),
    });
  }
  return { card, shadow };
}

/** Curva suave de 0 a 1 (empieza y acaba despacio). */
function smooth(value: number): number {
  return value * value * (3 - 2 * value);
}

/**
 * Darle la vuelta a una carta que está en el tapete: se levanta por un borde,
 * gira y vuelve a caer con un rebote pequeño. `from` es 180 (boca abajo) y
 * acaba en 0 (boca arriba).
 */
export function flipFrames(width: number, count = 22): ThrowFrames {
  const card: Keyframe[] = [];
  const shadow: Keyframe[] = [];
  for (let index = 0; index < count; index++) {
    const time = index / (count - 1);
    // Se levanta y gira deprisa; al caer plana da un rebote pequeño.
    const turned = Math.min(1, time / 0.72);
    const turn = 180 * (1 - smooth(turned));
    const bump = time < 0.72 ? Math.sin((Math.PI * time) / 0.72) * 6 : Math.sin(((time - 0.72) / 0.28) * Math.PI) * 2;
    const lift = clearance(width, turn) + bump;
    card.push({
      offset: time,
      transform: `translateZ(${lift.toFixed(2)}px) rotateY(${turn.toFixed(2)}deg)`,
    });
    shadow.push({
      offset: time,
      transform: `translate(${(lift * LIGHT.x).toFixed(2)}px, ${(lift * LIGHT.y).toFixed(2)}px) scaleX(${Math.max(0.08, Math.abs(Math.cos((turn * Math.PI) / 180))).toFixed(3)})`,
      opacity: 1 - Math.min(0.6, lift / 120),
    });
  }
  return { card, shadow };
}

/** Muelle amortiguado de 0 a 1: se pasa un poco y vuelve, como algo que cae y se asienta. */
export function settle(time: number): number {
  if (time <= 0) return 0;
  if (time >= 1) return 1;
  return 1 - Math.exp(-6 * time) * Math.cos(time * Math.PI * 2.4);
}

/**
 * Deslizar algo por el tapete hasta `to` frenando por el rozamiento, girando
 * un poco y desvaneciéndose: así se retiran las cartas al tirarlas.
 */
export function slideFrames(to: Vector, spin: number, count = 16): Keyframe[] {
  return Array.from({ length: count }, (_, index) => {
    const time = index / (count - 1);
    const along = 1 - (1 - time) * (1 - time); // frenada constante: recorre deprisa y se para
    return {
      offset: time,
      transform: `translate3d(${(to.x * along).toFixed(2)}px, ${(to.y * along).toFixed(2)}px, ${(Math.sin(Math.PI * time) * 4).toFixed(2)}px) rotateZ(${(spin * along).toFixed(2)}deg)`,
      opacity: time < 0.55 ? 1 : Math.max(0, Number((1 - (time - 0.55) / 0.45).toFixed(3))),
    };
  });
}

/** Un saltito en su sitio: el ganador levanta sus cartas un momento. */
export function hopFrames(height: number, count = 18): Keyframe[] {
  return Array.from({ length: count }, (_, index) => {
    const time = index / (count - 1);
    // Sube y cae como un objeto lanzado hacia arriba, con un rebote final.
    const rise = time < 0.7 ? 4 * (time / 0.7) * (1 - time / 0.7) : 0.18 * Math.sin(((time - 0.7) / 0.3) * Math.PI);
    return {
      offset: time,
      transform: `translateZ(${(rise * height).toFixed(2)}px) rotateZ(${(Math.sin(time * Math.PI * 2) * (1 - time) * 3).toFixed(2)}deg)`,
    };
  });
}
