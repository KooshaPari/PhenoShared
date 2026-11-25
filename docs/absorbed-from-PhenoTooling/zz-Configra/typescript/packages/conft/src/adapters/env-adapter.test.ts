/**
 * Tests for EnvConfigSource value parsing and edge cases.
 *
 * Addresses v37 audit findings:
 * - L25/L20: null-injection via JSON.parse("null") returning JS null instead
 *   of the string "null", producing a value outside ConfigValueSchema.
 * - Type safety: arrays with non-string elements and records with non-string
 *   values are filtered to match ConfigValueSchema at parse time.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { EnvConfigSource } from './env-adapter';

const PREFIX = 'CONFT_';
const KEYS: string[] = [];

function setEnv(key: string, value: string): void {
  const fullKey = PREFIX + key;
  process.env[fullKey] = value;
  KEYS.push(fullKey);
}

afterEach(() => {
  for (const k of KEYS) process.env[k] = undefined as unknown as string;
  KEYS.length = 0;
});

describe('EnvConfigSource parseValue — null handling', () => {
  it('treats the string "null" as the string "null", not JS null', async () => {
    setEnv('MY_VAL', 'null');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('my_val');
    // The literal env string "null" must NOT produce JavaScript null
    // (which is outside ConfigValueSchema). It must be the string "null".
    expect(value).toBe('null');
    expect(typeof value).toBe('string');
  });

  it('treats the string "undefined" as the string, not undefined', async () => {
    setEnv('MY_VAL', 'undefined');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('my_val');
    expect(value).toBe('undefined');
    expect(typeof value).toBe('string');
  });
});

describe('EnvConfigSource parseValue — array element safety', () => {
  it('filters non-string elements from JSON arrays', async () => {
    setEnv('ARR', '["a",1,true,null]');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('arr');
    expect(Array.isArray(value)).toBe(true);
    // Non-string elements must be filtered out
    expect(value).toEqual(['a']);
  });

  it('returns an empty array when all elements are non-string', async () => {
    setEnv('ARR', '[1,2,3]');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('arr');
    expect(value).toEqual([]);
  });
});

describe('EnvConfigSource parseValue — record value safety', () => {
  it('filters non-string values from JSON records', async () => {
    setEnv('CFG', '{"a":"str","b":42,"c":true}');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('cfg');
    expect(value).toEqual({ a: 'str' });
  });

  it('returns an empty record when all values are non-string', async () => {
    setEnv('CFG', '{"a":1,"b":true}');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('cfg');
    expect(value).toEqual({});
  });
});

describe('EnvConfigSource parseValue — normal parsing preserved', () => {
  it('still parses JSON objects with string values', async () => {
    setEnv('CFG', '{"host":"localhost","port":"8080"}');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('cfg');
    expect(value).toEqual({ host: 'localhost', port: '8080' });
  });

  it('still parses JSON arrays of strings', async () => {
    setEnv('ARR', '["x","y","z"]');
    const source = new EnvConfigSource(PREFIX);
    const value = await source.get('arr');
    expect(value).toEqual(['x', 'y', 'z']);
  });

  it('still parses booleans', async () => {
    setEnv('FLAG', 'true');
    const source = new EnvConfigSource(PREFIX);
    await expect(source.get('flag')).resolves.toBe(true);
  });

  it('still parses numbers', async () => {
    setEnv('CNT', '42');
    const source = new EnvConfigSource(PREFIX);
    await expect(source.get('cnt')).resolves.toBe(42);
  });

  it('preserves plain strings', async () => {
    setEnv('NAME', 'hello world');
    const source = new EnvConfigSource(PREFIX);
    await expect(source.get('name')).resolves.toBe('hello world');
  });
});
