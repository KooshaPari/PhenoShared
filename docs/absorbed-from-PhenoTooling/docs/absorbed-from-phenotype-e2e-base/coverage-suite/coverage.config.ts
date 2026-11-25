/**
 * Declarative coverage matrix for the Phenotype E2E suite.
 *
 * This file is the single source of truth for "what should be tested".
 * The generator script (./generate-report.ts) reads it, cross-references
 * the actual test specs, and emits:
 *   - coverage.json  — machine-readable matrix
 *   - COVERAGE.md    — human-readable coverage report
 *
 * Schema:
 *   sites[]                — landing pages under test
 *   flows[]                — user journeys / component checks per site
 *   requiredProjects[]     — Playwright projects (browsers) each flow must run on
 *
 * Adding a new site or flow here is a deliberate, reviewed action.
 * Removing one is a coverage regression and must be justified in the PR.
 */

export type SiteId =
	| "byteport"
	| "phenokits"
	| "agileplus"
	| "projects"
	| "kooshapari";

export type FlowId =
	| "hero-cta"
	| "github-stats"
	| "footer-year"
	| "nav-links"
	| "a11y-baseline";

/** Sites under test — keys must match the `gotoLanding` fixture URLs. */
export const sites: ReadonlyArray<{ id: SiteId; url: string }> = [
	{ id: "byteport", url: "https://byteport.kooshapari.com" },
	{ id: "phenokits", url: "https://phenokits.kooshapari.com" },
	{ id: "agileplus", url: "https://agileplus.kooshapari.com" },
	{ id: "projects", url: "https://projects.kooshapari.com" },
	{ id: "kooshapari", url: "https://kooshapari.com" },
];

/**
 * Required flows × sites. The "x" denotes a flow that MUST be tested
 * for the given site. A flow exercised on one site is intentionally
 * NOT inherited — every site has its own hero / footer / stats and
 * each must be independently covered.
 */
export const requiredMatrix: ReadonlyArray<{
	site: SiteId;
	flow: FlowId;
	requiredProjects: ReadonlyArray<"chromium" | "firefox" | "webkit">;
}> = [
	{
		site: "byteport",
		flow: "hero-cta",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "byteport",
		flow: "github-stats",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "byteport",
		flow: "footer-year",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "byteport",
		flow: "nav-links",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{ site: "byteport", flow: "a11y-baseline", requiredProjects: ["chromium"] },

	{
		site: "phenokits",
		flow: "hero-cta",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "phenokits",
		flow: "github-stats",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "phenokits",
		flow: "footer-year",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{ site: "phenokits", flow: "nav-links", requiredProjects: ["chromium"] },

	{
		site: "agileplus",
		flow: "hero-cta",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "agileplus",
		flow: "github-stats",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "agileplus",
		flow: "footer-year",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{ site: "agileplus", flow: "nav-links", requiredProjects: ["chromium"] },

	{
		site: "projects",
		flow: "hero-cta",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "projects",
		flow: "footer-year",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{ site: "projects", flow: "nav-links", requiredProjects: ["chromium"] },

	{
		site: "kooshapari",
		flow: "hero-cta",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{
		site: "kooshapari",
		flow: "footer-year",
		requiredProjects: ["chromium", "firefox", "webkit"],
	},
	{ site: "kooshapari", flow: "nav-links", requiredProjects: ["chromium"] },
];

/** The Playwright project names that this harness actually runs. */
export const activeProjects = ["chromium", "firefox", "webkit"] as const;
