import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const config = readFileSync(join(process.cwd(), 'docs/.vitepress/config.mts'), 'utf8');

assert.ok(config.includes('themeConfig'));
assert.ok(config.includes('Branch Protection'));
assert.ok(config.includes('Upgrade'));
