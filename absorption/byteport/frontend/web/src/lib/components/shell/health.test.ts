import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { isBackendReachable } from '$lib/api';
import {
	backendOrigin,
	backendState,
	checkBackend,
	startBackendPolling,
	stopBackendPolling
} from './health';

vi.mock('$lib/api', () => ({
	getApiBaseUrl: vi.fn(() => 'http://localhost:8081'),
	isBackendReachable: vi.fn()
}));

const reachable = vi.mocked(isBackendReachable);

describe('backendOrigin', () => {
	it('exposes the API base URL for user-facing copy', () => {
		expect(backendOrigin()).toBe('http://localhost:8081');
	});
});

describe('checkBackend', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		backendState.set('checking');
		stopBackendPolling();
	});

	afterEach(() => {
		stopBackendPolling();
	});

	it('starts in the checking state', () => {
		expect(get(backendState)).toBe('checking');
	});

	it('reports online when the probe succeeds', async () => {
		reachable.mockResolvedValueOnce(true);
		await checkBackend({ showChecking: true });
		expect(get(backendState)).toBe('online');
	});

	it('reports offline when the probe fails', async () => {
		reachable.mockResolvedValueOnce(false);
		await checkBackend({ showChecking: true });
		expect(get(backendState)).toBe('offline');
	});

	it('reports offline when the probe rejects', async () => {
		reachable.mockRejectedValueOnce(new Error('network down'));
		await checkBackend({ showChecking: true });
		expect(get(backendState)).toBe('offline');
	});

	it('keeps the current state during background polls', async () => {
		reachable.mockResolvedValueOnce(true);
		await checkBackend({ showChecking: true });
		expect(get(backendState)).toBe('online');

		reachable.mockResolvedValueOnce(false);
		await checkBackend();
		// No showChecking: the pill must not flash back to "checking".
		expect(get(backendState)).toBe('offline');
	});

	it('ignores a second probe while one is in flight', async () => {
		let release!: (value: boolean) => void;
		reachable.mockImplementationOnce(() => new Promise<boolean>((r) => (release = r)));

		const first = checkBackend({ showChecking: true });
		// Second call must return immediately without starting another probe.
		await checkBackend({ showChecking: true });
		expect(reachable).toHaveBeenCalledTimes(1);

		release(true);
		await first;
		expect(get(backendState)).toBe('online');
	});
});

describe('backend polling', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.useFakeTimers();
		backendState.set('checking');
		stopBackendPolling();
	});

	afterEach(() => {
		stopBackendPolling();
		vi.useRealTimers();
	});

	it('probes immediately and then on each interval', async () => {
		reachable.mockResolvedValue(true);
		startBackendPolling(1000);
		await vi.advanceTimersByTimeAsync(0);
		expect(reachable).toHaveBeenCalledTimes(1);

		await vi.advanceTimersByTimeAsync(1000);
		expect(reachable).toHaveBeenCalledTimes(2);

		await vi.advanceTimersByTimeAsync(1000);
		expect(reachable).toHaveBeenCalledTimes(3);
	});

	it('stops probing after the returned teardown runs', async () => {
		reachable.mockResolvedValue(true);
		const teardown = startBackendPolling(1000);
		await vi.advanceTimersByTimeAsync(0);
		expect(reachable).toHaveBeenCalledTimes(1);

		teardown();
		await vi.advanceTimersByTimeAsync(5000);
		expect(reachable).toHaveBeenCalledTimes(1);
	});

	it('is safe to stop when nothing is running', () => {
		expect(() => stopBackendPolling()).not.toThrow();
	});
});
