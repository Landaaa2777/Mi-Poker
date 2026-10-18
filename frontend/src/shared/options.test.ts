import { describe, expect, it } from "vitest";
import { defaultValues, numberProblem, type GameOption } from "./options";

const stack: GameOption = {
  key: "starting_stack",
  type: "number",
  label: "Fichas iniciales",
  default: 1000,
  min: 10,
  max: 1_000_000,
  step: 10,
};
const toggle: GameOption = { key: "surrender", type: "toggle", label: "Rendición", default: false };

describe("defaultValues", () => {
  it("toma el valor por defecto de cada opción", () => {
    expect(defaultValues([stack, toggle])).toEqual({ starting_stack: 1000, surrender: false });
  });
});

describe("numberProblem", () => {
  it("acepta lo que está dentro de los límites", () => {
    expect(numberProblem(stack, 500)).toBeNull();
    expect(numberProblem(toggle, 3)).toBeNull();
  });

  it("explica qué falla", () => {
    expect(numberProblem(stack, 5)).toContain("como poco 10");
    expect(numberProblem(stack, 2_000_000)).toContain("como mucho 1000000");
    expect(numberProblem(stack, 505)).toContain("de 10 en 10");
    expect(numberProblem(stack, Number.NaN)).toContain("escribe un número");
  });

  it("puede ser más estricto que el servidor (el saldo de la cuenta)", () => {
    expect(numberProblem(stack, 900, 800)).toContain("como mucho 800");
  });
});
