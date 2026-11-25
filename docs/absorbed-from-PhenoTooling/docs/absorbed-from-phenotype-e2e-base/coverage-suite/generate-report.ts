/**
 * Playwright test coverage report generator.
 *
 * Reads:
 *   - ./coverage.config.ts  — the declared coverage matrix (what SHOULD be tested)
 *   - ../tests/*.spec.ts    — the actual spec files (what IS being tested)
 *
 * Emits:
 *   - ../coverage.json      — machine-readable report (for CI / dashboards)
 *   - ../COVERAGE.md        — human-readable report (committed to the repo)
 *
 * Detection strategy:
 *   A spec file named `byteport.spec.ts` is considered to cover the
 *   `byteport` site. Each `test(...)` block inside the file is treated
 *   as covering one flow if its name contains a known flow id
 *   (kebab-cased), e.g. "hero CTA is visible" → hero-cta.
 *
 * Browser coverage is INHERITED from playwright.config.ts: every spec
 * runs on every project in the active matrix (chromium/firefox/webkit),
 * unless a test is tagged with `@only` / `@skip` (Playwright built-in).
 *
 * This script is intentionally dependency-free — only Node stdlib
 * (fs/path) and the TypeScript config file itself.
 */

import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import {
	type FlowId,
	type SiteId,
	activeProjects,
	requiredMatrix,
	sites,
} from "./coverage.config.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = join(__dirname, "..");
const testsDir = join(repoRoot, "tests");

// ─── types ────────────────────────────────────────────────────────────────

type CellStatus = "covered" | "partial" | "missing";

interface CellReport {
	site: SiteId;
	flow: FlowId;
	requiredProjects: ReadonlyArray<string>;
	actualProjects: string[];
	status: CellStatus;
	testNames: string[];
}

interface CoverageReport {
	generatedAt: string;
	totals: {
		required: number;
		covered: number;
		partial: number;
		missing: number;
		percentCovered: number;
	};
	sites: ReadonlyArray<{ id: SiteId; url: string }>;
	projects: ReadonlyArray<string>;
	cells: CellReport[];
}

// ─── spec scanning ────────────────────────────────────────────────────────

/**
 * Scan tests/*.spec.ts and return, per site, the set of flows exercised
 * (derived from test names) and the raw test names.
 */
