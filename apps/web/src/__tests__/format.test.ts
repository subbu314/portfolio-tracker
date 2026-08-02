import { describe, expect, it } from "vitest";
import { formatInr, formatPct, formatPp, formatSignedInr } from "@/lib/format";

describe("format", () => {
  it("formats INR", () => {
    expect(formatInr(1234.5)).toContain("1,235");
  });
  it("formats percent", () => {
    expect(formatPct(0.256)).toBe("25.60%");
  });
  it("formats NA", () => {
    expect(formatPct(null)).toBe("N/A");
  });
  it("formats excess pp", () => {
    expect(formatPp(5.2)).toBe("+5.20 pp");
  });
  it("formats signed INR", () => {
    expect(formatSignedInr(100)).toContain("+");
    expect(formatSignedInr(100)).toContain("₹");
  });
});
