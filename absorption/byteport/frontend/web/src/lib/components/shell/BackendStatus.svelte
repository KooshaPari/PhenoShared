<script lang="ts">
	/**
	 * Backend reachability indicator, in two densities.
	 *
	 * - `pill`: always visible in the page header, quiet.
	 * - `banner`: rendered only when the backend is unreachable, directly above
	 *   the content, with a retry action.
	 *
	 * Showing reachability is the honest alternative to rendering an empty list
	 * that looks like a bug in the app rather than a service that is not running.
	 */
	import TriangleAlert from 'lucide-svelte/icons/triangle-alert';
	import Badge from '../ui/Badge.svelte';
	import Button from '../ui/Button.svelte';
	import { backendOrigin, backendState, checkBackend } from './health';

	let { variant = 'pill' }: { variant?: 'pill' | 'banner' } = $props();

	const state = $derived($backendState);

	const label = $derived(
		state === 'online'
			? 'Backend online'
			: state === 'offline'
				? 'Backend offline'
				: 'Checking backend'
	);

	const tone = $derived(
		state === 'online' ? 'primary' : state === 'offline' ? 'danger' : 'neutral'
	);
</script>

{#if variant === 'pill'}
	<Badge {tone} dot>{label}</Badge>
{:else if state === 'offline'}
	<div
		class="border-border bg-dark-errorContainer/25 flex items-center gap-2.5 border-b px-5 py-2"
		role="status"
	>
		<TriangleAlert
			size={14}
			strokeWidth={1.75}
			class="text-dark-error shrink-0"
			aria-hidden="true"
		/>
		<p class="text-dark-onSurface min-w-0 flex-1 truncate text-[12px]">
			No response from the BytePort backend at {backendOrigin()}. Live projects and instances
			are unavailable until it is running.
		</p>
		<Button variant="ghost" size="sm" onclick={() => checkBackend({ showChecking: true })}>
			Check again
		</Button>
	</div>
{/if}