function scanSpecs(): Map<SiteId, { flows: Set<FlowId>; tests: string[] }> {
	const result = new Map<SiteId, { flows: Set<FlowId>; tests: string[] }>();
	for (const site of sites) {
		result.set(site.id, { flows: new Set(), tests: [] });
	}

	let specFiles: string[];
	try {
		specFiles = readdirSync(testsDir).filter((f) => f.endsWith(".spec.ts"));
	} catch {
		return result; // tests/ doesn't exist yet
	}

	for (const file of specFiles) {
		const siteId = file.replace(/\.spec\.ts$/, "") as SiteId;
		if (!result.has(siteId)) continue; // spec for an undeclared site — ignore

		const content = readFileSync(join(testsDir, file), "utf-8");
		// Match `test("…", …)` or `test('…', …)` blocks (handles single + double quotes).
		const testRe = /\btest\s*\(\s*["'`]([^"'`]+)["'`]/g;
		let match = testRe.exec(content);
		while (match !== null) {
			const name = match[1] ?? "";
			const entry = result.get(siteId);
			if (!entry) continue;
			entry.tests.push(name);
			const flow = matchFlow(name);
			if (flow) entry.flows.add(flow);
			match = testRe.exec(content);
		}
	}

	return result;
}

/** Map a test name to a declared flow id via substring matching. */
function matchFlow(name: string): FlowId | null {
	const n = name.toLowerCase();
	if (/(hero|cta)/.test(n)) return "hero-cta";
	if (/(github|stats)/.test(n)) return "github-stats";
	if (/(footer|year)/.test(n)) return "footer-year";
	if (/(nav|links|menu)/.test(n)) return "nav-links";
	if (/(a11y|accessib|axe)/.test(n)) return "a11y-baseline";
	return null;
}

// ─── report assembly ──────────────────────────────────────────────────────

function buildReport(
	scanned: Map<SiteId, { flows: Set<FlowId>; tests: string[] }>,
): CoverageReport {
	const cells: CellReport[] = requiredMatrix.map((req) => {
		const entry = scanned.get(req.site);
		const hasFlow = entry?.flows.has(req.flow) ?? false;
		const actualProjects = hasFlow ? [...activeProjects] : [];

		let status: CellStatus;
		if (!hasFlow) {
			status = "missing";
		} else if (req.requiredProjects.every((p) => actualProjects.includes(p))) {
			status = "covered";
		} else {
			status = "partial";
		}

		return {
			site: req.site,
			flow: req.flow,
			requiredProjects: req.requiredProjects,
			actualProjects,
			status,
			testNames: entry?.tests.filter((t) => matchFlow(t) === req.flow) ?? [],
		};
	});

	const covered = cells.filter((c) => c.status === "covered").length;
	const partial = cells.filter((c) => c.status === "partial").length;
	const missing = cells.filter((c) => c.status === "missing").length;
	const total = cells.length;

	return {
		generatedAt: new Date().toISOString(),
		totals: {
			required: total,
			covered,
			partial,
			missing,
			percentCovered: total === 0 ? 100 : Math.round((covered / total) * 100),
		},
		sites,
		projects: [...activeProjects],
		cells,
	};
}

// ─── emitters ─────────────────────────────────────────────────────────────

function emitJson(report: CoverageReport): void {
	const out = join(repoRoot, "coverage.json");
	writeFileSync(out, `${JSON.stringify(report, null, 2)}\n`, "utf-8");
	// eslint-disable-next-line no-console
	console.log(`[coverage] wrote ${relative(repoRoot, out)}`);
}

function emitMarkdown(report: CoverageReport): void {
	const lines: string[] = [];
	const { totals } = report;
	const badge =
		totals.percentCovered >= 90
			? "🟢"
			: totals.percentCovered >= 60
				? "🟡"
				: "🔴";

	lines.push("# Playwright Test Coverage");
	lines.push("");
	lines.push(
		"> Auto-generated by `coverage-suite/generate-report.ts`. Do not edit by hand.",
	);
	lines.push("");
	lines.push(`Generated: \`${report.generatedAt}\``);
	lines.push("");
	lines.push(`## Summary ${badge}`);
	lines.push("");
	lines.push("| Metric | Value |");
	lines.push("|--------|-------|");
	lines.push(`| Required cells | ${totals.required} |`);
	lines.push(`| Covered | ${totals.covered} |`);
	lines.push(`| Partial | ${totals.partial} |`);
	lines.push(`| Missing | ${totals.missing} |`);
	lines.push(`| **% Covered** | **${totals.percentCovered}%** |`);
	lines.push("");

	// Per-site breakdown
	lines.push("## Coverage Matrix");
	lines.push("");
	lines.push(
		"Legend: ✅ covered on all required browsers · 🟡 partial · ❌ missing",
	);
	lines.push("");

	// Collect unique flow ids in declared order
	const flowOrder: FlowId[] = [];
	for (const req of requiredMatrix) {
		if (!flowOrder.includes(req.flow)) flowOrder.push(req.flow);
	}

	const header = ["Site", ...flowOrder];
	lines.push(`| ${header.join(" | ")} |`);
	lines.push(`| ${header.map(() => "------").join(" | ")} |`);

	for (const site of sites) {
		const row: string[] = [`\`${site.id}\``];
		for (const flow of flowOrder) {
			const cell = report.cells.find(
				(c) => c.site === site.id && c.flow === flow,
			);
			if (!cell) {
				row.push("—");
				continue;
			}
			const icon =
				cell.status === "covered"
					? "✅"
					: cell.status === "partial"
						? "🟡"
						: "❌";
			const browsers =
				cell.status === "missing"
					? ""
					: ` ${cell.actualProjects.length}/${cell.requiredProjects.length}`;
			row.push(`${icon}${browsers}`);
		}
		lines.push(`| ${row.join(" | ")} |`);
	}
	lines.push("");

	// Gaps
	const gaps = report.cells.filter((c) => c.status !== "covered");
	if (gaps.length > 0) {
		lines.push("## Gaps");
		lines.push("");
		for (const gap of gaps) {
			const icon = gap.status === "missing" ? "❌" : "🟡";
			lines.push(`- ${icon} \`${gap.site}\` → \`${gap.flow}\` (${gap.status})`);
		}
		lines.push("");
	}

	lines.push("## Concepts");
	lines.push("");
	lines.push(
		"See [COVERAGE.md](./COVERAGE.md) for the full model — what a *cell* is, how to add a flow, and how this maps to the Playwright project matrix.",
	);
	lines.push("");

	const out = join(repoRoot, "COVERAGE_REPORT.md");
	writeFileSync(out, lines.join("\n"), "utf-8");
	// eslint-disable-next-line no-console
	console.log(`[coverage] wrote ${relative(repoRoot, out)}`);
}

// ─── entrypoint ───────────────────────────────────────────────────────────

function main(): void {
	mkdirSync(repoRoot, { recursive: true });
	const scanned = scanSpecs();
	const report = buildReport(scanned);
	emitJson(report);
	emitMarkdown(report);
	// eslint-disable-next-line no-console
	console.log(
		`[coverage] ${report.totals.covered}/${report.totals.required} cells covered (${report.totals.percentCovered}%)`,
	);
	if (report.totals.missing > 0) {
		process.exitCode = 0; // report-only, not a hard failure
	}
}

main();
