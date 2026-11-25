/**
 * OKF language adapter stub — TypeScript reference (C08 L75).
 *
 * Implements the language-agnostic contract in adapters/README.md:
 *   load(path) -> Record<string, unknown>
 *   validate(doc, stem?) -> void (throws on failure)
 *   emit(doc) -> string
 *
 * CLI:
 *   node --experimental-strip-types okf_adapter.ts validate <path.okf.json>
 *   node --experimental-strip-types okf_adapter.ts emit <path.okf.json>
 *
 * Hermetic: Node stdlib only. Not a Harbor / agent-eval harness.
 */

import { readFileSync } from "node:fs";
import { basename } from "node:path";

const OKF_DIALECT = "1.0";

const REQUIRED_SHARED_ENTITY_TYPES = new Set([
  "intent",
  "acceptance",
  "constraint",
  "resource",
  "state",
  "gate",
]);

const ALLOWED_RELATION_TYPES = new Set([
  "verified_by",
  "bounded_by",
  "grounds",
  "requires",
  "asserts",
]);

type JsonObject = Record<string, unknown>;

function load(path: string): JsonObject {
  const raw = readFileSync(path, "utf8");
  const doc: unknown = JSON.parse(raw);
  if (typeof doc !== "object" || doc === null || Array.isArray(doc)) {
    throw new Error("OKF root must be a JSON object");
  }
  return doc as JsonObject;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asObject(value: unknown): JsonObject | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as JsonObject)
    : null;
}

function asArray(value: unknown): unknown[] | null {
  return Array.isArray(value) ? value : null;
}

function validate(doc: JsonObject, stem?: string): void {
  if (doc.okf !== OKF_DIALECT) {
    throw new Error(`expected okf '${OKF_DIALECT}', got ${String(doc.okf)}`);
  }

  const sourceId = asString(doc.source_id);
  if (!sourceId) {
    throw new Error("missing non-empty source_id");
  }
  if (stem !== undefined && sourceId !== stem) {
    throw new Error(
      `source_id ${JSON.stringify(sourceId)} must equal filename stem ${JSON.stringify(stem)}`,
    );
  }

  const provenance = asObject(doc.provenance);
  if (!provenance) {
    throw new Error("missing document provenance object");
  }
  if (provenance.source_id !== sourceId) {
    throw new Error("provenance.source_id must equal top-level source_id");
  }

  const entities = asArray(doc.entities);
  if (!entities) {
    throw new Error("entities must be a JSON array");
  }
  if (entities.length < 1) {
    throw new Error("entities must be non-empty");
  }

  const ids = new Set<string>();
  const types = new Set<string>();
  for (const item of entities) {
    const entity = asObject(item);
    if (!entity) {
      throw new Error("each entity must be an object");
    }
    const eid = asString(entity.id);
    const etype = asString(entity.type);
    const label = asString(entity.label);
    if (!eid) {
      throw new Error("entity missing id");
    }
    if (!etype) {
      throw new Error(`entity ${JSON.stringify(eid)} missing type`);
    }
    if (!label || !label.trim()) {
      throw new Error(`entity ${JSON.stringify(eid)} missing label`);
    }
    if (ids.has(eid)) {
      throw new Error(`duplicate entity id ${JSON.stringify(eid)}`);
    }
    ids.add(eid);
    types.add(etype);
  }

  const missing = [...REQUIRED_SHARED_ENTITY_TYPES].filter(
    (t) => !types.has(t),
  );
  if (missing.length > 0) {
    throw new Error(
      `missing required shared entity types: ${missing.sort().join(", ")}`,
    );
  }

  const relations = asArray(doc.relations);
  if (!relations) {
    throw new Error("relations must be a JSON array");
  }
  if (relations.length < 1) {
    throw new Error("relations must be non-empty");
  }

  for (const item of relations) {
    const rel = asObject(item);
    if (!rel) {
      throw new Error("each relation must be an object");
    }
    const src = rel.source;
    const tgt = rel.target;
    const rtype = rel.type;
    const rprov = asObject(rel.provenance);
    if (typeof src !== "string" || !ids.has(src)) {
      throw new Error(`relation source ${JSON.stringify(src)} not in entities`);
    }
    if (typeof tgt !== "string" || !ids.has(tgt)) {
      throw new Error(`relation target ${JSON.stringify(tgt)} not in entities`);
    }
    if (typeof rtype !== "string" || !ALLOWED_RELATION_TYPES.has(rtype)) {
      throw new Error(
        `relation type ${JSON.stringify(rtype)} not in OKF v1.0 set`,
      );
    }
    if (!rprov || rprov.source_id !== sourceId) {
      throw new Error(
        "relation provenance.source_id must equal top-level source_id",
      );
    }
  }
}

function emit(doc: JsonObject): string {
  return `${JSON.stringify(doc, null, 2)}\n`;
}

function stemOf(path: string): string {
  const name = basename(path);
  const suffix = ".okf.json";
  if (name.endsWith(suffix)) {
    return name.slice(0, -suffix.length);
  }
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(0, dot) : name;
}

function main(argv: string[]): number {
  if (argv.length !== 4 || (argv[2] !== "validate" && argv[2] !== "emit")) {
    process.stderr.write(
      "usage: okf_adapter.ts validate|emit <path.okf.json>\n",
    );
    return 2;
  }

  const command = argv[2];
  const path = argv[3];

  try {
    const doc = load(path);
    validate(doc, stemOf(path));
    if (command === "validate") {
      process.stdout.write(
        `OKF validate ok: ${path} (source_id=${String(doc.source_id)})\n`,
      );
      return 0;
    }
    process.stdout.write(emit(doc));
    return 0;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    process.stderr.write(`OKF adapter error: ${message}\n`);
    return 1;
  }
}

process.exit(main(process.argv));
