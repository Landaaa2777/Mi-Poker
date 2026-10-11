import { describe, expect, it } from "vitest";
import { formatChips } from "./format";

describe("formatChips", () => {
  it("pone un punto cada tres cifras", () => {
    expect(formatChips(0)).toBe("0");
    expect(formatChips(999)).toBe("999");
    expect(formatChips(1000)).toBe("1.000");
    expect(formatChips(10000)).toBe("10.000");
    expect(formatChips(1234567)).toBe("1.234.567");
  });
});
