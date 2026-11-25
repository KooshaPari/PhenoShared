/**
 * Recorder fixture: parses `@user-story` frontmatter from the current
 * spec file, captures screenshots + ARIA snapshots on each moment,
 * and writes a `manifest.verified.json` conformant with the
 * Phenotype journey manifest schema (see `schema/manifest.schema.json`).
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, relative, resolve } from "node:path";
import type { Page, TestInfo } from "@playwright/test";

import {
  parseUserStoryFrontmatter,
  type UserStoryFrontmatter,
} from "./frontmatter.js";

export interface RecorderMoment {
  slug: string;
  intent: string;
  screenshot_path: string;
  aria_snapshot_path: string;
  structural_path: string;
}

export interface ManifestStep {
  index: number;
  slug: string;
  intent: string;
  screenshot_path: string;
  description?: string;
  assertions?: {
    structural_path: string;
  };
}

export interface VerifiedManifest {
  id: string;
  intent: string;
  title: string;
  persona: string;
  given: string;
  when: string[];
  then: string[];
  traces_to: string[];
  family: string;
  blind_judge: "auto" | "manual" | "off";
  recording: string | null;
  recording_gif: string | null;
  keyframe_count: number;
  passed: boolean;
  steps: ManifestStep[];
  verification: {
    generator: "phenotype-playwright-record";
    generator_version: string;
    verified_at: string;
  };
}

const PLUGIN_VERSION = "0.1.0";

export interface RecorderOptions {
  /**
   * Root directory where `target/user-stories/<journey_id>.manifest.json`
   * and supporting artefacts are written. Defaults to
   * `<cwd>/target`.
   */
  outputRoot?: string;
}

/**
 * Recorder instance scoped to a single Playwright test.
 *
 * Lifecycle:
 *   1. `await recorder.init(testInfo)` — parse frontmatter, prepare dirs.
 *   2. `await recorder.capture(page, 'slug', 'intent')` — manual capture.
 *   3. Auto-capture on `expect(...)` success via `attachExpect(expect)`.
 *   4. `await recorder.finalize()` — emit manifest.
 */
export class Recorder {
  public frontmatter!: UserStoryFrontmatter;
  private moments: RecorderMoment[] = [];
  private outDir!: string;
  private keyframesDir!: string;
  private snapshotsDir!: string;
  private manifestPath!: string;
  private passed = true;
  private recording: string | null = null;

  constructor(private readonly options: RecorderOptions = {}) {}

  async init(testInfo: TestInfo): Promise<void> {
    const source = await readFile(testInfo.file, "utf8");
    this.frontmatter = parseUserStoryFrontmatter(source);

    const root = resolve(
      this.options.outputRoot ??
        process.env.PHENOTYPE_USERSTORY_OUT ??
        join(process.cwd(), "target"),
    );
    this.outDir = join(root, "user-stories", this.frontmatter.journey_id);
    this.keyframesDir = join(this.outDir, "keyframes");
    this.snapshotsDir = join(this.outDir, "aria");
    this.manifestPath = join(
      root,
      "user-stories",
      `${this.frontmatter.journey_id}.manifest.json`,
    );

    await mkdir(this.keyframesDir, { recursive: true });
    await mkdir(this.snapshotsDir, { recursive: true });
  }

  /**
   * Capture a screenshot + ARIA snapshot of the current page state.
   * Safe to call multiple times; each call becomes one step.
   */
  async capture(page: Page, slug: string, intent: string): Promise<void> {
    if (!this.frontmatter.record) {
      return;
    }
    const idx = this.moments.length;
    const frameName = `frame-${String(idx + 1).padStart(3, "0")}.png`;
    const ariaName = `frame-${String(idx + 1).padStart(3, "0")}.aria.txt`;

    await page.screenshot({
      path: join(this.keyframesDir, frameName),
      fullPage: false,
    });

    let aria = "";
    try {
      aria = await page
        .locator("body")
        .ariaSnapshot({ mode: "default" } as any);
    } catch {
      // Some test contexts (e.g. static HTML served via file://) don't
      // support ARIA snapshots at the body level; fall back to HTML.
      try {
        aria = await page.content();
      } catch {
        aria = "";
      }
    }
    await writeFile(join(this.snapshotsDir, ariaName), aria, "utf8");

    this.moments.push({
      slug,
      intent,
      screenshot_path: `keyframes/${frameName}`,
      aria_snapshot_path: `aria/${ariaName}`,
      structural_path: `aria/${ariaName}`,
    });
  }

