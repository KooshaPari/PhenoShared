import { afterEach, describe, expect, it } from 'vitest';
import { mkdtemp, rm, writeFile } from 'fs/promises';
import { join } from 'path';
import { tmpdir } from 'os';
import {
  ConfigEntrySchema,
  ConfigErrorSchema,
  ConfigSnapshotSchema,
  ConfigSourceNotFoundError,
  ConfigValidationError,
  ConfigValueSchema,
  EnvConfigSource,
  FileConfigSource,
  ImmutableConfig,
  type ConfigValue,
} from './index';

const environmentKeys = [
  'UNIT_STRING',
  'UNIT_TRUE',
  'UNIT_TRUE_UPPER',
  'UNIT_FALSE',
  'UNIT_NUMBER',
  'UNIT_NUMBER_PADDED',
  'UNIT_ARRAY',
  'UNIT_RECORD',
  'UNIT_BAD_JSON',
];

afterEach(() => {
  for (const key of environmentKeys) delete process.env[key];
});

describe('@phenotype/config-ts public contract', () => {
  it('validates domain value, entry, snapshot, and error shapes', () => {
    const values: ConfigValue[] = [
      'value',
      2,
      false,
      ['a'],
      { key: 'value' },
    ];
    for (const value of values) expect(ConfigValueSchema.parse(value)).toEqual(value);

    expect(
      ConfigEntrySchema.parse({ key: 'port', value: 8080, source: 'env' }),
    ).toMatchObject({ key: 'port', value: 8080 });
    expect(
      ConfigSnapshotSchema.parse({
        entries: { port: 8080 },
        sources: ['env'],
        version: 'v1',
        timestamp: 1,
      }),
    ).toMatchObject({ version: 'v1' });
    expect(
      ConfigErrorSchema.parse({
        message: 'bad',
        path: ['port'],
        value: 'invalid',
      }),
    ).toMatchObject({ message: 'bad' });
  });

  it('retains structured error diagnostics', () => {
    const validation = new ConfigValidationError(
      'bad value',
      ['port'],
      'x',
      { source: 'env' },
    );
    expect(validation.toJSON()).toEqual({
      message: 'bad value',
      path: ['port'],
      value: 'x',
      context: { source: 'env' },
    });

    const missing = new ConfigSourceNotFoundError('missing', 'settings.json', {
      cwd: '/tmp',
    });
    expect(missing).toMatchObject({
      name: 'ConfigSourceNotFoundError',
      source: 'settings.json',
      context: { cwd: '/tmp' },
    });
  });

  it('detaches immutable configuration from constructor and snapshot inputs', () => {
    const entries = new Map<string, ConfigValue>([['port', 8080]]);
    const sources = ['file'];
    const config = new ImmutableConfig(entries, sources, 'v1');

    entries.set('port', 9090);
    sources.push('env');
    expect(config.get('port')).toBe(8080);
    expect(config.has('port')).toBe(true);
    expect(config.has('missing')).toBe(false);

    const snapshot = config.toSnapshot();
    expect(snapshot).toMatchObject({
      entries: { port: 8080 },
      sources: ['file'],
      version: 'v1',
    });
    snapshot.sources.push('changed');
    expect(config.sources).toEqual(['file']);
  });

  it('loads, reads, and rejects writes to JSON file sources', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'conft-unit-'));
    const file = join(directory, 'config.json');
    await writeFile(file, JSON.stringify({ port: 8080, enabled: true }));
    const source = new FileConfigSource(file);

    try {
      expect(await source.load()).toEqual([
        expect.objectContaining({ key: 'port', value: 8080, source: 'file' }),
        expect.objectContaining({ key: 'enabled', value: true, source: 'file' }),
      ]);
      expect(await source.get('port')).toBe(8080);
      expect(await source.get('missing')).toBeUndefined();
      expect(source.isWritable()).toBe(false);
      await expect(source.set('port', 9090)).rejects.toThrow(
        'File configuration sources are read-only',
      );
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it('propagates invalid JSON file errors', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'conft-unit-invalid-'));
    const file = join(directory, 'config.json');
    await writeFile(file, '{');

    try {
      await expect(new FileConfigSource(file).load()).rejects.toBeInstanceOf(
        SyntaxError,
      );
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it('loads prefixed environment values and parses only supported shapes', async () => {
    process.env.UNIT_STRING = 'plain';
    process.env.UNIT_TRUE = 'true';
    process.env.UNIT_TRUE_UPPER = 'TRUE';
    process.env.UNIT_FALSE = 'FALSE';
    process.env.UNIT_NUMBER = '12.5';
    process.env.UNIT_NUMBER_PADDED = ' 42 ';
    process.env.UNIT_ARRAY = '["a","b"]';
    process.env.UNIT_RECORD = '{"a":"b"}';
    process.env.UNIT_BAD_JSON = '[1,2]';

    const source = new EnvConfigSource('UNIT_');
    const entries = await source.load();
    expect(Object.fromEntries(entries.map(({ key, value }) => [key, value]))).toEqual({
      array: ['a', 'b'],
      bad_json: '[1,2]',
      false: false,
      number: 12.5,
      number_padded: 42,
      record: { a: 'b' },
      string: 'plain',
      true: true,
      true_upper: true,
    });
    expect(await source.get('NUMBER')).toBe(12.5);
    expect(await source.get('MISSING')).toBeUndefined();
    expect(source.isWritable()).toBe(false);
    await expect(source.set('NUMBER', 1)).rejects.toThrow(
      'Environment variables are read-only',
    );
  });
});
