/**
 * @phenotype/sdk - Core types and interfaces for the Phenotype fleet
 * 
 * Absorbed from KooshaPari/AtomsBot (decomposed 2026-06-18)
 * See: https://github.com/KooshaPari/AtomsBot
 */
export * from './types.js';

// Re-exports for common adapter patterns
export interface Adapter<TConfig = unknown, TState = unknown> {
  readonly name: string;
  readonly version: string;
  init(config: TConfig): Promise<void>;
  getState(): TState;
  shutdown(): Promise<void>;
}

export interface Bot {
  readonly id: string;
  readonly name: string;
  registerAdapter(adapter: Adapter): void;
  start(): Promise<void>;
  stop(): Promise<void>;
}

export interface Message {
  id: string;
  channel: string;
  author: string;
  content: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export type AdapterType = 'discord' | 'github' | 'jira' | 'slack' | 'webhook' | 'custom';
