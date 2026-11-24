/**
 * Adapters Layer - Infrastructure implementations
 */

import { OutputPort } from '../ports';

// In-Memory Repository
export class InMemoryRepository<T extends { id: { value: string } }>
  implements OutputPort
{
  private entities = new Map<string, T>();

  async save(entity: T): Promise<T> {
    this.entities.set(entity.id.value, entity);
    return entity;
  }

  async findById(id: { value: string }): Promise<T | null> {
    return this.entities.get(id.value) ?? null;
  }

  async delete(id: { value: string }): Promise<void> {
    this.entities.delete(id.value);
  }

  async findAll(): Promise<T[]> {
    return Array.from(this.entities.values());
  }

  async findByIds(ids: { value: string }[]): Promise<T[]> {
    return ids
      .map((id) => this.entities.get(id.value))
      .filter((e): e is T => e !== undefined);
  }

  clear(): void {
    this.entities.clear();
  }
}

// REST Adapter
export interface RestRequest {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  headers: Record<string, string>;
  body?: unknown;
  query: Record<string, string>;
  params: Record<string, string>;
}

export interface RestResponse<T = unknown> {
  status: number;
  headers: Record<string, string>;
  body?: T;
  error?: RestError;
}

export interface RestError {
  code: string;
  message: string;
  details?: unknown;
}

export class RestAdapter {
  private handlers: Map<string, Handler> = new Map();

  register(
    method: string,
    path: string,
    handler: Handler,
  ): void {
    this.handlers.set(`${method}:${path}`, handler);
  }

  async handle(request: RestRequest): Promise<RestResponse> {
    const handler = this.handlers.get(`${request.method}:${request.path}`);
    if (!handler) {
      return {
        status: 404,
        headers: {},
        error: { code: 'NOT_FOUND', message: 'Route not found' },
      };
    }

    try {
      const result = await handler(request);
      return {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: result,
      };
    } catch (error) {
      return {
        status: 500,
        headers: {},
        error: {
          code: 'INTERNAL_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error',
        },
      };
    }
  }
}

type Handler = (request: RestRequest) => Promise<unknown>;

// Message Bus
export class InMemoryMessageBus<E extends { eventType: string }>
  implements OutputPort
{
  private subscribers = new Map<string, Set<(event: E) => Promise<void>>>();

  async publish(topic: string, event: E): Promise<void> {
    const handlers = this.subscribers.get(topic);
    if (handlers) {
      await Promise.all(
        Array.from(handlers).map((handler) => handler(event)),
      );
    }
  }

  subscribe(topic: string, handler: (event: E) => Promise<void>): void {
    if (!this.subscribers.has(topic)) {
      this.subscribers.set(topic, new Set());
    }
    this.subscribers.get(topic)!.add(handler);
  }

  unsubscribe(topic: string, handler: (event: E) => Promise<void>): void {
    this.subscribers.get(topic)?.delete(handler);
  }
}
