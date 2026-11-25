import { describe, it, expect } from "vitest";
import { modelMetrics, routingDecisions, getParetoFrontier } from "./mockData";

describe("mockData", () => {
  it("all modelMetrics have valid cost and quality", () => {
    for (const m of modelMetrics) {
      expect(m.costPer1kTokens).toBeGreaterThan(0);
      expect(m.qualityScore).toBeGreaterThanOrEqual(0);
      expect(m.qualityScore).toBeLessThanOrEqual(100);
    }
  });

  it("getParetoFrontier returns non-empty set and includes cheapest+highest quality", () => {
    const frontier = getParetoFrontier(modelMetrics);
    expect(frontier.size).toBeGreaterThan(0);
    // cheapest model should be on frontier (nothing cheaper at same quality)
    const cheapest = modelMetrics.reduce((a, b) =>
      a.costPer1kTokens < b.costPer1kTokens ? a : b
    );
    expect(frontier.has(cheapest.model)).toBe(true);
    // highest quality model should be on frontier
    const bestQuality = modelMetrics.reduce((a, b) =>
      a.qualityScore > b.qualityScore ? a : b
    );
    expect(frontier.has(bestQuality.model)).toBe(true);
  });

  it("routingDecisions have unique ids", () => {
    const ids = routingDecisions.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
