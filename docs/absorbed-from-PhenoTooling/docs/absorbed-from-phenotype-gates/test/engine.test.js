import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  check,
  loadGatesYml,
  GatesConfigError,
  checkPinnedShas,
  applyFix,
  suggestFix,
} from "../src/engine.js";

function makeRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gates-test-"));
  fs.writeFileSync(
    path.join(dir, "gates.yml"),
    [
      "[gates]",
      'version = 1',
      "",
      "[gates.pinned_action_shas]",
      '"actions/checkout" = "b4ffde65f46336ab88eb53be808477a3936bae11"',
      "",
    ].join("\n"),
  );
  fs.mkdirSync(path.join(dir, ".github", "workflows"), { recursive: true });
  return dir;
}

test("gates.yml must define [gates] table (FR-PGAT-001)", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gates-test-"));
  fs.writeFileSync(path.join(dir, "gates.yml"), "version = 1\n");
  assert.throws(() => loadGatesYml(dir), GatesConfigError);
});

test("pinned workflow passes", () => {
  const dir = makeRepo();
  fs.writeFileSync(
    path.join(dir, ".github", "workflows", "ci.yml"),
    "uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11\n",
  );
  const r = check(dir);
  assert.equal(r.ok, true);
  assert.equal(r.violations.length, 0);
});

test("unpinned @v4 violates FR-PGAT-008", () => {
  const dir = makeRepo();
  fs.writeFileSync(
    path.join(dir, ".github", "workflows", "ci.yml"),
    "uses: foo/bar@v4\n",
  );
  const r = check(dir);
  assert.equal(r.ok, false);
  assert.equal(r.violations.length, 1);
  assert.equal(r.violations[0].gate, "FR-PGAT-008");
  assert.equal(r.violations[0].action, "foo/bar");
  assert.equal(r.violations[0].got, "v4");
});

test("fix applies SHA and writes gates.lock.json", () => {
  const dir = makeRepo();
  const wf = path.join(dir, ".github", "workflows", "ci.yml");
  fs.writeFileSync(wf, "uses: foo/bar@v4\n");
  const v = checkPinnedShas(dir)[0];
  const fix = suggestFix(v);
  assert.equal(fix.from, "foo/bar@v4");
  assert.match(fix.to, /^foo\/bar@[0-9a-f]{40}$/);
  const r = applyFix(dir, v, { write: true });
  assert.equal(r.applied, true);
  assert.match(fs.readFileSync(wf, "utf8"), /foo\/bar@[0-9a-f]{40}/);
  const lock = JSON.parse(
    fs.readFileSync(path.join(dir, "gates.lock.json"), "utf8"),
  );
  assert.equal(lock.pins["foo/bar"], fix.to);
});
