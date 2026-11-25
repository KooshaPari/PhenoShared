<script lang="ts">
	/**
	 * Small status pill. Used for deploy/instance state where colour carries
	 * meaning, so it leans on the semantic accent roles rather than arbitrary
	 * shades.
	 */
	import type { Snippet } from 'svelte';

	type Tone = 'neutral' | 'primary' | 'info' | 'warning' | 'danger';

	let {
		tone = 'neutral',
		dot = false,
		class: klass = '',
		children
	}: { tone?: Tone; dot?: boolean; class?: string; children: Snippet } = $props();

	const tones: Record<Tone, string> = {
		neutral: 'bg-dark-surfaceVariant/60 text-dark-onSurfaceVariant border-border',
		primary: 'bg-dark-primaryContainer text-dark-onPrimaryContainer border-transparent',
		info: 'bg-dark-secondaryContainer text-dark-onSecondaryContainer border-transparent',
		warning: 'bg-dark-tertiaryContainer text-dark-onTertiaryContainer border-transparent',
		danger: 'bg-dark-errorContainer text-dark-onErrorContainer border-transparent'
	};
</script>

<span
	class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px]
		font-medium tracking-wide uppercase {tones[tone]} {klass}"
>
	{#if dot}
		<span class="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true"></span>
	{/if}
	{@render children()}
</span>
