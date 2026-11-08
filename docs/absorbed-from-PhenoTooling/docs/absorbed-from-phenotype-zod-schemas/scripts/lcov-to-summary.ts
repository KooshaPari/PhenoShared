#!/usr/bin/env bun
// Convert bun's lcov.info to Istanbul-style coverage-summary.json
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const coverageDir = "coverage";
const lcovPath = join(coverageDir, "lcov.info");

if (!existsSync(lcovPath)) {
  console.error(`Missing ${lcovPath}`);
  process.exit(1);
}

const text = readFileSync(lcovPath, "utf8");
const records = text.split(/^end_of_record$/m).map((r) => r.trim()).filter(Boolean);

type Metric = { total: number; covered: number; skipped: number; pct: number };
type FileEntry = {
  lines: Metric;
  statements: Metric;
  functions: Metric;
  branches: Metric;
};

function emptyMetric(): Metric {
  return { total: 0, covered: 0, skipped: 0, pct: 100 };
}
function addMetric(m: Metric, total: number, covered: number) {
  m.total += total;
  m.covered += covered;
}
function finalize(m: Metric): Metric {
  m.pct = m.total === 0 ? 100 : +((m.covered / m.total) * 100).toFixed(2);
  return m;
}

const summary: Record<string, FileEntry> = {};
const total: FileEntry = {
  lines: emptyMetric(),
  statements: emptyMetric(),
  functions: emptyMetric(),
  branches: emptyMetric(),
};

// Lines and statements share hit count in lcov (DA = line = statement in TS).
// Functions come from FN/FNF/FNH. Branches come from BRF/BRH.
for (const rec of records) {
  const fileMatch = rec.match(/^SF:(.+)$/m);
  if (!fileMatch) continue;
  const file = fileMatch[1];
  const entry: FileEntry = {
    lines: emptyMetric(),
    statements: emptyMetric(),
    functions: emptyMetric(),
    branches: emptyMetric(),
  };

  // Lines / statements
  const daLines = rec.match(/^DA:(\d+),(\d+)$/gm) ?? [];
  for (const da of daLines) {
    const parts = da.split(",");
    const exec = Number(parts[1]);
    addMetric(entry.lines, 1, exec > 0 ? 1 : 0);
    addMetric(entry.statements, 1, exec > 0 ? 1 : 0);
  }

  // Functions
  const fnLines = rec.match(/^FN:(\d+),(\d+)$/gm) ?? [];
  const fnFound = fnLines.length;
  const fnHitLine = rec.match(/^FNF:(\d+)$/m);
  const fnHit = rec.match(/^FNH:(\d+)$/m);
  entry.functions.total = fnFound;
  entry.functions.covered = fnHit ? Number(fnHit[1]) : 0;
  entry.functions.pct =
    entry.functions.total === 0
      ? 100
      : +((entry.functions.covered / entry.functions.total) * 100).toFixed(2);
  // Sanity: prefer FNF/FNH if present (may differ if FNDA missing)
  if (fnHitLine) entry.functions.total = Number(fnHitLine[1]);

  // Branches
  const brdaLines = rec.match(/^BRDA:.*$/gm) ?? [];
  let brFound = 0;
  let brHit = 0;
  for (const br of brdaLines) {
    brFound += 1;
    const hit = br.split(",").pop()?.trim();
    if (hit && Number(hit) > 0) brHit += 1;
  }
  // Prefer BRF/BRH if present
  const brf = rec.match(/^BRF:(\d+)$/m);
  const brh = rec.match(/^BRH:(\d+)$/m);
  if (brf) entry.branches.total = Number(brf[1]);
  else entry.branches.total = brFound;
  if (brh) entry.branches.covered = Number(brh[1]);
  else entry.branches.covered = brHit;
  entry.branches.pct =
    entry.branches.total === 0
      ? 100
      : +((entry.branches.covered / entry.branches.total) * 100).toFixed(2);

  finalize(entry.lines);
  finalize(entry.statements);

  summary[file] = entry;

  total.lines.total += entry.lines.total;
  total.lines.covered += entry.lines.covered;
  total.statements.total += entry.statements.total;
  total.statements.covered += entry.statements.covered;
  total.functions.total += entry.functions.total;
  total.functions.covered += entry.functions.covered;
  total.branches.total += entry.branches.total;
  total.branches.covered += entry.branches.covered;
}

finalize(total.lines);
finalize(total.statements);
finalize(total.functions);
finalize(total.branches);

const out = { total, ...summary };
writeFileSync(join(coverageDir, "coverage-summary.json"), JSON.stringify(out, null, 2));
console.log(`Wrote ${join(coverageDir, "coverage-summary.json")}`);
