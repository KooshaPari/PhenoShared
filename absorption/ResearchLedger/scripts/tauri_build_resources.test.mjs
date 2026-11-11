/** @vitest-environment node */

import { expect, test } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const buildScript = fs.readFileSync(
  path.join(repoRoot, "apps/desktop/src-tauri/build.rs"),
  "utf8",
);

test("only the explicit Rust-test switch removes packaged browser resources", () => {
  expect(buildScript).toContain('std::env::var("RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION")');
  expect(buildScript).toContain(
    "cargo:rerun-if-env-changed=RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION",
  );
  expect(buildScript).toContain('== Some("1")');
  expect(buildScript).toContain('if std::env::var_os("TAURI_CONFIG").is_some()');
  expect(buildScript).toContain(
    "RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION cannot be combined with TAURI_CONFIG",
  );
  expect(buildScript).toContain('std::env::set_var("TAURI_CONFIG", r#"{"bundle":{"resources":null}}"#)');
  expect(buildScript).toContain("tauri_build::build()");
});
