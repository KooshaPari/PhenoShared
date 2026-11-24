/**
 * Recorder integration test — uses a mock Playwright `Page` backed
 * by an in-memory static HTML string. We don't spin up a real browser
 * here (that's Batch 3's e2e coverage); instead we validate that the
 * Recorder produces a schema-conformant manifest from the frontmatter
 * + captured moments.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { mkdtemp, readFile, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Recorder } from "../src/recorder";

const SPEC = `/**
 * @user-story
 * ---
 * journey_id: fixture-journey
 * title: Fixture journey
 * persona: Test runner
 * given: static HTML fixture loaded
 * when:
 *   - render landing
 *   - click next
 * then:
 *   - url settles on /done
 * traces_to: [FR-FIX-001]
 * record: true
 * blind_judge: auto
 * family: fixture
 * ---
 */
`;

function makeMockPage(html: string): any {
  return {
    async screenshot({ path }: { path: string }) {
      // Write a minimal PNG header so the file exists and is nonzero.
      await writeFile(path, Buffer.from([0x89, 0x50, 0x4e, 0x47]));
    },
    locator(_sel: string) {
      return {
        async ariaSnapshot(_opts: unknown) {
          return `- document:\n  - heading: "Fixture"\n`;
        },
      };
    },
    async content() {
      return html;
    },
  };
}

function makeTestInfo(specPath: string, outRoot: string): any {
  return {
    file: specPath,
    status: "passed",
    attachments: [] as unknown[],
    __outRoot: outRoot,
  };
}

describe("Recorder", () => {
  let tmp: string;
  let specPath: string;
  let outRoot: string;

  beforeEach(async () => {
    tmp = await mkdtemp(join(tmpdir(), "phenotype-rec-"));
    specPath = join(tmp, "spec.ts");
    outRoot = join(tmp, "target");
    await writeFile(specPath, SPEC, "utf8");
    await mkdir(outRoot, { recursive: true });
  });

  it("produces a schema-conformant manifest.json against a static fixture", async () => {
    const recorder = new Recorder({ outputRoot: outRoot });
    const info = makeTestInfo(specPath, outRoot);
    await recorder.init(info);

    const page = makeMockPage("<html><body><h1>Fixture</h1></body></html>");
    await recorder.capture(page, "landing", "landing rendered");
    await recorder.capture(page, "next-clicked", "next clicked");

    const manifest = await recorder.finalize(info);

    expect(manifest.id).toBe("fixture-journey");
    expect(manifest.title).toBe("Fixture journey");
    expect(manifest.persona).toBe("Test runner");
    expect(manifest.when).toEqual(["render landing", "click next"]);
    expect(manifest.then).toEqual(["url settles on /done"]);
    expect(manifest.traces_to).toEqual(["FR-FIX-001"]);
    expect(manifest.keyframe_count).toBe(2);
    expect(manifest.passed).toBe(true);
    expect(manifest.steps).toHaveLength(2);
    expect(manifest.steps[0]).toMatchObject({
      index: 0,
      slug: "landing",
      intent: "landing rendered",
    });
    expect(manifest.steps[0].screenshot_path).toMatch(/keyframes\/frame-001\.png/);
    expect(manifest.steps[0].assertions?.structural_path).toMatch(/aria\/frame-001/);
    expect(manifest.verification.generator).toBe("phenotype-playwright-record");

    // The primary manifest path should exist.
    const primary = join(outRoot, "user-stories", "fixture-journey.manifest.json");
    const raw = await readFile(primary, "utf8");
    const parsed = JSON.parse(raw);
    expect(parsed.id).toBe("fixture-journey");

    // Co-located copy inside the journey dir.
    const colocated = join(
      outRoot,
      "user-stories",
      "fixture-journey",
      "manifest.verified.json",
    );
    const rawCo = await readFile(colocated, "utf8");
    expect(JSON.parse(rawCo).id).toBe("fixture-journey");

    await rm(tmp, { recursive: true, force: true });
  });

  it("marks manifest as failed when testInfo reports failure", async () => {
    const recorder = new Recorder({ outputRoot: outRoot });
    const info = makeTestInfo(specPath, outRoot);
    info.status = "failed";
    await recorder.init(info);

    const page = makeMockPage("<html></html>");
    await recorder.capture(page, "only-step", "something");
    const manifest = await recorder.finalize(info);

    expect(manifest.passed).toBe(false);
    await rm(tmp, { recursive: true, force: true });
  });

  it("skips capture when record=false", async () => {
    const SPEC_NORECORD = SPEC.replace("record: true", "record: false");
    await writeFile(specPath, SPEC_NORECORD, "utf8");

    const recorder = new Recorder({ outputRoot: outRoot });
    const info = makeTestInfo(specPath, outRoot);
    await recorder.init(info);

    const page = makeMockPage("<html></html>");
    await recorder.capture(page, "ignored", "ignored");
    const manifest = await recorder.finalize(info);

    expect(manifest.keyframe_count).toBe(0);
    expect(manifest.steps).toHaveLength(0);
    await rm(tmp, { recursive: true, force: true });
  });
});
