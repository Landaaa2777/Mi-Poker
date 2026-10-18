import { describe, expect, it } from "vitest";
import { describeArrival, formatChips } from "./format";

describe("formatChips", () => {
  it("pone un punto cada tres cifras", () => {
    expect(formatChips(0)).toBe("0");
    expect(formatChips(999)).toBe("999");
    expect(formatChips(1000)).toBe("1.000");
    expect(formatChips(10000)).toBe("10.000");
    expect(formatChips(1234567)).toBe("1.234.567");
  });
});

describe("describeArrival", () => {
  // Fechas en la hora del navegador, para que el test valga en cualquier zona horaria.
  const at = (hour: number, minute: number, day = 17) => new Date(2026, 9, day, hour, minute).getTime() / 1000;

  it("dice el día, la hora y cuánto falta", () => {
    expect(describeArrival(at(20, 15, 18), at(20, 15))).toBe("mañana a las 20:15 (dentro de 24 h)");
    expect(describeArrival(at(21, 0), at(20, 15))).toBe("hoy a las 21:00 (dentro de 45 min)");
    expect(describeArrival(at(9, 30, 18), at(20, 15))).toBe("mañana a las 09:30 (dentro de 13 h 15 min)");
    expect(describeArrival(at(9, 30, 20), at(9, 0, 18))).toBe("el 20 de octubre a las 09:30 (dentro de 48 h 30 min)");
  });

  it("si ya casi está, o ya pasó, no da la hora", () => {
    expect(describeArrival(at(20, 15), at(20, 15) - 30)).toBe("en un momento");
    expect(describeArrival(at(20, 15), at(20, 30))).toBe("en un momento");
  });
});
