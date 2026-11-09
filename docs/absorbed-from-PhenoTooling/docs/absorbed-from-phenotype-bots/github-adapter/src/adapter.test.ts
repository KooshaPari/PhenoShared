import { describe, it, expect } from 'vitest';
import { GitHubAdapter } from './index.js';

describe('GitHubAdapter', () => {
  it('implements the Adapter contract', () => {
    const adapter = new GitHubAdapter();
    expect(adapter.name).toBe('github');
    expect(adapter.version).toBe('0.1.0');
  });

  it('initializes with config', async () => {
    const adapter = new GitHubAdapter();
    await adapter.init({ token: 'ghp_test', owner: 'KooshaPari', repo: 'phenotype' });
    const state = adapter.getState();
    expect(state.ready).toBe(true);
    expect(state.config?.owner).toBe('KooshaPari');
  });

  it('translates GitHub events to Phenotype format', () => {
    const adapter = new GitHubAdapter();
    const msg = adapter.toPhenotypeMessage({
      event: 'issues',
      action: 'opened',
      deliveryId: 'd1',
      payload: {
        sender: { login: 'alice' },
        repository: { full_name: 'KooshaPari/phenotype' },
        issue: { number: 42, title: 'Bug' },
      },
      timestamp: 1000,
    });
    expect(msg.id).toBe('d1');
    expect(msg.content).toBe('issues.opened');
    expect(msg.metadata?.source).toBe('github');
  });

  it('shutdown clears config', async () => {
    const adapter = new GitHubAdapter();
    await adapter.init({ token: 'test' });
    await adapter.shutdown();
    expect(adapter.getState().ready).toBe(false);
  });
});
