import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { API_PORT, ApiError, apiFetch, apiUrl, getApiBaseUrl, isBackendReachable } from './api';

const fetchMock = vi.fn();

describe('getApiBaseUrl', () => {
	afterEach(() => {
		delete (globalThis as Record<string, unknown>).window;
	});

	it('falls back to localhost outside Tauri', () => {
		// Vitest runs in node: no window, so no Tauri internals to detect.
		expect(getApiBaseUrl()).toBe(`http://localhost:${API_PORT}`);
	});

	it('uses the Android emulator host loopback inside Tauri on android', () => {
		(globalThis as Record<string, unknown>).window = {
			__TAURI_INTERNALS__: {},
			__TAURI_OS_PLUGIN_INTERNALS__: { platform: 'android' }
		};
		expect(getApiBaseUrl()).toBe(`http://10.0.2.2:${API_PORT}`);
	});

	it('uses localhost for desktop Tauri platforms', () => {
		(globalThis as Record<string, unknown>).window = {
			__TAURI_INTERNALS__: {},
			__TAURI_OS_PLUGIN_INTERNALS__: { platform: 'macos' }
		};
		expect(getApiBaseUrl()).toBe(`http://localhost:${API_PORT}`);
	});

	it('treats a missing OS plugin as an unknown platform', () => {
		(globalThis as Record<string, unknown>).window = { __TAURI_INTERNALS__: {} };
		expect(getApiBaseUrl()).toBe(`http://localhost:${API_PORT}`);
	});

	it('survives a throwing platform lookup', () => {
		(globalThis as Record<string, unknown>).window = {
			__TAURI_INTERNALS__: {},
			__TAURI_OS_PLUGIN_INTERNALS__: {
				get platform(): string {
					throw new Error('plugin not registered');
				}
			}
		};
		expect(getApiBaseUrl()).toBe(`http://localhost:${API_PORT}`);
	});
});

describe('apiUrl', () => {
	it('joins a leading-slash path without doubling the separator', () => {
		expect(apiUrl('/user/1')).toBe(`http://localhost:${API_PORT}/user/1`);
	});

	it('normalizes a path missing the leading slash', () => {
		expect(apiUrl('user/1')).toBe(`http://localhost:${API_PORT}/user/1`);
	});
});

describe('apiFetch', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', fetchMock);
		fetchMock.mockReset();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('parses a successful JSON response', async () => {
		fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: 7 }), { status: 200 }));

		await expect(apiFetch<{ id: number }>('/projects')).resolves.toEqual({ id: 7 });

		expect(fetchMock).toHaveBeenCalledTimes(1);
		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toBe(`http://localhost:${API_PORT}/projects`);
		expect(init.credentials).toBe('include');
		expect(init.headers['Content-Type']).toBe('application/json');
		expect(init.signal).toBeInstanceOf(AbortSignal);
	});

	it('returns undefined for 204 responses', async () => {
		fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
		await expect(apiFetch('/done')).resolves.toBeUndefined();
	});

	it('throws a typed ApiError carrying the status and parsed body', async () => {
		fetchMock.mockResolvedValue(new Response(JSON.stringify({ error: 'nope' }), { status: 422 }));

		const err = await apiFetch('/projects').catch((e: unknown) => e);
		expect(err).toBeInstanceOf(ApiError);
		expect(err).toMatchObject({
			name: 'ApiError',
			status: 422,
			body: { error: 'nope' },
			message: 'Request to /projects failed with 422'
		});
	});

	it('falls back to the text body when the error body is not JSON', async () => {
		fetchMock.mockResolvedValue({
			ok: false,
			status: 502,
			json: () => Promise.reject(new Error('not json')),
			text: () => Promise.resolve('bad gateway')
		});

		const err = await apiFetch('/health').catch((e: unknown) => e);
		expect(err).toBeInstanceOf(ApiError);
		expect(err).toMatchObject({ status: 502, body: 'bad gateway' });
	});

	it('leaves the body undefined when the error body cannot be read', async () => {
		fetchMock.mockResolvedValue({
			ok: false,
			status: 500,
			json: () => Promise.reject(new Error('not json')),
			text: () => Promise.reject(new Error('not text'))
		});

		const err = await apiFetch('/boom').catch((e: unknown) => e);
		expect(err).toBeInstanceOf(ApiError);
		expect(err).toMatchObject({ status: 500, body: undefined });
	});

	it('merges caller headers, method and timeout into the request', async () => {
		fetchMock.mockResolvedValue(new Response('null', { status: 200 }));

		await apiFetch('/projects', {
			method: 'POST',
			headers: { 'X-Trace': 'abc' },
			timeoutMs: 50
		});

		const [, init] = fetchMock.mock.calls[0];
		expect(init.method).toBe('POST');
		expect(init.headers).toMatchObject({
			'Content-Type': 'application/json',
			'X-Trace': 'abc'
		});
	});

	it('aborts the request when the timeout elapses', async () => {
		// Behave like a real fetch: stay pending until the signal aborts.
		fetchMock.mockImplementation(
			(_url: string, init: RequestInit) =>
				new Promise<Response>((_resolve, reject) => {
					init.signal!.addEventListener('abort', () =>
						reject(new DOMException('Aborted', 'AbortError'))
					);
				})
		);

		const pending = apiFetch('/slow', { timeoutMs: 1 }).then(
			() => 'resolved' as const,
			(error: unknown) => error
		);
		await new Promise((resolve) => setTimeout(resolve, 20));

		const [, init] = fetchMock.mock.calls[0];
		expect(init.signal.aborted).toBe(true);
		const outcome = await pending;
		expect(outcome).toBeInstanceOf(DOMException);
		expect((outcome as DOMException).message).toBe('Aborted');
	});

	it('propagates network failures untouched', async () => {
		fetchMock.mockRejectedValue(new TypeError('Network error'));
		await expect(apiFetch('/x')).rejects.toThrow('Network error');
	});
});

describe('isBackendReachable', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', fetchMock);
		fetchMock.mockReset();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('is true when the health endpoint answers', async () => {
		fetchMock.mockResolvedValue(new Response('null', { status: 200 }));
		await expect(isBackendReachable()).resolves.toBe(true);
	});

	it('is true on an ApiError: the server answered even if unauthorized', async () => {
		fetchMock.mockResolvedValue(new Response('{}', { status: 401 }));
		await expect(isBackendReachable()).resolves.toBe(true);
	});

	it('is false when the request fails without a server response', async () => {
		fetchMock.mockRejectedValue(new TypeError('connection refused'));
		await expect(isBackendReachable()).resolves.toBe(false);
	});
});
