/**
 * Playwright -> Phenotype journey manifest bridge.
 *
 * Usage:
 *
 *   import { record } from "@phenotype/journey-playwright";
 *   import { chromium } from "playwright";
 *
 *   const browser = await chromium.launch();
 *   const page = await browser.newPage();
 *   await record({
 *     id: "first-plan",
 *     intent: "Run your first plan",
 *     outDir: "./artefacts",
 *     page,
 *     steps: [
 *       { intent: "Open the dashboard", action: async (p) => await p.goto("http://localhost:3000") },
 *       { intent: "Click run", action: async (p) => await p.getByRole("button", { name: "Run" }).click() }
 *     ]
 *   });
 *   await browser.close();
 */
import type { Page } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

export interface JourneyStep {
  intent: string;
  action: (page: Page) => Promise<void>;
  /** Optional slug; defaults to `frame-<index>`. */
  slug?: string;
}

export interface JourneySpec {
  id: string;
  intent: string;
  /** Directory under which `recordings/`, `keyframes/<id>/`, `manifests/<id>/` are written. */
  outDir: string;
  page: Page;
  steps: JourneyStep[];
}

export interface ManifestStep {
  index: number;
  slug: string;
  intent: string;
  screenshot_path: string;
}

export interface Manifest {
  id: string;
  intent: string;
  recording: string | null;
  recording_gif: string | null;
  keyframe_count: number;
  passed: boolean;
  steps: ManifestStep[];
}

/**
 * Execute each step, capture a screenshot per step, and write a
 * Phenotype-conformant `manifest.json`.
 */
export async function record(spec: JourneySpec): Promise<Manifest> {
  const keyframesDir = join(spec.outDir, "keyframes", spec.id);
  const manifestDir = join(spec.outDir, "manifests", spec.id);
  await mkdir(keyframesDir, { recursive: true });
  await mkdir(manifestDir, { recursive: true });

  const manifestSteps: ManifestStep[] = [];
  let passed = true;

  for (let i = 0; i < spec.steps.length; i++) {
    const step = spec.steps[i];
    const slug = step.slug ?? `frame-${i}`;
    const filename = `frame-${String(i + 1).padStart(3, "0")}.png`;
    try {
      await step.action(spec.page);
      await spec.page.screenshot({ path: join(keyframesDir, filename), fullPage: false });
      manifestSteps.push({ index: i, slug, intent: step.intent, screenshot_path: filename });
    } catch (err) {
      passed = false;
      manifestSteps.push({
        index: i,
        slug,
        intent: `${step.intent} (FAILED: ${(err as Error).message})`,
        screenshot_path: filename
      });
      break;
    }
  }

  const manifest: Manifest = {
    id: spec.id,
    intent: spec.intent,
    recording: null,
    recording_gif: null,
    keyframe_count: manifestSteps.length,
    passed,
    steps: manifestSteps
  };

  await writeFile(
    join(manifestDir, "manifest.json"),
    JSON.stringify(manifest, null, 2),
    "utf8"
  );

  return manifest;
}
