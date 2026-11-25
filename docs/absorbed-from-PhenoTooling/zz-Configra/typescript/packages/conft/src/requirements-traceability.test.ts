import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";

type Status = "verified" | "partial" | "gap";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const requirements = readFileSync(resolve(root, "FUNCTIONAL_REQUIREMENTS.md"), "utf8");
const documentedIds = [...new Set(requirements.match(/FR-[A-Z]+-\d{3}/g) ?? [])].sort();

const trace: ReadonlyArray<{
  id: string;
  status: Status;
  evidence: string | string[];
}> = [
  { id: "FR-SCHEMA-001", status: "partial", evidence: "src/domain/config.ts" },
  { id: "FR-SCHEMA-002", status: "partial", evidence: "src/index.test.ts" },
  { id: "FR-SCHEMA-003", status: "verified", evidence: "src/domain/config.ts" },
  { id: "FR-SRC-001", status: "partial", evidence: "src/adapters/file-adapter.test.ts" },
  { id: "FR-SRC-002", status: "verified", evidence: "src/adapters/env-adapter.test.ts" },
  { id: "FR-SRC-003", status: "verified", evidence: "src/services/config-manager.test.ts" },
  { id: "FR-LAYER-001", status: "verified", evidence: "src/services/config-manager.test.ts" },
  { id: "FR-LAYER-002", status: "gap", evidence: "adr/ADR-003-deep-merge.md" },
  { id: "FR-LAYER-003", status: "gap", evidence: "src/domain/secret.test.ts" },
  { id: "FR-HEX-001", status: "verified", evidence: "src/ports/config-source.ts" },
  { id: "FR-HEX-002", status: "verified", evidence: "src/services/config-manager.ts" },
  {
    id: "FR-HEX-003",
    status: "verified",
    evidence: ["src/adapters/file-adapter.ts", "src/adapters/env-adapter.ts"],
  },
];

describe("functional requirement traceability", () => {
  it("traces every declared requirement exactly once (12/12)", () => {
    const tracedIds = trace.map(({ id }) => id).sort();
    expect(tracedIds).toEqual(documentedIds);
    expect(new Set(tracedIds).size).toBe(trace.length);
  });

  it("keeps every evidence path resolvable", () => {
    for (const item of trace) {
      const paths = Array.isArray(item.evidence) ? item.evidence : [item.evidence];
      for (const path of paths) {
        expect(existsSync(resolve(root, path)), `${item.id}: ${path}`).toBe(true);
      }
    }
  });

  it("reports implementation gaps instead of treating traceability as satisfaction", () => {
    expect(trace.filter(({ status }) => status === "verified")).toHaveLength(7);
    expect(trace.filter(({ status }) => status === "partial")).toHaveLength(3);
    expect(trace.filter(({ status }) => status === "gap").map(({ id }) => id).sort()).toEqual([
      "FR-LAYER-002",
      "FR-LAYER-003",
    ]);
  });
});
