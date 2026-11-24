import { describe, expect, it } from "vitest";
import { OtelAdapter } from "../adapters/otel";
import { PromAdapter } from "../adapters/prom";

describe("PhenoObservability ports", () => {
  it("OtelAdapter.backend", () => {
    expect(new OtelAdapter().backend).toBe("otel");
  });
  it("PromAdapter.backend", () => {
    expect(new PromAdapter().backend).toBe("prom");
  });
  it("OtelAdapter.trace returns Span", () => {
    const s = new OtelAdapter().trace("x");
    expect(s.name).toBe("x");
  });
  it("OtelAdapter.metric no-throw", () => {
    new OtelAdapter().metric({ name: "n", value: 1, tags: {}, timestamp: 0 });
  });
  it("Telemetry interface object-safe", () => {
    const _s: import("../telemetry").Telemetry = new OtelAdapter();
  });
});
