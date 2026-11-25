import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const readWorkflow = (name) => readFile(path.join(root, ".github", "workflows", name), "utf8");

describe("hosted CI contracts", () => {
  test("declares ESM package semantics for Vite's native config loader", async () => {
    const manifest = JSON.parse(await readFile(path.join(root, "package.json"), "utf8"));

    expect(manifest.type).toBe("module");
  });

  test("uses the Bun lock and discovers the nested Tauri crate", async () => {
    const workflow = await readWorkflow("ci.yml");

    expect(workflow).toContain("oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6");
    expect(workflow).toContain("bun install --frozen-lockfile");
    expect(workflow).not.toContain("npm ci");
    expect(workflow).toContain("-name Cargo.toml -type f");
    expect(workflow).toContain("--manifest-path apps/desktop/src-tauri/Cargo.toml");
    expect(workflow).toContain("needs.dep-review.result");
    expect(workflow).not.toContain("needs.dependency-review.result");
  });

  test("gives history-based scanners the complete PR history", async () => {
    const workflow = await readWorkflow("ci.yml");
    const security = workflow.slice(workflow.indexOf("  security:"), workflow.indexOf("  dep-review:"));

    expect(security).toContain("fetch-depth: 0");
  });

  test("pins checkout and does not persist its workflow credential", async () => {
    const workflow = await readWorkflow("ci.yml");

    expect(workflow).not.toContain("actions/checkout@v7");
    expect(workflow).toContain("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1");
    const checkoutCount = (workflow.match(/uses: actions\/checkout@/g) ?? []).length;
    const disabledCredentialCount = (workflow.match(/persist-credentials: false/g) ?? []).length;
    expect(checkoutCount).toBeGreaterThan(0);
    expect(disabledCredentialCount).toBe(checkoutCount);
  });

  test("runs the desktop Rust gate on its supported macOS target", async () => {
    const workflow = await readWorkflow("ci.yml");
    const rust = workflow.slice(workflow.indexOf("  rust:"), workflow.indexOf("  cargo-deny:"));

    expect(rust).toContain("runs-on: macos-latest");
    expect(rust).toContain("RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION: \"1\"");
    expect(rust).not.toContain("Swatinem/rust-cache");
  });

  test("pins Rust toolchain and Cargo Deny actions to immutable revisions", async () => {
    const workflow = await readWorkflow("ci.yml");

    expect(workflow).toContain("dtolnay/rust-toolchain@4360b52568e2003a75bf9bc1d59f33a8e3fc893c");
    expect(workflow).toContain("EmbarkStudios/cargo-deny-action@3c6349835b2b7b196a839186cb8b78e02f7b5f25");
    expect(workflow).not.toContain("dtolnay/rust-toolchain@stable");
    expect(workflow).not.toContain("EmbarkStudios/cargo-deny-action@v2");
  });

  test("uses a pinned checkout and deterministic Prettier instead of broken Trunk", async () => {
    const workflow = await readWorkflow("trunk-check.yml");

    expect(workflow).toContain("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1");
    expect(workflow).toContain("npm install --global prettier@3.6.2");
    expect(workflow).toContain("prettier --check");
    expect(workflow).not.toContain("uses: trunk-io/trunk-action@");
  });

  test("keeps release verification on the Bun toolchain", async () => {
    const workflow = await readWorkflow("release.yml");

    expect(workflow).toContain("oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6");
    expect(workflow).toContain("bun install --frozen-lockfile");
    expect(workflow).toContain("bun run build");
    expect(workflow).toContain("bun run test");
    expect(workflow).not.toContain("actions/setup-node");
    expect(workflow).not.toContain("npm ");
  });

  test("uses the current Trunk configuration schema", async () => {
    const config = await readFile(path.join(root, ".trunk", "trunk.yaml"), "utf8");

    expect(config).toContain("version: 0.1");
    expect(config).toContain("lint:");
    expect(config).not.toContain("linters:");
    expect(config).not.toContain("formatters:");
    expect(config).toContain("- git-diff-check");
    expect(config).not.toContain("- actionlint");
    expect(config).not.toContain("- prettier");
    expect(config).not.toContain("- taplo");
  });

  test("scopes Prettier to changed supported files outside scheduled full checks", async () => {
    const workflow = await readWorkflow("trunk-check.yml");

    expect(workflow).toContain("git diff --diff-filter=ACMR --name-only FETCH_HEAD HEAD");
    expect(workflow).toContain("if [[ \"${{ github.event_name }}\" == \"schedule\" ]]");
    expect(workflow).toContain("No changed Prettier-supported files to check.");
    expect(workflow).not.toContain("uses: actions/setup-go@");
    expect(workflow).not.toContain("github.com/rhysd/actionlint/cmd/actionlint@");
  });

  test("keeps all repository workflows valid for actionlint", async () => {
    const scorecard = await readWorkflow("scorecard.yml");
    const config = await readFile(path.join(root, ".github", "actionlint.yaml"), "utf8");

    expect(scorecard).not.toContain("    security:\n      permissions: read-all");
    expect(config).toContain("blacksmith-2vcpu-ubuntu-2204");
  });

  test("uses current Mergify rule syntax", async () => {
    const config = await readFile(path.join(root, ".mergify.yml"), "utf8");

    expect(config).toContain("- or:");
    expect(config).toContain("updated-at < 30 days ago");
    expect(config).toContain("        users:\n          - KooshaPari");
    expect(config).not.toContain("github_accounts:");
    expect(config).not.toContain("post_merge:");
    expect(config).not.toContain("age>=30d");
  });
});
