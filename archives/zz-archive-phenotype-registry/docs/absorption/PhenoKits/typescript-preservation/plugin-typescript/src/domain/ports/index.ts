// Ports - interface definitions (ISP - Interface Segregation Principle)
import { Example } from '../entities/index.js';
import { DomainError } from '../errors/index.js';

// Repository port - outbound interface for persistence
export interface Repository<T extends { id: string }> {
  save(entity: T): Promise<Result<void>>;
  findById(id: string): Promise<Result<T | null>>;
  delete(id: string): Promise<Result<void>>;
  list(page: number, pageSize: number): Promise<Result<T[]>>;
}

// Plugin interface - for extensibility
export interface Plugin {
  readonly name: string;
  readonly version: string;
  initialize(): Promise<void>;
  shutdown(): Promise<void>;
}

// Plugin Registry - manages plugin lifecycle
export interface PluginRegistry {
  register(plugin: Plugin): Promise<void>;
  unregister(name: string): Promise<void>;
  get(name: string): Plugin | undefined;
  list(): Plugin[];
}

// Wrap-Over: Validation port using Zod
export interface Validator<T> {
  parse(data: unknown): T;
  safeParse(data: unknown): Result<T>;
}
