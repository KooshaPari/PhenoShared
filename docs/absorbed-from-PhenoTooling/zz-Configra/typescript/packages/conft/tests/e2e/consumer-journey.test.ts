/**
 * E2E smoke test for @phenotype/config-ts.
 *
 * Exercises the consumer's full user journey against the built package:
 *   1. Import from the built artifact (dist/index.mjs) — proves the package
 *      is publishable and the public exports resolve correctly.
 *   2. Construct an EnvConfigSource — the primary runtime source.
 *   3. Read entries via load() and a value via get().
 *   4. Validate returned values with the exported Zod schema.
 *
 * NOTE: Conft is a library with no UI or server. Web-app E2E (Playwright) is
 * N/A here — see FLEET-AUDIT-30-PILLAR.md T3 (UI pillars) for the reason
 * (N/A = 3 for library / CLI repos). This "consumer journey" is the
 * library-equivalent: a downstream package would import from dist/, build
 * a source, read values, and validate. That import-and-validate flow is
 * the T3 surface for a library.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { writeFile, mkdtemp, rm } from 'fs/promises';
import { createRequire } from 'module';
import { tmpdir } from 'os';
import { join } from 'path';
import {
  EnvConfigSource,
  FileConfigSource,
  ConfigValueSchema,
  ConfigValidationError,
  ImmutableConfig,
  type ConfigSource,
  type ConfigValue,
} from '../../dist/index.mjs';

describe('@phenotype/config-ts — E2E consumer journey', () => {
  let tmpDir: string;
  let tmpFile: string;

  beforeAll(async () => {
    tmpDir = await mkdtemp(join(tmpdir(), 'conft-e2e-'));
    tmpFile = join(tmpDir, 'config.json');
    await writeFile(
      tmpFile,
      JSON.stringify({ feature: 'on', retries: 3, nested: { a: '1' } }),
      'utf-8',
    );
  });

  afterAll(async () => {
    await rm(tmpDir, { recursive: true, force: true });
  });

  it('exports the documented API from the built package', () => {
    const require = createRequire(import.meta.url);
    const commonJs = require('../../dist/index.js');

    expect(EnvConfigSource).toBeDefined();
    expect(FileConfigSource).toBeDefined();
    expect(ConfigValueSchema).toBeDefined();
    expect(ConfigValidationError).toBeDefined();
    expect(ImmutableConfig).toBeDefined();
    expect(commonJs.EnvConfigSource).toBeDefined();
    expect(commonJs.FileConfigSource).toBeDefined();
  });

  it('validates every supported value shape and rejects unsupported shapes', () => {
    for (const value of [
      'hello',
      42,
      true,
      ['a', 'b'],
      { k1: 'v1', k2: 'v2' },
    ]) {
      expect(ConfigValueSchema.parse(value)).toEqual(value);
    }

    for (const value of [null, ['a', 2], { nested: { value: 'no' } }]) {
      expect(ConfigValueSchema.safeParse(value).success).toBe(false);
    }
  });

  it('serializes validation errors without losing diagnostic context', () => {
    const error = new ConfigValidationError(
      'invalid port',
      ['server', 'port'],
      'abc',
      { source: 'env' },
    );

    expect(error.name).toBe('ConfigValidationError');
    expect(error.toJSON()).toEqual({
      message: 'invalid port',
      path: ['server', 'port'],
      value: 'abc',
      context: { source: 'env' },
    });
  });

  it('loads all JSON entries with file provenance', async () => {
    const entries = await new FileConfigSource(tmpFile).load();

    expect(entries.map((entry) => entry.key).sort()).toEqual([
      'feature',
      'nested',
      'retries',
    ]);
    for (const entry of entries) {
      expect(entry.source).toBe('file');
      expect(entry.timestamp).toEqual(expect.any(Number));
    }
  });

  it('reads named JSON values and enforces read-only behavior', async () => {
    const source = new FileConfigSource(tmpFile);

    expect(await source.get('feature')).toBe('on');
    expect(await source.get('retries')).toBe(3);
    expect(await source.get('missing')).toBeUndefined();
    expect(source.isWritable()).toBe(false);
    await expect(source.set('feature', 'off')).rejects.toThrow(
      'File configuration sources are read-only',
    );
  });

  it('loads only prefixed environment values and normalizes keys', async () => {
    process.env.APP_FOO = 'bar';
    process.env.APP_BAZ = 'qux';
    process.env.UNRELATED = 'skip';
    try {
      const source = new EnvConfigSource('APP_');
      const entries = await source.load();
      const keys = entries.map((e) => e.key).sort();
      expect(keys).toEqual(['baz', 'foo']);
      const foo = entries.find((e) => e.key === 'foo');
      expect(foo?.value).toBe('bar');
      expect(foo?.source).toBe('env');
    } finally {
      delete process.env.APP_FOO;
      delete process.env.APP_BAZ;
      delete process.env.UNRELATED;
    }
  });

  it('parses supported environment value shapes without unsafe coercion', async () => {
    const values: Record<string, [string, ConfigValue]> = {
      STRING: ['on', 'on'],
      TRUE: ['true', true],
      FALSE: ['FALSE', false],
      NUMBER: ['5.5', 5.5],
      ARRAY: ['["a","b"]', ['a', 'b']],
      RECORD: ['{"a":"b"}', { a: 'b' }],
      EMPTY: ['', ''],
      INFINITY: ['Infinity', 'Infinity'],
      UNSUPPORTED_JSON: ['[1,2]', '[1,2]'],
    };
    for (const [key, [raw]] of Object.entries(values)) {
      process.env[`APP_${key}`] = raw;
    }

    try {
      const source = new EnvConfigSource('APP_');
      for (const [key, [, expected]] of Object.entries(values)) {
        expect(await source.get(key)).toEqual(expected);
      }
    } finally {
      for (const key of Object.keys(values)) delete process.env[`APP_${key}`];
    }
  });

  it('reports absent environment values and rejects writes', async () => {
    const source = new EnvConfigSource('TRACE_TEST_');

    expect(await source.get('ABSENT')).toBeUndefined();
    expect(source.isWritable()).toBe(false);
    await expect(source.set('KEY', 'value')).rejects.toThrow(
      'Environment variables are read-only',
    );
  });

  it('provides immutable lookups and detached snapshots', () => {
    const inputEntries = new Map<string, ConfigValue>([['feature', 'on']]);
    const inputSources = ['file'];
    const config = new ImmutableConfig(inputEntries, inputSources, 'v1');

    inputEntries.set('feature', 'mutated');
    inputSources.push('env');
    expect(config.get('feature')).toBe('on');
    expect(config.has('feature')).toBe(true);
    expect(config.has('missing')).toBe(false);

    const snapshot = config.toSnapshot();
    expect(snapshot).toMatchObject({
      entries: { feature: 'on' },
      sources: ['file'],
      version: 'v1',
    });
    expect(snapshot.timestamp).toEqual(expect.any(Number));
    snapshot.sources.push('mutated');
    expect(config.sources).toEqual(['file']);
  });

  it('adapters satisfy the asynchronous source port', async () => {
    const loadThroughPort = async (source: ConfigSource) => source.load();
    const filePromise = loadThroughPort(new FileConfigSource(tmpFile));
    const envPromise = loadThroughPort(new EnvConfigSource('TRACE_NONE_'));

    expect(filePromise).toBeInstanceOf(Promise);
    expect(envPromise).toBeInstanceOf(Promise);
    await expect(filePromise).resolves.toHaveLength(3);
    await expect(envPromise).resolves.toEqual([]);
  });
});
