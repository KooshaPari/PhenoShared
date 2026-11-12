<script lang="ts">
	/**
	 * The BytePort application shell.
	 *
	 * Owns the desktop frame: sidebar, page header, backend indicator and the
	 * scrolling content region. Route segments render inside it via the default
	 * `children` snippet, so no page needs to draw navigation chrome itself.
	 *
	 * Elevation is expressed with the surface ramp plus hairline borders (see
	 * tailwind.config.ts), never with drop shadows.
	 */
	import type { Snippet } from 'svelte';
	import { page } from '$app/state';
	import BackendStatus from './BackendStatus.svelte';
	import PageHeader from './PageHeader.svelte';
	import Sidebar from './Sidebar.svelte';
	import { startBackendPolling } from './health';
	import { entryForPath } from './nav';

	let { children }: { children: Snippet } = $props();

	const entry = $derived(entryForPath(page.url.pathname));

	// Keep probing for as long as the shell is mounted; the returned teardown
	// stops the interval when it unmounts.
	$effect(() => startBackendPolling());
</script>

<div class="bg-background text-dark-onSurface flex h-screen w-screen overflow-hidden">
	<Sidebar />

	<div class="flex min-w-0 flex-1 flex-col">
		<PageHeader title={entry.label} subtitle={entry.subtitle}>
			{#snippet actions()}
				<BackendStatus variant="pill" />
			{/snippet}
		</PageHeader>

		<BackendStatus variant="banner" />

		<main class="min-h-0 flex-1 overflow-y-auto">
			<div class="mx-auto w-full max-w-[1440px] px-5 py-5">
				{@render children()}
			</div>
		</main>
	</div>
</div>
