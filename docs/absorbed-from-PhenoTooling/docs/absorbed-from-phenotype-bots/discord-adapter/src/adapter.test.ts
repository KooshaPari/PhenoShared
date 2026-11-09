import { describe, it, expect } from 'vitest';
import { DiscordAdapter } from './index.js';

describe('DiscordAdapter', () => {
  it('implements the Adapter contract', () => {
    const adapter = new DiscordAdapter();
    expect(adapter.name).toBe('discord');
    expect(adapter.version).toBe('0.1.0');
  });

  it('initializes with config', async () => {
    const adapter = new DiscordAdapter();
    await adapter.init({ token: 'test-token' });
    const state = adapter.getState();
    expect(state.ready).toBe(true);
    expect(state.config?.token).toBe('test-token');
  });

  it('translates Discord messages to Phenotype format', () => {
    const adapter = new DiscordAdapter();
    const msg = adapter.toPhenotypeMessage({
      id: 'm1',
      channelId: 'c1',
      authorId: 'u1',
      authorName: 'alice',
      content: 'hello',
      timestamp: 1000,
    });
    expect(msg.id).toBe('m1');
    expect(msg.content).toBe('hello');
    expect(msg.metadata?.source).toBe('discord');
    expect(msg.metadata?.authorName).toBe('alice');
  });

  it('shutdown clears config', async () => {
    const adapter = new DiscordAdapter();
    await adapter.init({ token: 'test' });
    await adapter.shutdown();
    expect(adapter.getState().ready).toBe(false);
  });
});
