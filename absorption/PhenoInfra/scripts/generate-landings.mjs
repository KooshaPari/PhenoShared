#!/usr/bin/env node
/**
 * Phenotype Landing Generator
 *
 * Generates landing pages from project configuration files.
 *
 * Pattern: Each project repo should have a `.phenotype/landing.json` or
 * `docs/landing.json` file that describes the landing page content.
 * This script reads from those files (via GitHub API) and generates
 * Astro landing pages using the template in `templates/landing/`.
 *
 * Usage:
 *   node scripts/generate-landings.mjs
 *
 * Environment:
 *   GITHUB_TOKEN — GitHub API token (raises rate limit to 5000/hr)
 */

import { writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SITES_DIR = resolve(ROOT, "sites");
const TEMPLATE_DIR = resolve(ROOT, "templates", "landing");

const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
const headers = {
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": "phenotype-landing-generator",
};
if (token) headers.Authorization = `Bearer ${token}`;

const PROJECTS = [
  { repo: "BytePort", site: "byteport-landing" },
  { repo: "Phenokits", site: "phenokits-landing" },
  { repo: "AgilePlus", site: "agileplus-landing" },
  { repo: "HWLedger", site: "hwledger-landing" },
  { repo: "thegent", site: "thegent-landing" },
];

async function fetchConfig(owner, repo) {
  const paths = [
    `.phenotype/landing.json`,
    `docs/landing.json`,
    `.github/landing.json`,
  ];

  for (const path of paths) {
    const url = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
    try {
      const res = await fetch(url, { headers });
      if (!res.ok) continue;
      const json = await res.json();
      if (json.content) {
        const decoded = Buffer.from(json.content, "base64").toString("utf8");
        return JSON.parse(decoded);
      }
    } catch {
      continue;
    }
  }

  return null;
}

async function generateSite(project) {
  const { repo, site } = project;
  const config = await fetchConfig("KooshaPari", repo);

  if (!config) {
    console.warn(`No landing config found for ${repo} — skipping generation`);
    return false;
  }

  const siteDir = resolve(SITES_DIR, site);
  await mkdir(siteDir, { recursive: true });

  // Write config.json
  const dataDir = resolve(siteDir, "data");
  await mkdir(dataDir, { recursive: true });
  await writeFile(
    resolve(dataDir, "config.json"),
    JSON.stringify(config, null, 2) + "\n",
    "utf8"
  );

  // Copy template files ( Astro page, styles, etc. )
  // For now, we just write a minimal index.astro that imports the shared template
  const indexAstro = `---
import { Hero, Features, CTA, Footer, Header } from '@phenotype/landing-ui';
import config from '../data/config.json';

const { brand, hero, features, cta, footer, header } = config;
---

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{brand.name} — {brand.tagline}</title>
  <meta name="description" content={brand.description} />
</head>
<body>
  <Header brand={brand.name} links={header?.links ?? []} />
  <Hero title={hero.title} subtitle={hero.subtitle} cta={hero.cta} />
  <Features title={features.title} features={features.items} />
  <CTA text={cta.text} href={cta.href} secondary={cta.secondary} />
  <Footer brand={brand.name} links={footer?.links ?? []} />
</body>
</html>

<style is:global>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Inter', system-ui, sans-serif; color: var(--pheno-dark, #0f172a); background: white; line-height: 1.6; }
</style>
`;

  await writeFile(resolve(siteDir, "src/pages/index.astro"), indexAstro, "utf8");

  // Write package.json if it doesn't exist
  const pkgPath = resolve(siteDir, "package.json");
  let pkgExists = true;
  try {
    await import("node:fs/promises").then((fs) => fs.access(pkgPath));
  } catch {
    pkgExists = false;
  }

  if (!pkgExists) {
    const pkg = {
      name: site,
      version: "0.1.0",
      private: true,
      type: "module",
      scripts: {
        dev: "astro dev",
        build: "astro build",
        preview: "astro preview",
        check: "astro check",
      },
      dependencies: {
        astro: "^6.1.9",
        "@phenotype/landing-ui": "github:KooshaPari/phenoDesign",
        "@phenotype/design-tokens": "github:KooshaPari/phenoDesign",
      },
      devDependencies: {
        "@types/node": "^25.6.0",
      },
    };
    await writeFile(pkgPath, JSON.stringify(pkg, null, 2) + "\n", "utf8");
  }

  console.log(`Generated ${site} from ${repo} config`);
  return true;
}

async function main() {
  let generated = 0;
  for (const project of PROJECTS) {
    const ok = await generateSite(project);
    if (ok) generated++;
  }
  console.log(`\nGenerated ${generated}/${PROJECTS.length} landing sites`);
}

main().catch((err) => {
  console.error("generate-landings failed:", err.message);
  process.exit(1);
});
