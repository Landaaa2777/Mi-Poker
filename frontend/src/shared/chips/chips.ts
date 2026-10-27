// Fichas de la mesa: qué fichas forman una cantidad y cómo se apilan.
//
// Son cuentas puras, sin dibujo, para poder probarlas. Las fichas no valen
// nada fuera del juego: es solo la forma de enseñar las apuestas y el bote.

/** Valores de las fichas, de mayor a menor. Cada uno tiene su color (ver tokens.css). */
export const DENOMINATIONS = [5000, 1000, 500, 100, 25, 5, 1] as const;
export type Denomination = (typeof DENOMINATIONS)[number];

/** Las fichas de una cantidad, de mayor a menor valor, con las menos fichas posibles. */
export function breakdown(amount: number): Denomination[] {
  const chips: Denomination[] = [];
  let left = Math.max(0, Math.floor(amount));
  for (const value of DENOMINATIONS) {
    while (left >= value) {
      chips.push(value);
      left -= value;
    }
  }
  return chips;
}

export function total(chips: readonly Denomination[]): number {
  return chips.reduce((sum, chip) => sum + chip, 0);
}

/**
 * Las fichas que hay en la mesa tras varias aportaciones (una apuesta, otra
 * subida...): cada una se pone con sus propias fichas, sin cambiarlas, como en
 * una mesa de verdad. Así la pila crece a la vista con cada apuesta. Si se
 * juntan demasiadas, se cambian por fichas de más valor.
 */
export function pile(amounts: readonly number[], most = 40): Denomination[] {
  const chips = amounts.flatMap((amount) => breakdown(amount));
  return chips.length > most ? breakdown(total(chips)) : chips;
}

/**
 * Cambia fichas pequeñas por las de más valor, como hace el crupier con el
 * bote: cinco de 5 por una de 25, cuatro de 25 por una de 100... La cantidad
 * no cambia y las pilas no crecen sin control.
 */
export function colorUp(chips: readonly Denomination[]): Denomination[] {
  const counts = new Map<Denomination, number>(DENOMINATIONS.map((value) => [value, 0]));
  for (const chip of chips) counts.set(chip, (counts.get(chip) ?? 0) + 1);
  const ascending = [...DENOMINATIONS].reverse();
  ascending.forEach((value, index) => {
    const bigger = ascending[index + 1];
    if (!bigger) return;
    const needed = bigger / value; // cuántas de estas hacen una de la siguiente
    const count = counts.get(value) ?? 0;
    if (count < needed) return;
    const swaps = Math.floor(count / needed);
    counts.set(value, count - swaps * needed);
    counts.set(bigger, (counts.get(bigger) ?? 0) + swaps);
  });
  return DENOMINATIONS.flatMap((value) => Array<Denomination>(counts.get(value) ?? 0).fill(value));
}

export interface Stack {
  value: Denomination;
  count: number;
  first: number; // cuántas fichas de este valor hay en las pilas anteriores (para identificarlas)
}

/**
 * Las fichas agrupadas en pilas: una por valor (de mayor a menor), y si una
 * pasa de `tallest` fichas, sigue en otra pila al lado.
 */
export function stacks(chips: readonly Denomination[], tallest = 10): Stack[] {
  const result: Stack[] = [];
  for (const value of DENOMINATIONS) {
    let count = chips.filter((chip) => chip === value).length;
    let first = 0;
    while (count > 0) {
      const height = Math.min(count, tallest);
      result.push({ value, count: height, first });
      first += height;
      count -= height;
    }
  }
  return result;
}
