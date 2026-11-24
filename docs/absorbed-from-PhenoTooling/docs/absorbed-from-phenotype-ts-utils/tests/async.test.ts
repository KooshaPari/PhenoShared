import { describe, it, expect } from 'vitest';
import { sleep, retry } from '../src/async.js';

describe('sleep', () => {
  it('waits the requested ms', async () => {
    const start = Date.now();
    await sleep(50);
    const elapsed = Date.now() - start;
    expect(elapsed).toBeGreaterThanOrEqual(45);
  });
});

describe('retry', () => {
  it('returns immediately on success', async () => {
    let calls = 0;
    const r = await retry(async () => {
      calls++;
      return 42;
    });
    expect(r).toBe(42);
    expect(calls).toBe(1);
  });

  it('throws after exhausting attempts', async () => {
    let calls = 0;
    await expect(
      retry(
        async () => {
          calls++;
          throw new Error('boom');
        },
        { attempts: 3, baseDelayMs: 5 },
      ),
    ).rejects.toThrow('boom');
    expect(calls).toBe(3);
  });

  it('uses exponential backoff between attempts', async () => {
    const timestamps: number[] = [];
    await expect(
      retry(
        async () => {
          timestamps.push(Date.now());
          throw new Error('fail');
        },
        { attempts: 3, baseDelayMs: 30 },
      ),
    ).rejects.toThrow('fail');
    // Gap between call 1 and call 2 should be >= baseDelay (30)
    // Gap between call 2 and call 3 should be >= 2*baseDelay (60)
    expect(timestamps[1] - timestamps[0]).toBeGreaterThanOrEqual(28);
    expect(timestamps[2] - timestamps[1]).toBeGreaterThanOrEqual(58);
  });
});
