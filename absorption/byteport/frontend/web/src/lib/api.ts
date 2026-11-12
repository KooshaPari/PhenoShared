/**
 * Single source of truth for talking to the BytePort backend.
 *
 * Previously every page carried its own copy of `getBaseUrl` (15 files) and
 * most called `platform()` from `@tauri-apps/plugin-os` unguarded. That plugin
 * is not registered in the Rust shell, and `platform()` dereferences
 * `window.__TAURI_OS_PLUGIN_INTERNALS__`, so it throws a TypeError wherever it
 * is called. In several pages the throw happened inside an async function whose
 * promise was never awaited with a catch, so user initialisation silently never
 * ran and the view stayed empty.
 *
 * Import these helpers instead of re-implementing base-URL logic.
 */

/** Port the backend actually listens on (see backend/byteport/main.go). */
export const API_PORT = 8081;

/**
 * Backend origin for the current runtime.
 *
 * - Android emulator reaches the host loopback via 10.0.2.2.
 * - Desktop (macOS/Windows/Linux) uses localhost.
 * - `VITE_API_URL` overrides everything for non-Tauri/dev builds.
 *
 * Never throws: platform detection is best-effort, because a failure there must
 * not take down the whole view.
 */
export function getApiBaseUrl(): string {
	const override = import.meta.env?.VITE_API_URL;
	if (override) return override;

	// Not running inside Tauri (plain browser / SSR) — nothing to detect.
	if (typeof window === 'undefined' || !(window as any).__TAURI_INTERNALS__) {
		return `http://localhost:${API_PORT}`;
	}

	let platform: string;
	try {
		// Dynamic import keeps this synchronous-looking while avoiding a hard
		// dependency at module load in non-Tauri contexts.
		platform = (window as any).__TAURI_OS_PLUGIN_INTERNALS__?.platform ?? '';
	} catch {
		platform = '';
	}

	// Android is the only platform whose host loopback differs.
	return platform === 'android' ? `http://10.0.2.2:${API_PORT}` : `http://localhost:${API_PORT}`;
}

/** Absolute URL for a backend path, tolerating a leading slash or not. */
export function apiUrl(path: string): string {
	const normalized = path.startsWith('/') ? path : `/${path}`;
	return `${getApiBaseUrl()}${normalized}`;
}

export class ApiError extends Error {
	constructor(
		message: string,
		readonly status: number,
		readonly body?: unknown
	) {
		super(message);
		this.name = 'ApiError';
	}
}

/**
 * Fetch JSON from the backend with credentials, timeouts and a typed error.
 *
 * `credentials: 'include'` is required: the session cookie is how the backend
 * authenticates the desktop app.
 */
export async function apiFetch<T = unknown>(
	path: string,
	init: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
	const { timeoutMs = 30000, headers, ...rest } = init;

	// AbortController rather than a bare fetch: a hung backend previously left
	// the UI spinning forever with no way to recover.
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeoutMs);

	try {
		const response = await fetch(apiUrl(path), {
			credentials: 'include',
			headers: { 'Content-Type': 'application/json', ...headers },
			signal: controller.signal,
			...rest
		});

		if (!response.ok) {
			let body: unknown;
			try {
				body = await response.json();
			} catch {
				body = await response.text().catch(() => undefined);
			}
			throw new ApiError(
				`Request to ${path} failed with ${response.status}`,
				response.status,
				body
			);
		}

		if (response.status === 204) return undefined as T;
		return (await response.json()) as T;
	} finally {
		clearTimeout(timer);
	}
}

/**
 * Whether the backend is reachable. Used by the shell to show an honest
 * "backend offline" indicator instead of rendering empty lists that look like
 * the app is broken.
 */
export async function isBackendReachable(timeoutMs = 2500): Promise<boolean> {
	try {
		await apiFetch('/health', { timeoutMs });
		return true;
	} catch (err) {
		// A 401 means the server answered — it is up, we are just not logged in.
		return err instanceof ApiError;
	}
}
