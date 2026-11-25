/**
 * Backend reachability state for the shell.
 *
 * The desktop app talks to a local service on port 8081 that the user has to
 * start themselves. When it is not running, every list in the app is
 * legitimately empty, which is indistinguishable from a broken view. The shell
 * therefore keeps one shared reachability state and renders a quiet indicator
 * instead of leaving the user to guess.
 *
 * A store (rather than component state) is used because two places render it:
 * the header pill and the content banner.
 */
import { writable } from 'svelte/store';
import { getApiBaseUrl, isBackendReachable } from '$lib/api';

export type BackendState = 'checking' | 'online' | 'offline';

/** `checking` is only visible while the first probe is in flight. */
export const backendState = writable<BackendState>('checking');

/** How often the reachability probe re-runs while the shell is mounted. */
const POLL_INTERVAL_MS = 30_000;

/** Backend origin, for copy that tells the user where to look. */
export function backendOrigin(): string {
	return getApiBaseUrl();
}

let timer: ReturnType<typeof setInterval> | undefined;
let inFlight = false;

/**
 * Probe the backend once.
 *
 * `showChecking` avoids the pill flickering back to "Checking backend" on every
 * background poll; it is only honest to show it on the first probe or on an
 * explicit user retry.
 */
export async function checkBackend({ showChecking = false }: { showChecking?: boolean } = {}) {
	if (inFlight) return;
	inFlight = true;
	if (showChecking) backendState.set('checking');

	try {
		const reachable = await isBackendReachable();
		backendState.set(reachable ? 'online' : 'offline');
	} catch {
		// isBackendReachable never throws, but a rejected probe must still be
		// reported as offline rather than leaving the UI stuck on `checking`.
		backendState.set('offline');
	} finally {
		inFlight = false;
	}
}

/** Start polling. Returns a teardown suitable for an `$effect` return value. */
export function startBackendPolling(intervalMs = POLL_INTERVAL_MS): () => void {
	void checkBackend({ showChecking: true });

	stopBackendPolling();
	timer = setInterval(() => void checkBackend(), intervalMs);

	return stopBackendPolling;
}

/** Stop polling. Safe to call when nothing is running. */
export function stopBackendPolling() {
	if (timer !== undefined) {
		clearInterval(timer);
		timer = undefined;
	}
}
