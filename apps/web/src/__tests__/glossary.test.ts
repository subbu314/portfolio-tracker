import { describe, expect, it } from "vitest";
import { GLOSSARY_TERMS } from "@/lib/glossary";

describe("glossary", () => {
  it("includes required terms", () => {
    const ids = GLOSSARY_TERMS.map((t) => t.id);
    for (const need of [
      "absolute-return",
      "xirr",
      "cagr",
      "outperformance",
      "window",
      "ltp",
      "nav",
      "benchmark",
    ]) {
      expect(ids).toContain(need);
    }
  });
});