  /**
   * Wrap a Playwright `expect` instance so each successful assertion
   * triggers an auto-capture. Returns a proxy that should be used in
   * place of the raw `expect`.
   *
   * Note: users can also call `capture()` directly for named moments.
   */
  wireAutoCapture(page: Page, baseExpect: any): any {
    const self = this;
    let autoIdx = 0;
    return new Proxy(baseExpect, {
      apply(target, thisArg, args) {
        const assertion = Reflect.apply(target, thisArg, args);
        return new Proxy(assertion as object, {
          get(aTarget, prop, aReceiver) {
            const orig = Reflect.get(aTarget, prop, aReceiver);
            if (typeof orig !== "function") {
              return orig;
            }
            return (...callArgs: unknown[]) => {
              const res = (orig as Function).apply(aTarget, callArgs);
              if (res && typeof (res as Promise<unknown>).then === "function") {
                return (res as Promise<unknown>).then(async (v) => {
                  await self
                    .capture(
                      page,
                      `auto-${++autoIdx}`,
                      `expect(...).${String(prop)} satisfied`,
                    )
                    .catch(() => undefined);
                  return v;
                });
              }
              return res;
            };
          },
        });
      },
    });
  }

  markFailed(): void {
    this.passed = false;
  }

  attachVideo(path: string | null): void {
    this.recording = path;
  }

  async finalize(testInfo?: TestInfo): Promise<VerifiedManifest> {
    if (testInfo && testInfo.status && testInfo.status !== "passed") {
      this.passed = false;
    }

    // Best-effort: pick up attached video from Playwright's trace output.
    if (!this.recording && testInfo) {
      for (const attach of testInfo.attachments ?? []) {
        if (attach.contentType?.startsWith("video/") && attach.path) {
          this.recording = relative(this.outDir, attach.path);
          break;
        }
      }
    }

    const steps: ManifestStep[] = this.moments.map((m, index) => ({
      index,
      slug: m.slug,
      intent: m.intent,
      screenshot_path: m.screenshot_path,
      assertions: {
        structural_path: m.structural_path,
      },
    }));

    const manifest: VerifiedManifest = {
      id: this.frontmatter.journey_id,
      intent: this.frontmatter.title,
      title: this.frontmatter.title,
      persona: this.frontmatter.persona,
      given: this.frontmatter.given,
      when: this.frontmatter.when,
      then: this.frontmatter.then,
      traces_to: this.frontmatter.traces_to,
      family: this.frontmatter.family,
      blind_judge: this.frontmatter.blind_judge,
      recording: this.recording,
      recording_gif: null,
      keyframe_count: this.moments.length,
      passed: this.passed,
      steps,
      verification: {
        generator: "phenotype-playwright-record",
        generator_version: PLUGIN_VERSION,
        verified_at: new Date().toISOString(),
      },
    };

    await mkdir(dirname(this.manifestPath), { recursive: true });
    await writeFile(
      this.manifestPath,
      JSON.stringify(manifest, null, 2) + "\n",
      "utf8",
    );
    // Also drop a copy inside the journey dir for co-located consumers.
    await writeFile(
      join(this.outDir, "manifest.verified.json"),
      JSON.stringify(manifest, null, 2) + "\n",
      "utf8",
    );
    return manifest;
  }
}
