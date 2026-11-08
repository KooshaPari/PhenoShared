/** T80: PhenoObservability hexagonal port — Telemetry. 3 adapters: OTel, Prom, Datadog. */
export interface Span {
  readonly traceId: string;
  readonly spanId: string;
  readonly name: string;
  readonly startMs: number;
  readonly endMs?: number;
}
export interface Metric {
  readonly name: string;
  readonly value: number;
  readonly tags: Readonly<Record<string, string>>;
  readonly timestamp: number;
}
export interface LogEntry {
  readonly level: "debug" | "info" | "warn" | "error";
  readonly message: string;
  readonly timestamp: number;
}
export interface Telemetry {
  readonly backend: "otel" | "prom" | "datadog";
  trace(name: string): Span;
  metric(m: Metric): void;
  log(l: LogEntry): void;
}
