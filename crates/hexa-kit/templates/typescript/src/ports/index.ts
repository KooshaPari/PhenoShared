/**
 * Ports Layer - Interface definitions
 */

// Input Ports (Driving)
export interface InputPort {}

// Output Ports (Driven)
export interface OutputPort {}

// Repository Pattern
export interface Repository<T, TId extends EntityId> extends OutputPort {
  save(entity: T): Promise<T>;
  findById(id: TId): Promise<T | null>;
  delete(id: TId): Promise<void>;
  findAll(): Promise<T[]>;
}

export interface QueryRepository<T> extends OutputPort {
  findByFilter(filter: Filter): Promise<T[]>;
  count(filter: Filter): Promise<number>;
}

// Event Store
export interface EventStore<E extends DomainEvent> extends OutputPort {
  append(aggregateId: string, events: E[], expectedVersion: number): Promise<void>;
  getEvents(aggregateId: string): Promise<E[]>;
}

// Message Bus
export interface MessageBus<E extends DomainEvent> extends OutputPort {
  publish(topic: string, event: E): Promise<void>;
  subscribe(topic: string, handler: EventHandler<E>): void;
}

export interface EventHandler<E extends DomainEvent> {
  handle(event: E): Promise<void>;
}

// Filter
export interface Filter {
  conditions: Condition[];
  limit?: number;
  offset?: number;
}

export interface Condition {
  field: string;
  operator: FilterOperator;
  value: unknown;
}

export type FilterOperator =
  | 'eq'
  | 'ne'
  | 'gt'
  | 'lt'
  | 'gte'
  | 'lte'
  | 'contains'
  | 'startsWith'
  | 'in';

// Unit of Work
export interface UnitOfWork {
  begin(): Promise<void>;
  commit(): Promise<void>;
  rollback(): Promise<void>;
}

// External Service
export interface ExternalService<Req, Res> extends OutputPort {
  call(request: Req): Promise<Res>;
}

// Re-exports
export type { EntityId, DomainEvent } from '../domain';
