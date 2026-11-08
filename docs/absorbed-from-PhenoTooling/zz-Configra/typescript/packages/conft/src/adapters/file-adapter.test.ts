/**
 * Tests for FileConfigSource caching, write, and error handling.
 *
 * Addresses L15/L17 (full-file reparse per key) and L25 (runtime safety
 * — turn raw JSON.parse exceptions into typed errors).
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtemp, readFile, writeFile } from 'fs/promises';
import { tmpdir } from 'os';
import { join } from 'path';
import {
  ConfigSourceNotFoundError,
  ConfigValidationError,
  FileConfigSource,
} from './file-adapter';

let dir: string;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'conft-file-'));
});

afterEach(async () => {
  // mkdtemp returns a unique dir per test; nothing to clean explicitly —
  // the OS reclaims it. Reset env vars in case a test set them.
});

describe('FileConfigSource — caching', () => {
  it('caches entries so the file is read at most once across many gets', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({ a: 1, b: 2, c: 3 }), 'utf-8');

    const source = new FileConfigSource(file);

    // Spy on the private read path by wrapping fs.readFile is invasive;
    // instead, use load() count via the public surface — get() after load()
    // must not re-read. We assert this by mutating the file on disk and
    // confirming get() still returns the original (cached) value.
    await source.load();
    await expect(source.get('a')).resolves.toBe(1);

    await writeFile(file, JSON.stringify({ a: 999 }), 'utf-8');

    // Cache must shield the caller from the on-disk mutation.
    await expect(source.get('a')).resolves.toBe(1);
  });

  it('re-reads after invalidate()', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({ a: 1 }), 'utf-8');

    const source = new FileConfigSource(file);
    await source.load();
    await expect(source.get('a')).resolves.toBe(1);

    await writeFile(file, JSON.stringify({ a: 2 }), 'utf-8');
    source.invalidate();

    await expect(source.get('a')).resolves.toBe(2);
  });

  it('reload() forces a synchronous refresh and returns the new entries', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({ a: 1 }), 'utf-8');

    const source = new FileConfigSource(file);
    await source.load();

    await writeFile(file, JSON.stringify({ a: 2, b: 3 }), 'utf-8');

    const fresh = await source.reload();
    expect(fresh.map((e) => e.key).sort()).toEqual(['a', 'b']);
    await expect(source.get('b')).resolves.toBe(3);
  });

  it('hydrate() seeds the cache without touching disk', async () => {
    const source = new FileConfigSource(join(dir, 'never-read.json'));
    source.hydrate([['seeded', 'value']]);
    await expect(source.get('seeded')).resolves.toBe('value');
  });
});

describe('FileConfigSource — write', () => {
  it('set() persists to disk and updates the cache', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({ a: 1 }), 'utf-8');

    const source = new FileConfigSource(file);
    await source.load();

    await source.set('b', 2);

    // On-disk contents include the new key.
    const onDisk = JSON.parse(await readFile(file, 'utf-8'));
    expect(onDisk).toEqual({ a: 1, b: 2 });

    // And the cache serves the new value without a re-read.
    await writeFile(file, JSON.stringify({ a: 999 }), 'utf-8'); // mutate externally
    await expect(source.get('b')).resolves.toBe(2);
  });

  it('set() rejects values that are not valid ConfigValues', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({}), 'utf-8');

    const source = new FileConfigSource(file);

    // null is not a valid ConfigValue — must be rejected.
    await expect(source.set('key', null as never)).rejects.toBeInstanceOf(ConfigValidationError);
    // undefined is not a valid ConfigValue — must be rejected.
    await expect(source.set('key2', undefined as never)).rejects.toBeInstanceOf(ConfigValidationError);
  });

  it('set() rejects nested objects that are not string-valued records', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({}), 'utf-8');

    const source = new FileConfigSource(file);

    // Objects must be string-valued records (ConfigValueSchema). Mixed-type
    // values should be rejected at write time so the file stays internally
    // consistent.
    await expect(source.set('key', { a: 1 } as never)).rejects.toBeInstanceOf(ConfigValidationError);
  });
});

describe('FileConfigSource — typed errors', () => {
  it('throws ConfigSourceNotFoundError for a missing file', async () => {
    const source = new FileConfigSource(join(dir, 'does-not-exist.json'));
    await expect(source.load()).rejects.toBeInstanceOf(ConfigSourceNotFoundError);
  });

  it('throws ConfigValidationError for malformed JSON', async () => {
    const file = join(dir, 'broken.json');
    await writeFile(file, '{ this is : not, valid json', 'utf-8');

    const source = new FileConfigSource(file);
    await expect(source.load()).rejects.toBeInstanceOf(ConfigValidationError);
  });

  it('throws ConfigValidationError when root is not a JSON object', async () => {
    const file = join(dir, 'array.json');
    await writeFile(file, JSON.stringify(['a', 'b']), 'utf-8');

    const source = new FileConfigSource(file);
    await expect(source.load()).rejects.toBeInstanceOf(ConfigValidationError);
  });
});

describe('FileConfigSource — concurrent load de-duplication', () => {
  it('shares a single disk read across concurrent callers', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({ a: 1 }), 'utf-8');

    const source = new FileConfigSource(file);

    // Fire 5 concurrent gets before the first load completes.
    const results = await Promise.all([
      source.get('a'),
      source.get('a'),
      source.get('a'),
      source.get('a'),
      source.get('a'),
    ]);

    expect(results).toEqual([1, 1, 1, 1, 1]);
    // De-duplication must coalesce concurrent reads into a single call.
    expect(source.getReadCount()).toBe(1);
  });

  it('coalesces a load() racing with concurrent get()s into one read', async () => {
    const file = join(dir, 'config.json');
    await writeFile(file, JSON.stringify({ a: 1, b: 2 }), 'utf-8');

    const source = new FileConfigSource(file);
    await Promise.all([source.load(), source.get('a'), source.get('b')]);

    expect(source.getReadCount()).toBe(1);
  });
});