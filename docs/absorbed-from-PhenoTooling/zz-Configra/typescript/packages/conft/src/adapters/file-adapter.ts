/**
 * File-based configuration source adapter.
 *
 * Implements ConfigSource port for JSON/YAML config files.
 */

import { readFile } from 'fs/promises';
import { ConfigSource } from '../ports/config-source';
import { ConfigEntry, ConfigValue } from '../domain/config';

/**
 * File-based config source.
 *
 * Reads configuration from JSON or YAML files.
 */
export class FileConfigSource implements ConfigSource {
  readonly name = 'file';
  private readonly path: string;

  constructor(path: string) {
    this.path = path;
  }

  async load(): Promise<ConfigEntry[]> {
    const content = await readFile(this.path, 'utf-8');
    const parsed = JSON.parse(content);
    const entries: ConfigEntry[] = [];

    for (const [key, value] of Object.entries(parsed)) {
      entries.push({
        key,
        value: value as ConfigValue,
        source: this.name,
        timestamp: Date.now(),
      });
    }

    return entries;
  }

  async get(key: string): Promise<ConfigValue | undefined> {
    const entries = await this.load();
    const entry = entries.find((e) => e.key === key);
    return entry?.value;
  }

  async set(_key: string, _value: ConfigValue): Promise<void> {
    throw new Error('File configuration sources are read-only');
  }

  isWritable(): boolean {
    return false;
  }
}
