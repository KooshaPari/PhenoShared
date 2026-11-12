<script lang="ts">
	/**
	 * Slim page header: current route identity on the left, page actions on the
	 * right. 56px tall so it reads as a desktop toolbar rather than a hero band.
	 *
	 * The old shell's header reserved a fifth of the viewport for a decorative
	 * "Hello." and two unlabelled icon buttons; route identity now comes from
	 * `nav.ts` and the right-hand region is a real slot.
	 */
	import type { Snippet } from 'svelte';

	let {
		title,
		subtitle = '',
		actions
	}: { title: string; subtitle?: string; actions?: Snippet } = $props();
</script>

<header
	class="border-border bg-background flex h-14 shrink-0 items-center justify-between gap-4 border-b px-5"
>
	<div class="flex min-w-0 flex-col">
		<h1 class="text-dark-onSurface truncate text-[14px] leading-tight font-semibold">
			{title}
		</h1>
		{#if subtitle}
			<p class="text-dark-onSurfaceVariant truncate text-[12px] leading-tight">{subtitle}</p>
		{/if}
	</div>

	{#if actions}
		<div class="flex shrink-0 items-center gap-2">
			{@render actions()}
		</div>
	{/if}
</header>
