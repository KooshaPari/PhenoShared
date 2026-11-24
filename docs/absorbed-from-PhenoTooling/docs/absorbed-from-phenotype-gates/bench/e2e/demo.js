#!/usr/bin/env node
// bench/e2e/demo.js
// End-to-end demo: reproduces the issue's acceptance flow on a fresh clone.
// 1. self check (`gates check .`) must exit 0
// 2. fixture check must fail with the FR-PGAT-008 message
// 3. `gates fix --gate=FR-PGAT-008` suggests and applies a patch
// 4. re-run check on the fixture exits 0 and gates.lock.json is updated
// 5. `just demo` exits 0

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import {
  check,
  loadGatesYml,
  loadLockFile,
  saveLockFile,
  checkPinnedShas,
  applyFix,
} from "../../src/engine.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const fixtureSrc = path.join(root, "bench", "fixture");
const scratch = path.join(root, "bench", "fixture.demo");

function rmrf(p) {
  fs.rmSync(p, { recursive: true, force: true });
}

function cpdir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const ent of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, ent.name);
    const d = path.join(dst, ent.name);
    if (ent.isDirectory()) cpdir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function run(cmd, args, cwd) {
  const r = spawnSync(cmd, args, {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf8",
  });
  return {
    status: r.status,
    stdout: r.stdout || "",
    stderr: r.stderr || "",
  };
}

function step(name) {
  process.stdout.write(`\n=== ${name} ===\n`);
}

function assert(cond, msg) {
  if (!cond) {
    process.stderr.write(`ASSERT FAILED: ${msg}\n`);
    process.exit(1);
  }
  process.stdout.write(`  ok: ${msg}\n`);
}

function gates(args, cwd) {
  return run("node", [path.join(root, "src", "cli.js"), ...args], cwd);
}

step("0. prepare fresh fixture scratch");
rmrf(scratch);
cpdir(fixtureSrc, scratch);
const lockFile = path.join(scratch, "gates.lock.json");
if (fs.existsSync(lockFile)) fs.unlinkSync(lockFile);
assert(fs.existsSync(path.join(scratch, "gates.yml")), "fixture gates.yml present");
assert(
  fs.existsSync(path.join(scratch, ".github", "workflows", "ci.yml")),
  "fixture workflow present",
);

step("1. self gates check exits 0");
const self = gates(["check", "."], root);
process.stdout.write(self.stdout);
if (self.stderr) process.stdout.write(self.stderr);
assert(self.status === 0, `gates check . exited ${self.status}`);

step("2. fixture gates check exits 1 with FR-PGAT-008 message");
const bad = gates(["check", scratch], root);
process.stdout.write(bad.stdout);
assert(bad.status === 1, `gates check fixture exited ${bad.status}`);
assert(
  bad.stdout.includes("FR-PGAT-008: action foo/bar must be pinned SHA, got @v4"),
  "expected FR-PGAT-008 message present",
);

step("3. gates fix --gate=FR-PGAT-008 prints suggested patch and applies it");
const fix = gates(["fix", "--gate", "FR-PGAT-008", scratch], root);
process.stdout.write(fix.stdout);
assert(fix.status === 0, `gates fix exited ${fix.status}`);
assert(
  fix.stdout.includes("suggested:") && fix.stdout.includes("applied:"),
  "fix printed suggested and applied lines",
);
const wfText = fs.readFileSync(
  path.join(scratch, ".github", "workflows", "ci.yml"),
  "utf8",
);
assert(
  wfText.includes("foo/bar@1111111111111111111111111111111111111111"),
  "fixture workflow pinned to SHA",
);
assert(fs.existsSync(lockFile), "gates.lock.json created");
const lock = JSON.parse(fs.readFileSync(lockFile, "utf8"));
assert(lock.pins && lock.pins["foo/bar"], "gates.lock.json pins foo/bar");

step("4. re-run check on fixture exits 0");
const good = gates(["check", scratch], root);
process.stdout.write(good.stdout);
assert(good.status === 0, `re-check exited ${good.status}`);

step("5. just demo reproduces all on fresh clone");
rmrf(scratch);
const just = run(
  "bash",
  [path.join(root, "bin", "just"), "demo"],
  root,
);
process.stdout.write(just.stdout);
if (just.stderr) process.stdout.write(just.stderr);
assert(just.status === 0, `just demo exited ${just.status}`);
const justLock = path.join(scratch, "gates.lock.json");
assert(fs.existsSync(justLock), "just demo produced gates.lock.json");

process.stdout.write("\nALL E2E STEPS PASSED\n");
