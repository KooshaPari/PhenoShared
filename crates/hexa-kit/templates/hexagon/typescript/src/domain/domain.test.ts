/**
 * @vitest-environment node
 */
import { describe, it, expect } from 'vitest';
import {
  BaseEntity,
  Uuid,
  Entity,
  BaseValueObject,
  ValueObject,
  BaseAggregate,
  AggregateRoot,
  BaseDomainEvent,
  DomainError,
  Errors,
} from '../index';

// Test Entity Implementation
class TestEntity extends BaseEntity<Uuid> {
  constructor(id: Uuid, public readonly name: string) {
    super(id);
  }
}

// Test Value Object Implementation
class Email extends BaseValueObject {
  constructor(public readonly value: string) {
    super();
    if (!value.includes('@')) {
      throw new Error('Invalid email');
    }
  }

  equals(other: ValueObject): boolean {
    return other instanceof Email && this.value === other.value;
  }

  toString(): string {
    return this.value;
  }
}

// Test Aggregate Implementation
interface TestAggregate extends AggregateRoot<TestAggregate, Uuid> {}

class OrderAggregate extends BaseAggregate<TestAggregate, Uuid>
  implements TestAggregate
{
  constructor(id: Uuid, private _status: string = 'pending') {
    super(id);
  }

  get status(): string {
    return this._status;
  }

  confirm(): void {
    this._status = 'confirmed';
    this.addEvent(new OrderConfirmedEvent(this.id.value));
  }
}

// Test Domain Event
class OrderConfirmedEvent extends BaseDomainEvent {
  constructor(aggregateId: string) {
    super('OrderConfirmed', aggregateId);
  }
}

describe('Domain Layer', () => {
  describe('EntityId', () => {
    it('should create a valid UUID', () => {
      const id = Uuid.create();
      expect(id.value).toBeDefined();
      expect(typeof id.value).toBe('string');
    });

    it('should generate unique UUIDs', () => {
      const id1 = Uuid.create();
      const id2 = Uuid.create();
      expect(id1.value).not.toBe(id2.value);
    });

    it('should equal another UUID with same value', () => {
      const id1 = Uuid.create();
      const id2 = new Uuid(id1.value);
      expect(id1.equals(id2)).toBe(true);
    });

    it('should not equal another UUID with different value', () => {
      const id1 = Uuid.create();
      const id2 = Uuid.create();
      expect(id1.equals(id2)).toBe(false);
    });

    it('should convert to string correctly', () => {
      const id = new Uuid('test-123');
      expect(id.toString()).toBe('test-123');
    });
  });

  describe('Entity', () => {
    it('should create entity with id', () => {
      const id = Uuid.create();
      const entity = new TestEntity(id, 'Test');
      expect(entity.id).toBe(id);
      expect(entity.name).toBe('Test');
    });

    it('should equal another entity with same id', () => {
      const id = Uuid.create();
      const entity1 = new TestEntity(id, 'Test1');
      const entity2 = new TestEntity(id, 'Test2');
      expect(entity1.equals(entity2)).toBe(true);
    });

    it('should not equal another entity with different id', () => {
      const entity1 = new TestEntity(Uuid.create(), 'Test1');
      const entity2 = new TestEntity(Uuid.create(), 'Test2');
      expect(entity1.equals(entity2)).toBe(false);
    });

    it('should return false when comparing with null', () => {
      const entity = new TestEntity(Uuid.create(), 'Test');
      expect(entity.equals(null as unknown as Entity<Uuid>)).toBe(false);
    });
  });

  describe('ValueObject', () => {
    it('should create value object with valid email', () => {
      const email = new Email('test@example.com');
      expect(email.value).toBe('test@example.com');
    });

    it('should throw for invalid email', () => {
      expect(() => new Email('invalid-email')).toThrow('Invalid email');
    });

    it('should equal another email with same value', () => {
      const email1 = new Email('test@example.com');
      const email2 = new Email('test@example.com');
      expect(email1.equals(email2)).toBe(true);
    });

    it('should not equal another email with different value', () => {
      const email1 = new Email('test1@example.com');
      const email2 = new Email('test2@example.com');
      expect(email1.equals(email2)).toBe(false);
    });
  });

  describe('AggregateRoot', () => {
    it('should create aggregate with id and version 1', () => {
      const id = Uuid.create();
      const aggregate = new OrderAggregate(id);
      expect(aggregate.id).toBe(id);
      expect(aggregate.version).toBe(1);
    });

    it('should track pending events', () => {
      const id = Uuid.create();
      const aggregate = new OrderAggregate(id);
      expect(aggregate.pendingEvents).toEqual([]);
    });

    it('should increment version when adding events', () => {
      const id = Uuid.create();
      const aggregate = new OrderAggregate(id);
      const initialVersion = aggregate.version;

      aggregate.confirm();
      expect(aggregate.version).toBeGreaterThan(initialVersion);
    });

    it('should pull events and clear them', () => {
      const id = Uuid.create();
      const aggregate = new OrderAggregate(id);
      aggregate.confirm();

      const events = aggregate.pullEvents();
      expect(events.length).toBe(1);
      expect(aggregate.pendingEvents).toEqual([]);
    });
  });

  describe('DomainEvent', () => {
    it('should create domain event with correct properties', () => {
      const event = new OrderConfirmedEvent('aggregate-123');
      expect(event.eventType).toBe('OrderConfirmed');
      expect(event.aggregateId).toBe('aggregate-123');
      expect(event.occurredAt).toBeInstanceOf(Date);
    });
  });

  describe('DomainError', () => {
    it('should create domain error with code and message', () => {
      const error = new DomainError('TEST_ERROR', 'Test error message');
      expect(error.code).toBe('TEST_ERROR');
      expect(error.message).toBe('Test error message');
      expect(error.name).toBe('DomainError');
    });

    it('should include cause error if provided', () => {
      const cause = new Error('Cause error');
      const error = new DomainError('TEST_ERROR', 'Test', cause);
      expect(error.cause).toBe(cause);
    });
  });

  describe('Error Factory', () => {
    it('should create NotFound error', () => {
      const error = Errors.NotFound('Resource not found');
      expect(error.code).toBe('NOT_FOUND');
      expect(error.message).toBe('Resource not found');
    });

    it('should create InvalidInput error', () => {
      const error = Errors.InvalidInput('Invalid input data');
      expect(error.code).toBe('INVALID_INPUT');
      expect(error.message).toBe('Invalid input data');
    });

    it('should create Conflict error', () => {
      const error = Errors.Conflict('Resource conflict');
      expect(error.code).toBe('CONFLICT');
      expect(error.message).toBe('Resource conflict');
    });

    it('should use default message if not provided', () => {
      expect(Errors.NotFound().message).toBe('Entity not found');
      expect(Errors.InvalidInput().message).toBe('Invalid input');
      expect(Errors.Conflict().message).toBe('Conflict');
    });
  });
});
