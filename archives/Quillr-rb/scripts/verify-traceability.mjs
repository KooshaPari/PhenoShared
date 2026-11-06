import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const specPath = path.join(root, "docs", "specs", "SPEC.md");
const matrixPath = path.join(root, "docs", "quality", "TRACEABILITY.md");
const evidencePath = path.join(root, "artifacts", "quality", "traceability.json");

const spec = await readFile(specPath, "utf8");
const matrix = await readFile(matrixPath, "utf8");
const requirementIds = [...spec.matchAll(/^#### (FR-\d+|NFR-\d+):/gm)].map((match) => match[1]);
const matrixRows = [...matrix.matchAll(/^\| (FR-\d+|NFR-\d+) \|.*\| VERIFIED \|$/gm)].map(
  (match) => match[1],
);
const verified = requirementIds.filter((id) => matrixRows.includes(id));
const missing = requirementIds.filter((id) => !matrixRows.includes(id));
const coverage = requirementIds.length === 0 ? 0 : verified.length / requirementIds.length;
const evidence = {
  generatedAt: new Date().toISOString(),
  definition: "requirements with a VERIFIED matrix row / requirements declared in SPEC.md",
  numerator: verified.length,
  denominator: requirementIds.length,
  coverage,
  minimum: 0.85,
  missing,
};

await mkdir(path.dirname(evidencePath), { recursive: true });
await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);
console.log(
  `Traceability: ${verified.length}/${requirementIds.length} = ${(coverage * 100).toFixed(1)}%`,
);
if (coverage < 0.85 || missing.length > 0) {
  console.error(`Missing verified requirements: ${missing.join(", ") || "none"}`);
  process.exitCode = 1;
}
