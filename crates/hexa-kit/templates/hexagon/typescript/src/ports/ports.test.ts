/**
 * @vitest-environment node
 */
import { describe, it, expect } from 'vitest';
import {
  InputPort,
  OutputPort,
  Repository,
  EventStore,
  MessageBus,
  Filter,
  FilterOperator,
} from '../index';

describe('Ports Layer', () => {
  describe('InputPort', () => {
    it('should be an empty interface (marker)', () => {
      const port: InputPort = {};
      expect(port).toEqual({});
    });
  });

  describe('OutputPort', () => {
    it('should be an empty interface (marker)', () => {
      const port: OutputPort = {};
      expect(port).toEqual({});
    });
  });

  describe('Repository', () => {
    it('should define save method signature', () => {
      interface TestEntity {
        id: { value: string };
        name: string;
      }

      const repo: Repository<TestEntity, { value: string }> = {
        save: async (entity: TestEntity) => entity,
        findById: async (_id: { value: string }) => null,
        delete: async (_id: { value: string }) => {},
        findAll: async () => [],
      };

      expect(repo.save).toBeDefined();
      expect(repo.findById).toBeDefined();
      expect(repo.delete).toBeDefined();
      expect(repo.findAll).toBeDefined();
    });
  });

  describe('EventStore', () => {
    it('should define event store methods', () => {
      interface TestEvent {
        eventType: string;
        aggregateId: string;
        occurredAt: Date;
      }

      const store: EventStore<TestEvent> = {
        append: async () => {},
        getEvents: async (_id: string) => [],
      };

      expect(store.append).toBeDefined();
      expect(store.getEvents).toBeDefined();
    });
  });

  describe('MessageBus', () => {
    it('should define message bus methods', () => {
      interface TestEvent {
        eventType: string;
      }

      const bus: MessageBus<TestEvent> = {
        publish: async (_topic: string, _event: TestEvent) => {},
        subscribe: (_topic: string, _handler) => {},
      };

      expect(bus.publish).toBeDefined();
      expect(bus.subscribe).toBeDefined();
    });
  });

  describe('Filter', () => {
    it('should create filter with conditions', () => {
      const filter: Filter = {
        conditions: [
          { field: 'name', operator: 'eq', value: 'Test' },
        ],
        limit: 10,
        offset: 0,
      };

      expect(filter.conditions.length).toBe(1);
      expect(filter.limit).toBe(10);
    });
  });

  describe('FilterOperator', () => {
    it('should support all comparison operators', () => {
      const operators: FilterOperator[] = [
        'eq', 'ne', 'gt', 'lt', 'gte', 'lte', 'contains', 'startsWith', 'in',
      ];

      expect(operators.length).toBe(9);
    });
  });
});
