import assert from 'node:assert/strict';
import { createSiteMeta } from '../helpers/site-meta.mjs';

const meta = createSiteMeta();

assert.equal(meta.docsRoot, '/docs/');
assert.equal(meta.locales.root, '/');
assert.equal(meta.locales['zh-CN'], '/zh-CN/');
assert.equal(meta.locales['zh-TW'], '/zh-TW/');
assert.equal(meta.locales.fa, '/fa/');
assert.equal(meta.locales['fa-Latn'], '/fa-Latn/');
