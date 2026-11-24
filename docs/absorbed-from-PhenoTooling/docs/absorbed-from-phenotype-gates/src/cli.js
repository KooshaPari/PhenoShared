#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import {
  check,
  checkPinnedShas,
  loadGatesYml,
  suggestFix,
  applyFix,
  GatesConfigError,
} from "./engine.js";

const args = process.argv.slice(2);
const cmd = args[0];

function parseFlags(rest) {
  const out = { _: [], flags: {} };
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (a.startsWith("--")) {
      const k = a.slice(2);
      const v = rest[i + 1] && !rest[i + 1].startsWith("--") ? rest[++i] : "true";
      out.flags[k] = v;
    } else {
      out._.push(a);
    }
  }
  return out;
}

function resolveTarget(rest) {
  const target = rest[0] && !rest[0].startsWith("--") ? rest[0] : ".";
  return path.resolve(process.cwd(), target);
}

function fail(msg, code = 1) {
  process.stderr.write(msg + "\n");
  process.exit(code);
}

function printCheckReport(result) {
  if (result.ok) {
    process.stdout.write("gates: OK\n");
    return;
  }
  for (const v of result.violations) {
    if (v.gate === "FR-PGAT-008") {
      process.stdout.write(
        `${v.gate}: action ${v.action} must be pinned SHA, got @${v.got}\n`,
      );
    } else {
      process.stdout.write(`${v.gate}: ${JSON.stringify(v)}\n`);
    }
  }
}

switch (cmd) {
  case "check": {
    const { flags, _ } = parseFlags(args.slice(1));
    const root = resolveTarget(_);
    try {
      const result = check(root, { config: loadGatesYml(root) });
      printCheckReport(result);
      process.exit(result.ok ? 0 : 1);
    } catch (e) {
      if (e instanceof GatesConfigError) fail(`gates: ${e.message}`);
      throw e;
    }
    break;
  }
  case "fix": {
    const { flags, _ } = parseFlags(args.slice(1));
    const root = resolveTarget(_);
    const gate = flags.gate;
    const dryRun = flags["dry-run"] === "true";
    try {
      const cfg = loadGatesYml(root);
      const violations = checkPinnedShas(root, { config: cfg });
      const targets = gate
        ? violations.filter((v) => v.gate === gate)
        : violations;
      if (targets.length === 0) {
        process.stdout.write("gates fix: nothing to remediate\n");
        process.exit(0);
      }
      const out = [];
      for (const v of targets) {
        const fix = suggestFix(v);
        out.push(fix);
        process.stdout.write(
          `suggested: ${fix.file}: ${fix.from} -> ${fix.to}\n`,
        );
        if (!dryRun) {
          applyFix(root, v, { write: true });
          process.stdout.write(`applied: ${fix.from} -> ${fix.to}\n`);
        }
      }
      process.exit(0);
    } catch (e) {
      if (e instanceof GatesConfigError) fail(`gates: ${e.message}`);
      throw e;
    }
    break;
  }
  case "version":
  case "--version":
  case "-v":
    process.stdout.write("gates 0.1.0\n");
    break;
  case "help":
  case "--help":
  case "-h":
  default:
    process.stdout.write(
      [
        "gates - phenotype policy-as-code gate engine",
        "",
        "Usage:",
        "  gates check [path]",
        "  gates fix [--gate <id>] [--dry-run true] [path]",
        "  gates version",
        "",
      ].join("\n"),
    );
    process.exit(cmd ? 1 : 0);
}
