/**
 * @vitest-environment node
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { InMemoryRepository, RestAdapter, InMemoryMessageBus } from '../index';

interface TestEntity {
  id: { value: string };
  name: string;
}

describe('Adapters Layer', () => {
  describe('InMemoryRepository', () => {
    let repo: InMemoryRepository<TestEntity>;

    beforeEach(() => {
      repo = new InMemoryRepository<TestEntity>();
    });

    it('should save entity', async () => {
      const entity: TestEntity = { id: { value: '1' }, name: 'Test' };
      const saved = await repo.save(entity);
      expect(saved).toBe(entity);
    });

    it('should find entity by id', async () => {
      const entity: TestEntity = { id: { value: '1' }, name: 'Test' };
      await repo.save(entity);

      const found = await repo.findById({ value: '1' });
      expect(found).toBe(entity);
    });

    it('should return null for non-existent entity', async () => {
      const found = await repo.findById({ value: 'non-existent' });
      expect(found).toBeNull();
    });

    it('should delete entity', async () => {
      const entity: TestEntity = { id: { value: '1' }, name: 'Test' };
      await repo.save(entity);

      await repo.delete({ value: '1' });
      const found = await repo.findById({ value: '1' });
      expect(found).toBeNull();
    });

    it('should find all entities', async () => {
      await repo.save({ id: { value: '1' }, name: 'Test1' });
      await repo.save({ id: { value: '2' }, name: 'Test2' });

      const all = await repo.findAll();
      expect(all.length).toBe(2);
    });

    it('should clear all entities', async () => {
      await repo.save({ id: { value: '1' }, name: 'Test1' });
      repo.clear();
      const all = await repo.findAll();
      expect(all.length).toBe(0);
    });
  });

  describe('RestAdapter', () => {
    let adapter: RestAdapter;

    beforeEach(() => {
      adapter = new RestAdapter();
    });

    it('should return 404 for unregistered route', async () => {
      const response = await adapter.handle({
        method: 'GET',
        path: '/unknown',
        headers: {},
        query: {},
        params: {},
      });

      expect(response.status).toBe(404);
      expect(response.error?.code).toBe('NOT_FOUND');
    });

    it('should handle registered GET route', async () => {
      adapter.register('GET', '/api/test', async () => ({ message: 'ok' }));

      const response = await adapter.handle({
        method: 'GET',
        path: '/api/test',
        headers: {},
        query: {},
        params: {},
      });

      expect(response.status).toBe(200);
      expect(response.body).toEqual({ message: 'ok' });
    });

    it('should return 500 for handler errors', async () => {
      adapter.register('GET', '/api/error', async () => {
        throw new Error('Handler error');
      });

      const response = await adapter.handle({
        method: 'GET',
        path: '/api/error',
        headers: {},
        query: {},
        params: {},
      });

      expect(response.status).toBe(500);
      expect(response.error?.code).toBe('INTERNAL_ERROR');
    });
  });

  describe('InMemoryMessageBus', () => {
    let bus: InMemoryMessageBus<{ eventType: string; data: string }>;

    beforeEach(() => {
      bus = new InMemoryMessageBus<{ eventType: string; data: string }>();
    });

    it('should publish event', async () => {
      const received: string[] = [];
      bus.subscribe('test-topic', async (event) => {
        received.push(event.data);
      });

      await bus.publish('test-topic', { eventType: 'Test', data: 'hello' });
      expect(received.length).toBe(1);
      expect(received[0]).toBe('hello');
    });

    it('should handle multiple subscribers', async () => {
      const received1: string[] = [];
      const received2: string[] = [];

      bus.subscribe('test-topic', async (event) => {
        received1.push(event.data);
      });
      bus.subscribe('test-topic', async (event) => {
        received2.push(event.data);
      });

      await bus.publish('test-topic', { eventType: 'Test', data: 'broadcast' });
      expect(received1.length).toBe(1);
      expect(received2.length).toBe(1);
    });

    it('should unsubscribe handler', async () => {
      const received: string[] = [];
      const handler = async (event: { eventType: string; data: string }) => {
        received.push(event.data);
      };

      bus.subscribe('test-topic', handler);
      await bus.publish('test-topic', { eventType: 'Test', data: 'first' });

      bus.unsubscribe('test-topic', handler);
      await bus.publish('test-topic', { eventType: 'Test', data: 'second' });

      expect(received.length).toBe(1);
      expect(received[0]).toBe('first');
    });
  });
});
