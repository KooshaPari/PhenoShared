<script lang="ts">
	/**
	 * One sidebar navigation row.
	 *
	 * Rendered as an anchor rather than a `<button>`: these are real navigations,
	 * so they must support open-in-new-window, middle click and copy-link. The
	 * active row carries `aria-current="page"` so assistive tech gets the same
	 * "where am I" signal the teal rail gives sighted users.
	 */
	import type { Component } from 'svelte';

	let {
		href,
		label,
		active = false,
		icon: Icon
	}: {
		href: string;
		label: string;
		active?: boolean;
		icon: Component;
	} = $props();
</script>

<a
	{href}
	aria-current={active ? 'page' : undefined}
	class="group relative flex h-8 items-center gap-2.5 rounded-md px-2 text-[13px] font-medium transition-colors
		{active
		? 'bg-dark-surfaceContainerHighest text-dark-onSurface'
		: 'text-dark-onSurfaceVariant hover:bg-dark-surfaceContainerHigh hover:text-dark-onSurface'}"
>
	{#if active}
		<span
			class="bg-dark-primary absolute top-1/2 left-0 h-4 w-0.5 -translate-y-1/2 rounded-full"
			aria-hidden="true"
		></span>
	{/if}
	<span
		class="shrink-0 transition-colors {active
			? 'text-dark-primary'
			: 'text-dark-onSurfaceVariant group-hover:text-dark-onSurface'}"
		aria-hidden="true"
	>
		<Icon size={16} strokeWidth={1.75} />
	</span>
	<span class="truncate">{label}</span>
</a>
