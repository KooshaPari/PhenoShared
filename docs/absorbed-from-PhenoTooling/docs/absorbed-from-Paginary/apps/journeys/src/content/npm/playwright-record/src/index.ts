/**
 * `@phenotype/playwright-record` — Playwright test wrapper that emits
 * verified user-story manifests from `@user-story` JSDoc frontmatter.
 *
 * Usage:
 *
 *   import { test, expect } from '@phenotype/playwright-record';
 *
 *   test('hf-search to planner handoff', async ({ page, recorder }) => {
 *     await page.goto('/HF_Search');
 *     await recorder.capture(page, 'landing', 'Search page rendered');
 *     // ... drive interactions ...
 *     // recorder.finalize() is called automatically in afterEach.
 *   });
 */
import {
  test as base,
  expect as baseExpect,
  type TestInfo,
} from "@playwright/test";

import { Recorder, type RecorderOptions } from "./recorder.js";

export { Recorder } from "./recorder.js";
export type {
  RecorderOptions,
  VerifiedManifest,
  ManifestStep,
  RecorderMoment,
} from "./recorder.js";
export {
  parseUserStoryFrontmatter,
  extractUserStoryBlock,
  unwrapYamlBody,
  validate as validateFrontmatter,
  FrontmatterError,
  type UserStoryFrontmatter,
} from "./frontmatter.js";

type Fixtures = {
  recorder: Recorder;
  recorderOptions: RecorderOptions;
};

export const test = base.extend<Fixtures>({
  recorderOptions: [{}, { option: true }],

  recorder: async ({ recorderOptions }, use, testInfo: TestInfo) => {
    const recorder = new Recorder(recorderOptions);
    await recorder.init(testInfo);
    await use(recorder);
    await recorder.finalize(testInfo);
  },
});

export const expect = baseExpect;
