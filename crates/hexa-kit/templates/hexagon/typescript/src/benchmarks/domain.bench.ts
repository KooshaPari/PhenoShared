/**
 * Performance Benchmarks for HexaType Domain Layer
 * Run with: vitest bench src/benchmarks/domain.bench.ts
 */

import { describe, bench } from 'vitest';
import { Uuid, BaseEntity, BaseValueObject, BaseAggregate, BaseDomainEvent } from '../domain/index';

describe('Domain Benchmarks', () => {
  bench('Uuid.create()', () => {
    Uuid.create();
  });

  bench('Uuid.create() x 100', () => {
    for (let i = 0; i < 100; i++) {
      Uuid.create();
    }
  });

  bench('Uuid.equals() - same', () => {
    const id1 = new Uuid('550e8400-e29b-41d4-a716-446655440000');
    const id2 = new Uuid('550e8400-e29b-41d4-a716-446655440000');
    id1.equals(id2);
  });

  bench('Uuid.equals() - different', () => {
    const id1 = new Uuid('550e8400-e29b-41d4-a716-446655440000');
    const id2 = new Uuid('550e8400-e29b-41d4-a716-446655440001');
    id1.equals(id2);
  });

  bench('Uuid.toString()', () => {
    const id = new Uuid('550e8400-e29b-41d4-a716-446655440000');
    id.toString();
  });
});

describe('Aggregate Benchmarks', () => {
  bench('Aggregate instantiation', () => {
    class TestAggregate extends BaseAggregate<TestAggregate, Uuid> {
      getState() { return 'test'; }
    }
    new TestAggregate(new Uuid(crypto.randomUUID()));
  });

  bench('Aggregate addEvent and pullEvents', () => {
    class TestAggregate extends BaseAggregate<TestAggregate, Uuid> {
      getState() { return 'test'; }
    }
    const agg = new TestAggregate(new Uuid(crypto.randomUUID()));
    agg.addEvent({ eventType: 'TestEvent', aggregateId: 'test' } as any);
    agg.pullEvents();
  });

  bench('Aggregate version increment', () => {
    class TestAggregate extends BaseAggregate<TestAggregate, Uuid> {
      getState() { return 'test'; }
    }
    const agg = new TestAggregate(new Uuid(crypto.randomUUID()));
    for (let i = 0; i < 100; i++) {
      agg.addEvent({ eventType: 'TestEvent', aggregateId: 'test' } as any);
    }
  });
});

describe('Entity Benchmarks', () => {
  bench('Entity.equals() - same', () => {
    class TestEntity extends BaseEntity<Uuid> {
      getState() { return 'test'; }
    }
    const id = new Uuid('550e8400-e29b-41d4-a716-446655440000');
    const e1 = new TestEntity(id);
    const e2 = new TestEntity(id);
    e1.equals(e2);
  });

  bench('Entity.equals() - different ids', () => {
    class TestEntity extends BaseEntity<Uuid> {
      getState() { return 'test'; }
    }
    const e1 = new TestEntity(new Uuid('550e8400-e29b-41d4-a716-446655440000'));
    const e2 = new TestEntity(new Uuid('550e8400-e29b-41d4-a716-446655440001'));
    e1.equals(e2);
  });
});

describe('ValueObject Benchmarks', () => {
  bench('ValueObject instantiation', () => {
    class TestValueObject extends BaseValueObject {
      constructor(public readonly value: string) { super(); }
      equals(other: import('../domain/index').ValueObject): boolean {
        return other instanceof TestValueObject && this.value === other.value;
      }
      toString(): string { return this.value; }
    }
    new TestValueObject('test');
  });

  bench('ValueObject.equals() - same', () => {
    class TestValueObject extends BaseValueObject {
      constructor(public readonly value: string) { super(); }
      equals(other: import('../domain/index').ValueObject): boolean {
        return other instanceof TestValueObject && this.value === other.value;
      }
      toString(): string { return this.value; }
    }
    const v1 = new TestValueObject('test');
    const v2 = new TestValueObject('test');
    v1.equals(v2);
  });

  bench('ValueObject.equals() - different', () => {
    class TestValueObject extends BaseValueObject {
      constructor(public readonly value: string) { super(); }
      equals(other: import('../domain/index').ValueObject): boolean {
        return other instanceof TestValueObject && this.value === other.value;
      }
      toString(): string { return this.value; }
    }
    const v1 = new TestValueObject('test1');
    const v2 = new TestValueObject('test2');
    v1.equals(v2);
  });
});

describe('DomainEvent Benchmarks', () => {
  bench('DomainEvent instantiation', () => {
    class TestEvent extends BaseDomainEvent {
      constructor(aggregateId: string) {
        super('TestEvent', aggregateId);
      }
    }
    new TestEvent('test-aggregate-id');
  });

  bench('DomainEvent occurredAt timestamp', () => {
    class TestEvent extends BaseDomainEvent {
      constructor(aggregateId: string) {
        super('TestEvent', aggregateId);
      }
    }
    const event = new TestEvent('test');
    const ts = event.occurredAt;
  });
});
