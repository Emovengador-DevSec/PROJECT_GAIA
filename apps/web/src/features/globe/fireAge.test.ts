import { describe, expect, it } from "vitest";
import { fireAge } from "./fireAge";

const now = Date.parse("2026-11-14T09:00:00Z");

describe("fireAge", () => {
  it("marks a focus from the last 24 hours as the newest tier", () => {
    expect(fireAge("2026-11-13T18:47:00Z", now)).toBe(0);
  });
  it("uses the 1–3 day tier after 24 hours", () => {
    expect(fireAge("2026-11-13T08:59:00Z", now)).toBe(1);
    expect(fireAge("2026-11-11T09:01:00Z", now)).toBe(1);
  });
  it("uses the oldest tier from 3 days on", () => {
    expect(fireAge("2026-11-11T09:00:00Z", now)).toBe(2);
    expect(fireAge("2026-11-07T09:00:00Z", now)).toBe(2);
  });
  it("recalculates the same observation against the replay cursor", () => {
    const observed = "2026-11-13T18:47:00Z";
    expect(fireAge(observed, Date.parse("2026-11-13T19:00:00Z"))).toBe(0);
    expect(fireAge(observed, Date.parse("2026-11-15T18:47:00Z"))).toBe(1);
    expect(fireAge(observed, Date.parse("2026-11-17T18:47:00Z"))).toBe(2);
  });
});
