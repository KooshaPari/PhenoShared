import { describe, it, expect } from 'vitest';
import { PhenotypeBot, SimpleRouter } from './index.js';
import type { Adapter, Message } from '@phenotype/sdk';

class MockAdapter implements Adapter {
  readonly name = 'mock';
  readonly version = '0.0.1';
  async init() {}
  getState() { return {}; }
  async shutdown() {}
}

describe('PhenotypeBot', () => {
  it('registers adapters', () => {
    const bot = new PhenotypeBot({ id: 'test', name: 'test-bot' });
    const adapter = new MockAdapter();
    bot.registerAdapter(adapter);
    expect(bot).toBeDefined();
  });

  it('routes messages to registered handlers', async () => {
    const bot = new PhenotypeBot({ id: 'test', name: 'test-bot' });
    let called = false;
    bot.registerHandler('hello', async () => { called = true; });
    await bot.handleMessage({
      id: '1', channel: 'c', author: 'a',
      content: 'hello world', timestamp: Date.now(),
    });
    expect(called).toBe(true);
  });
});

describe('SimpleRouter', () => {
  it('matches string patterns', async () => {
    const router = new SimpleRouter();
    let called = false;
    router.register('foo', async () => { called = true; });
    const handler = await router.route({
      id: '1', channel: 'c', author: 'a',
      content: 'foo bar', timestamp: 0,
    });
    expect(handler).not.toBeNull();
    if (handler) await handler({} as Message);
    expect(called).toBe(true);
  });

  it('matches regex patterns', async () => {
    const router = new SimpleRouter();
    let called = false;
    router.register(/^!cmd/, async () => { called = true; });
    const handler = await router.route({
      id: '1', channel: 'c', author: 'a',
      content: '!cmd arg', timestamp: 0,
    });
    expect(handler).not.toBeNull();
  });

  it('returns null when no match', async () => {
    const router = new SimpleRouter();
    router.register('xyz', async () => {});
    const handler = await router.route({
      id: '1', channel: 'c', author: 'a',
      content: 'abc', timestamp: 0,
    });
    expect(handler).toBeNull();
  });
});
