import { describe, expect, it } from "vitest";
import {
  isInteractiveEventTarget,
  shouldIgnoreRowClick,
} from "@/lib/table-row-nav";

describe("table-row-nav", () => {
  it("treats anchors and buttons as interactive", () => {
    const anchor = document.createElement("a");
    const wrap = document.createElement("div");
    wrap.appendChild(anchor);
    expect(isInteractiveEventTarget(anchor)).toBe(true);
    expect(isInteractiveEventTarget(wrap)).toBe(false);
  });

  it("ignores modifier clicks and non-primary button", () => {
    const cell = document.createElement("td");
    expect(
      shouldIgnoreRowClick({
        target: cell,
        metaKey: true,
        ctrlKey: false,
        altKey: false,
        shiftKey: false,
        button: 0,
      }),
    ).toBe(true);
    expect(
      shouldIgnoreRowClick({
        target: cell,
        metaKey: false,
        ctrlKey: false,
        altKey: false,
        shiftKey: false,
        button: 1,
      }),
    ).toBe(true);
    expect(
      shouldIgnoreRowClick({
        target: cell,
        metaKey: false,
        ctrlKey: false,
        altKey: false,
        shiftKey: false,
        button: 0,
      }),
    ).toBe(false);
  });
});
