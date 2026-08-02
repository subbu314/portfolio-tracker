import { describe, expect, it } from "vitest";
import {
  formatInr,
  formatPct,
  formatPp,
  formatPrice,
  formatSignedInr,
} from "@/lib/format";

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
    expect(formatSignedInr(null)).toBe("N/A");
    expect(formatSignedInr(0)).toBe("₹0");
    expect(formatSignedInr(-100)).toContain("−₹100");
  });
  it("formats unit prices with paise", () => {
    expect(formatPrice(245.67)).toMatch(/245\.67/);
    expect(formatPrice(0.45)).toMatch(/0\.45/);
  });
  it("returns N/A for non-finite numbers", () => {
    expect(formatInr(Number.POSITIVE_INFINITY)).toBe("N/A");
    expect(formatPct(Number.NaN)).toBe("N/A");
    expect(formatPp(Number.NEGATIVE_INFINITY)).toBe("N/A");
    expect(formatPrice(Number.NaN)).toBe("N/A");
  });
});
