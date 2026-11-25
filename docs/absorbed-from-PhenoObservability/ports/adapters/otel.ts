import type { LogEntry, Metric, Span, Telemetry } from "../telemetry";

export class OtelAdapter implements Telemetry {
  readonly backend = "otel" as const;
  trace(name: string): Span {
    return { traceId: "0", spanId: "0", name, startMs: Date.now() };
  }
  metric(_m: Metric): void {}
  log(_l: LogEntry): void {}
}
