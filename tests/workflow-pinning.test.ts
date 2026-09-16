/**
 * Workflow Action Pinning Validation
 *
 * Validates that all GitHub Actions workflow files use SHA-pinned actions
 * (supply-chain security) and concrete runner versions (reproducibility).
 * Traces to: L10 CI/CD hygiene (audit v37)
 */

import { readdirSync, readFileSync } from "fs";
import { join } from "path";

const WORKFLOWS_DIR = join(__dirname, "..", ".github", "workflows");

// Actions that are exempt from SHA pinning because they don't have SHA-pinnable refs
const EXEMPT_ACTIONS = [
  // Reusable workflow calls use `@ref` syntax, not action SHAs
  "KooshaPari/",
];

describe("GitHub Actions SHA pinning", () => {
  const workflowFiles = readdirSync(WORKFLOWS_DIR).filter((f) =>
    f.endsWith(".yml"),
  );

  test.each(workflowFiles)("%s — all actions are SHA-pinned", (file) => {
    const content = readFileSync(join(WORKFLOWS_DIR, file), "utf8");
    const lines = content.split("\n");
    const violations: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Skip comments and non-uses lines
      if (!trimmed.startsWith("uses:") && !trimmed.startsWith("- uses:")) {
        continue;
      }

      // Normalize: strip leading "- " and "uses:"
      const usePart = trimmed.replace(/^- /, "").replace(/^uses:\s*/, "");
      const actionRef = usePart.split(/\s+/)[0]; // Get first word (may have # comment inline)

      // Skip actions that reference org patterns (reusable workflows)
      if (EXEMPT_ACTIONS.some((prefix) => actionRef.startsWith(prefix))) {
        continue;
      }

      // Check: docker:// references are not SHA-pinnable in the same way
      if (actionRef.startsWith("docker://")) {
        continue;
      }

      // Validate SHA pinning: must be owner/repo@<40-char-hex>
      // Supports sub-paths like owner/repo/sub-action
      const shaPattern = /^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+(\/[a-zA-Z0-9_.-]+)*@[0-9a-f]{40}$/;
      if (!shaPattern.test(actionRef)) {
        violations.push(
          `  Line ${i + 1}: "${trimmed}" — not SHA-pinned (ref: "${actionRef}")`,
        );
      }
    }

    expect(violations, violations.join("\n")).toHaveLength(0);
  });

  test.each(workflowFiles)("%s — no @latest references", (file) => {
    const content = readFileSync(join(WORKFLOWS_DIR, file), "utf8");
    const lines = content.split("\n");
    const violations: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.includes("@latest")) {
        violations.push(`  Line ${i + 1}: "${line.trim()}" — uses @latest`);
      }
    }

    expect(violations, violations.join("\n")).toHaveLength(0);
  });

  test.each(workflowFiles)("%s — uses concrete runner versions", (file) => {
    const content = readFileSync(join(WORKFLOWS_DIR, file), "utf8");
    const lines = content.split("\n");
    const violations: string[] = [];

    // Skip template/documentation files that aren't real workflows
    const templateMarkers = [
      "## What is",
      "**Source audit:**",
      "## Template:",
    ];
    const isTemplate = templateMarkers.some((marker) => content.includes(marker));
    if (isTemplate) {
      return; // Skip template/doc files
    }

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      // Check for `runs-on:` with `-latest` suffix
      if (line.startsWith("runs-on:") && line.includes("-latest")) {
        violations.push(
          `  Line ${i + 1}: "${line}" — uses floating runner version`,
        );
      }
    }

    expect(violations, violations.join("\n")).toHaveLength(0);
  });
});
