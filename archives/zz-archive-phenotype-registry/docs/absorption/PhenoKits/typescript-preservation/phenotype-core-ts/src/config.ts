/**
 * Config - Configuration key-value pair
 * Mirrors: phenotype-config Rust / pheno_config Python
 */

export enum ConfigSource {
  ENV = 'ENV',
  FILE = 'FILE',
  VAULT = 'VAULT',
  DEFAULT = 'DEFAULT'
}

export interface Config {
  key: string;
  value: string;
  source: ConfigSource;
}

export class Configuration implements Config {
  constructor(
    public key: string,
    public value: string,
    public source: ConfigSource = ConfigSource.DEFAULT
  ) {}

  toJSON(): string {
    return JSON.stringify({
      key: this.key,
      value: this.value,
      source: this.source
    });
  }

  static fromEnv(key: string): Configuration | null {
    const value = process.env[key];
    if (value === undefined) {
      return null;
    }
    return new Configuration(key, value, ConfigSource.ENV);
  }
}

/**
 * ConfigStore - Interface for configuration storage
 */
export interface ConfigStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  delete(key: string): Promise<void>;
}
