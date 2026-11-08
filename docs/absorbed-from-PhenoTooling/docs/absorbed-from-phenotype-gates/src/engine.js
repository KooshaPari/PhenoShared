import fs from "node:fs";
import path from "node:path";
import { parse as parseToml } from "smol-toml";

export const GATE_IDS = {
  FR_PGAT_001: "FR-PGAT-001",
  FR_PGAT_008: "FR-PGAT-008",
};

export const SHA_PIN_RE = /^[0-9a-f]{40}$/;

const KNOWN_ACTION_SHAS = {
  "actions/checkout": "b4ffde65f46336ab88eb53be808477a3936bae11",
  "actions/setup-node": "39370e3970a6d050c480ffad4ff0ed4d3fdee5af",
  "actions/setup-python": "0a5c61591373683505ea898e09a3ea4f254ef2dc",
  "actions/cache": "13aacd865c20de90d75de3b46ebe84c46ed7b09a",
  "actions/upload-artifact": "b4b15b8c7c6ac21ea08fcf65892d2ee8f75cf882",
  "actions/download-artifact": "fa0a91b85d4f404e444e00e005971372dc801d57",
  "foo/bar": "1111111111111111111111111111111111111111",
};

export class GatesConfigError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = "GatesConfigError";
    this.details = details;
  }
}

export function loadGatesYml(rootDir) {
  const file = path.join(rootDir, "gates.yml");
  if (!fs.existsSync(file)) {
    throw new GatesConfigError(`gates.yml not found at ${file}`);
  }
  let doc;
  try {
    doc = parseToml(fs.readFileSync(file, "utf8"));
  } catch (e) {
    throw new GatesConfigError(`gates.yml is not valid TOML: ${e.message}`);
  }
  validateConfig(doc, file);
  return doc;
}

function validateConfig(doc, file) {
  if (!doc || typeof doc !== "object") {
    throw new GatesConfigError(`gates.yml must be a TOML table: ${file}`);
  }
  if (!doc.gates || typeof doc.gates !== "object") {
    throw new GatesConfigError(
      `gates.yml must define a [gates] table covering FR-PGAT-001: ${file}`,
    );
  }
  if (!Array.isArray(doc.gates.policies) && !doc.gates.pinned_action_shas) {
    throw new GatesConfigError(
      `gates.yml [gates] must declare policies[] or pinned_action_shas (FR-PGAT-001): ${file}`,
    );
  }
}

export function loadLockFile(rootDir) {
  const file = path.join(rootDir, "gates.lock.json");
  if (!fs.existsSync(file)) return { version: 1, pins: {} };
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    throw new GatesConfigError(`gates.lock.json is not valid JSON: ${e.message}`);
  }
}

export function saveLockFile(rootDir, lock) {
  const file = path.join(rootDir, "gates.lock.json");
  fs.writeFileSync(file, JSON.stringify(lock, null, 2) + "\n");
}

export function discoverWorkflows(rootDir) {
  const wfDir = path.join(rootDir, ".github", "workflows");
  if (!fs.existsSync(wfDir)) return [];
  return fs
    .readdirSync(wfDir)
    .filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"))
    .map((f) => path.join(wfDir, f));
}

const USES_RE = /uses:\s*([^\s#]+)(?:\s+#.*)?/g;

export function extractUsesRefs(workflowPath) {
  const text = fs.readFileSync(workflowPath, "utf8");
  const refs = [];
  let m;
  USES_RE.lastIndex = 0;
  while ((m = USES_RE.exec(text)) !== null) {
    refs.push({ ref: m[1], file: workflowPath, index: m.index });
  }
  return refs;
}

export function checkPinnedShas(rootDir, opts = {}) {
  const cfg = opts.config ?? loadGatesYml(rootDir);
  const known = {
    ...KNOWN_ACTION_SHAS,
    ...(cfg.gates?.pinned_action_shas || {}),
  };
  const violations = [];
  for (const wf of discoverWorkflows(rootDir)) {
    for (const { ref, file } of extractUsesRefs(wf)) {
      if (ref.startsWith("./")) continue;
      const atIdx = ref.lastIndexOf("@");
      if (atIdx < 0) continue;
      const action = ref.slice(0, atIdx);
      const ver = ref.slice(atIdx + 1);
      if (!SHA_PIN_RE.test(ver)) {
        violations.push({
          gate: GATE_IDS.FR_PGAT_008,
          action,
          ref,
          got: ver,
          expected: known[action] || "<known-sha>",
          file,
        });
      }
    }
  }
  return violations;
}

export function check(rootDir, opts = {}) {
  const violations = checkPinnedShas(rootDir, opts);
  return { ok: violations.length === 0, violations };
}

export function suggestFix(violation) {
  const sha =
    KNOWN_ACTION_SHAS[violation.action] || violation.expected || "<known-sha>";
  return {
    from: `${violation.action}@${violation.got}`,
    to: `${violation.action}@${sha}`,
    file: violation.file,
  };
}

export function applyFix(rootDir, violation, opts = {}) {
  const fix = suggestFix(violation);
  const text = fs.readFileSync(fix.file, "utf8");
  if (!text.includes(fix.from)) {
    return { applied: false, fix };
  }
  if (opts.write === false) {
    return { applied: false, fix, dryRun: true };
  }
  const updated = text.replaceAll(fix.from, fix.to);
  fs.writeFileSync(fix.file, updated);
  const lock = loadLockFile(rootDir);
  lock.pins = lock.pins || {};
  lock.pins[fix.from.split("@")[0]] = fix.to;
  lock.version = lock.version || 1;
  saveLockFile(rootDir, lock);
  return { applied: true, fix };
}
