import { describe, expect, it } from "vitest";
import { DENOMINATIONS, breakdown, colorUp, pile, stacks, total } from "./chips";

describe("desglose en fichas", () => {
  it("usa las menos fichas posibles y suma exactamente la cantidad", () => {
    expect(breakdown(0)).toEqual([]);
    expect(breakdown(1)).toEqual([1]);
    expect(breakdown(30)).toEqual([25, 5]);
    expect(breakdown(1260)).toEqual([1000, 100, 100, 25, 25, 5, 5]);
    for (const amount of [7, 99, 135, 2350, 10000, 123456]) expect(total(breakdown(amount))).toBe(amount);
  });

  it("va de mayor a menor valor", () => {
    const chips = breakdown(6789);
    expect([...chips].sort((a, b) => b - a)).toEqual(chips);
  });

  it("no inventa fichas con cantidades raras", () => {
    expect(breakdown(-5)).toEqual([]);
    expect(breakdown(12.9)).toEqual([5, 5, 1, 1]);
  });

  it("los valores van de mayor a menor y el más pequeño es 1", () => {
    expect([...DENOMINATIONS].sort((a, b) => b - a)).toEqual([...DENOMINATIONS]);
    expect(DENOMINATIONS.at(-1)).toBe(1);
  });
});

describe("fichas apostadas en varias veces", () => {
  it("cada apuesta pone sus fichas encima de las que ya había: la pila solo crece", () => {
    const blind = pile([10]);
    const raised = pile([10, 30]);
    expect(raised.slice(0, blind.length)).toEqual(blind);
    expect(total(raised)).toBe(40);
  });

  it("si se juntan demasiadas, se cambian por fichas de más valor", () => {
    const many = pile(Array(30).fill(6), 40); // 30 × (5 + 1) = 60 fichas
    expect(total(many)).toBe(180);
    expect(many).toEqual(breakdown(180));
  });
});

describe("pilas", () => {
  it("una pila por valor, de mayor a menor", () => {
    expect(stacks([100, 25, 25, 5])).toEqual([
      { value: 100, count: 1, first: 0 },
      { value: 25, count: 2, first: 0 },
      { value: 5, count: 1, first: 0 },
    ]);
  });

  it("una pila demasiado alta sigue al lado", () => {
    expect(stacks(Array(23).fill(5), 10)).toEqual([
      { value: 5, count: 10, first: 0 },
      { value: 5, count: 10, first: 10 },
      { value: 5, count: 3, first: 20 },
    ]);
  });

  it("no pierde ninguna ficha", () => {
    const chips = pile([1260, 75, 5000, 3]);
    const counted = stacks(chips, 6).reduce((sum, stack) => sum + stack.count * stack.value, 0);
    expect(counted).toBe(total(chips));
  });
});

describe("cambiar fichas pequeñas por grandes", () => {
  it("no cambia la cantidad y usa menos fichas", () => {
    const small = pile(Array(17).fill(5)); // 17 fichas de 5
    const up = colorUp(small);
    expect(total(up)).toBe(85);
    expect(up).toEqual([25, 25, 25, 5, 5]);
  });

  it("encadena los cambios hacia arriba", () => {
    expect(colorUp(Array(25).fill(1))).toEqual([25]);
    expect(colorUp([100, 100, 100, 100, 100])).toEqual([500]);
  });

  it("deja igual lo que ya no se puede cambiar", () => {
    expect(colorUp([25, 5, 1])).toEqual([25, 5, 1]);
  });
});
