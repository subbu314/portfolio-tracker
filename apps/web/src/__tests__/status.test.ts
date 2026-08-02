import { describe, expect, it } from "vitest";
import { deriveStatusBanner } from "@/lib/status";

describe("deriveStatusBanner", () => {
  it("prompts login when disconnected", () => {
    const banner = deriveStatusBanner({
      connected: false,
      lastSyncAt: null,
      incomplete: false,
      gap: null,
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("login");
    expect(banner?.ctaHref).toBe("/settings");
  });

  it("links import when gap present", () => {
    const banner = deriveStatusBanner({
      connected: true,
      lastSyncAt: "2026-08-02T10:00:00+05:30",
      incomplete: false,
      gap: { suggested_from: "2024-01-01", suggested_to: "2024-06-01", message: "gap" },
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("gap");
    expect(banner?.ctaHref).toBe("/import");
  });

  it("flags outdated when last sync day is before today", () => {
    const banner = deriveStatusBanner({
      connected: true,
      lastSyncAt: "2026-08-01T18:00:00+05:30",
      incomplete: false,
      gap: null,
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("outdated");
    expect(banner?.ctaLabel).toMatch(/refresh holdings/i);
  });

  it("uses incomplete status when sync is fresh but metrics are incomplete", () => {
    const banner = deriveStatusBanner({
      connected: true,
      lastSyncAt: "2026-08-02T09:00:00+05:30",
      incomplete: true,
      gap: null,
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("incomplete");
    expect(banner?.message).toMatch(/prices|benchmarks/i);
    expect(banner?.ctaAction).toBeUndefined();
    expect(banner?.ctaLabel).not.toMatch(/refresh holdings/i);
  });

  it("prefers sync-stale refresh over incomplete status", () => {
    const banner = deriveStatusBanner({
      connected: true,
      lastSyncAt: "2026-08-01T09:00:00+05:30",
      incomplete: true,
      gap: null,
      today: "2026-08-02",
    });
    expect(banner?.kind).toBe("outdated");
    expect(banner?.ctaAction).toBe("refresh");
  });

  it("returns null when healthy", () => {
    expect(
      deriveStatusBanner({
        connected: true,
        lastSyncAt: "2026-08-02T09:00:00+05:30",
        incomplete: false,
        gap: null,
        today: "2026-08-02",
      }),
    ).toBeNull();
  });
});
