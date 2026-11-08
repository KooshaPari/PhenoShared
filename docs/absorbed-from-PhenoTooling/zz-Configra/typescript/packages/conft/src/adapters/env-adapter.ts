/**
 * Environment variable configuration source adapter.
 *
 * Implements ConfigSource port for environment variables.
 */

import { ConfigSource } from '../ports/config-source';
import { ConfigEntry, ConfigValue, ConfigValueSchema } from '../domain/config';

/**
 * Environment variable config source.
 *
 * Reads configuration from process.env.
 */
export class EnvConfigSource implements ConfigSource {
  readonly name = 'env';
  private readonly prefix: string;

  constructor(prefix = 'APP_') {
    this.prefix = prefix;
  }

  async load(): Promise<ConfigEntry[]> {
    const entries: ConfigEntry[] = [];

    for (const [key, value] of Object.entries(process.env)) {
      if (key.startsWith(this.prefix) && value !== undefined) {
        entries.push({
          key: this.stripPrefix(key),
          value: this.parseValue(value),
          source: this.name,
          timestamp: Date.now(),
        });
      }
    }

    return entries;
  }

  async get(key: string): Promise<ConfigValue | undefined> {
    const fullKey = this.prefix + key;
    const value = process.env[fullKey];
    if (value === undefined) return undefined;
    return this.parseValue(value);
  }

  async set(key: string, value: ConfigValue): Promise<void> {
    // Environment variables are read-only in most contexts
    throw new Error('Environment variables are read-only');
  }

  isWritable(): boolean {
    return false;
  }

  private stripPrefix(key: string): string {
    return key.slice(this.prefix.length).toLowerCase();
  }

  private parseValue(value: string): ConfigValue {
    // Parse JSON only when it is one of the public ConfigValue shapes.
    try {
      const parsed = JSON.parse(value);
      const result = ConfigValueSchema.safeParse(parsed);
      if (result.success) {
        return result.data;
      }
    } catch {
      // Continue with scalar parsing.
    }

    // Try boolean
    if (value.toLowerCase() === 'true') return true;
    if (value.toLowerCase() === 'false') return false;

    // Try number
    const number = Number(value);
    if (value.trim() !== '' && Number.isFinite(number)) return number;

    // Return as string
    return value;
  }
}
