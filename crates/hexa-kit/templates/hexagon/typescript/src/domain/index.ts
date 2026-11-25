/**
 * Domain Layer - Pure business logic with no external dependencies
 */

// Entity
export interface Entity<TId extends EntityId> {
  readonly id: TId;
  equals(other: Entity<TId>): boolean;
}

export abstract class BaseEntity<TId extends EntityId> implements Entity<TId> {
  constructor(public readonly id: TId) {}

  equals(other: Entity<TId>): boolean {
    if (!other) return false;
    return this.id.equals(other.id);
  }
}

// Entity ID
export interface EntityId {
  readonly value: string;
  equals(other: EntityId): boolean;
  toString(): string;
}

export class Uuid implements EntityId {
  constructor(public readonly value: string) {}

  equals(other: EntityId): boolean {
    return other instanceof Uuid && this.value === other.value;
  }

  toString(): string {
    return this.value;
  }

  static create(): Uuid {
    return new Uuid(crypto.randomUUID());
  }
}

// Value Object
export interface ValueObject {
  equals(other: ValueObject): boolean;
  toString(): string;
}

export abstract class BaseValueObject implements ValueObject {
  abstract equals(other: ValueObject): boolean;
  abstract toString(): string;
}

// Aggregate Root
export interface AggregateRoot<
  T extends AggregateRoot<T, TId>,
  TId extends EntityId,
> extends Entity<TId> {
  readonly version: number;
  readonly pendingEvents: DomainEvent[];
  pullEvents(): DomainEvent[];
}

export abstract class BaseAggregate<
  T extends AggregateRoot<T, TId>,
  TId extends EntityId,
> extends BaseEntity<TId> {
  private _version = 1;
  private _pendingEvents: DomainEvent[] = [];

  constructor(id: TId) {
    super(id);
  }

  get version(): number {
    return this._version;
  }

  get pendingEvents(): DomainEvent[] {
    return [...this._pendingEvents];
  }

  protected addEvent(event: DomainEvent): void {
    this._pendingEvents.push(event);
    this._version++;
  }

  pullEvents(): DomainEvent[] {
    const events = [...this._pendingEvents];
    this._pendingEvents = [];
    return events;
  }
}

// Domain Events
export interface DomainEvent {
  readonly eventType: string;
  readonly occurredAt: Date;
  readonly aggregateId: string;
}

export abstract class BaseDomainEvent implements DomainEvent {
  readonly occurredAt: Date;

  constructor(
    public readonly eventType: string,
    public readonly aggregateId: string,
  ) {
    this.occurredAt = new Date();
  }
}

// Domain Services
export interface DomainService {}

// Domain Errors
export class DomainError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly cause?: Error,
  ) {
    super(message);
    this.name = 'DomainError';
  }
}

export const Errors = {
  NotFound: (message = 'Entity not found') =>
    new DomainError('NOT_FOUND', message),
  InvalidInput: (message = 'Invalid input') =>
    new DomainError('INVALID_INPUT', message),
  Conflict: (message = 'Conflict') => new DomainError('CONFLICT', message),
};
