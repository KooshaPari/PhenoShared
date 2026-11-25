/**
 * Smoke test — verifies test harness works
 * Traces to: FR-ORG-AUDIT-2026-04-001
 */

describe("smoke test", () => {
  it("should pass basic arithmetic", () => {
    expect(2 + 2).toBe(4);
  });
});
