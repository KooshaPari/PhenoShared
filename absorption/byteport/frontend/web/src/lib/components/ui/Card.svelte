<script lang="ts">
	/**
	 * Card / panel surface.
	 *
	 * Elevation in BytePort comes from the surface ramp plus a 1px border, not
	 * from drop shadows: layered dark greys with hairline borders read correctly
	 * on macOS and avoid the muddy look the old Material fills produced.
	 */
	import type { Snippet } from 'svelte';

	let {
		title = '',
		description = '',
		padding = 'md',
		interactive = false,
		class: klass = '',
		actions,
		children
	}: {
		title?: string;
		description?: string;
		padding?: 'none' | 'sm' | 'md' | 'lg';
		interactive?: boolean;
		class?: string;
		actions?: Snippet;
		children: Snippet;
	} = $props();

	const paddings = {
		none: '',
		sm: 'p-3',
		md: 'p-4',
		lg: 'p-5'
	};

	const hasHeader = $derived(Boolean(title || description || actions));
</script>

<div
	class="border-border bg-dark-surfaceContainer rounded-lg border {paddings[padding]}
		{interactive
		? 'hover:border-dark-outline hover:bg-dark-surfaceContainerHigh transition-colors'
		: ''} {klass}"
>
	{#if hasHeader}
		<div class="mb-3 flex items-start justify-between gap-3">
			<div class="min-w-0">
				{#if title}
					<h3 class="text-dark-onSurface truncate text-sm font-semibold">{title}</h3>
				{/if}
				{#if description}
					<p class="text-dark-onSurfaceVariant mt-0.5 text-[13px] leading-snug">
						{description}
					</p>
				{/if}
			</div>
			{#if actions}
				<div class="shrink-0">{@render actions()}</div>
			{/if}
		</div>
	{/if}
	{@render children()}
</div>
