import { describe, expect, it } from "vitest";
import { messageFromApiBody, parseImportError } from "@/lib/api-errors";
import { isSingleImportResult } from "@/lib/import-types";

describe("api-errors", () => {
  it("reads string detail", () => {
    expect(
      messageFromApiBody(JSON.stringify({ detail: "Nope" }), "fallback"),
    ).toBe("Nope");
  });

  it("joins validation detail arrays", () => {
    expect(
      messageFromApiBody(
        JSON.stringify({ detail: [{ msg: "a" }, { msg: "b" }] }),
        "fallback",
      ),
    ).toBe("a; b");
  });

  it("parses import row errors from thrown Error message", () => {
    const err = new Error(
      JSON.stringify({
        detail: { message: "Bad rows", errors: ["row 2", "row 3"] },
      }),
    );
    expect(parseImportError(err)).toEqual({
      message: "Bad rows",
      rows: ["row 2", "row 3"],
    });
  });
});

describe("import-types", () => {
  it("accepts console_tradebook shapes", () => {
    expect(
      isSingleImportResult({
        format: "console_tradebook",
        new: 1,
        existing: 2,
        segment_counts: { EQ: 1 },
        flagged_rows: [],
        date_min: "2024-01-01",
        date_max: "2024-02-01",
        financial_years: ["FY24"],
      }),
    ).toBe(true);
  });

  it("rejects incomplete objects", () => {
    expect(isSingleImportResult({ format: "console_tradebook" })).toBe(false);
  });
});
