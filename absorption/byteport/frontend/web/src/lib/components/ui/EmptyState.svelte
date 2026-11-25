<script lang="ts">
	/**
	 * Empty state: icon, one-line explanation, single action.
	 *
	 * Every list in BytePort can legitimately be empty (no projects on first run,
	 * no instances, no deployments). Previously these rendered as blank panes,
	 * which is indistinguishable from a broken view.
	 */
	import type { Snippet } from 'svelte';

	let {
		title,
		description = '',
		icon,
		actions
	}: {
		title: string;
		description?: string;
		icon?: Snippet;
		actions?: Snippet;
	} = $props();
</script>

<div class="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
	{#if icon}
		<div class="text-dark-onSurfaceVariant/50">{@render icon()}</div>
	{/if}
	<div class="max-w-sm space-y-1">
		<p class="text-dark-onSurface text-sm font-medium">{title}</p>
		{#if description}
			<p class="text-dark-onSurfaceVariant text-[13px] leading-relaxed">{description}</p>
		{/if}
	</div>
	{#if actions}
		<div class="mt-1 flex items-center gap-2">{@render actions()}</div>
	{/if}
</div>
