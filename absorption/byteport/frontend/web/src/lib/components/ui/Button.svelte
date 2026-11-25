<script lang="ts">
	/**
	 * Button — the single button primitive for BytePort.
	 *
	 * Replaces the ad-hoc `<button class="bg-dark-primary rounded p-2">` markup
	 * scattered through the 2023-era views. Sizes are tuned for a desktop tool
	 * (32/36px tall, 13-14px labels) rather than touch targets.
	 */
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
	type Size = 'sm' | 'md' | 'icon';

	let {
		variant = 'secondary',
		size = 'md',
		disabled = false,
		loading = false,
		type = 'button',
		class: klass = '',
		children,
		...rest
	}: {
		variant?: Variant;
		size?: Size;
		disabled?: boolean;
		loading?: boolean;
		class?: string;
		children: Snippet;
	} & HTMLButtonAttributes = $props();

	const base =
		'inline-flex items-center justify-center gap-2 font-medium whitespace-nowrap ' +
		'rounded-md transition-colors select-none ' +
		'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-1 ' +
		'focus-visible:ring-offset-background ' +
		'disabled:pointer-events-none disabled:opacity-50';

	const variants: Record<Variant, string> = {
		primary:
			'bg-dark-primary text-dark-onPrimary hover:brightness-110 active:brightness-95 shadow-sm',
		secondary:
			'bg-dark-surfaceContainerHigh text-dark-onSurface border border-border ' +
			'hover:bg-dark-surfaceContainerHighest',
		ghost: 'text-dark-onSurfaceVariant hover:bg-dark-surfaceContainerHigh hover:text-dark-onSurface',
		danger: 'bg-dark-error text-dark-onError hover:brightness-110'
	};

	const sizes: Record<Size, string> = {
		sm: 'h-8 px-3 text-[13px]',
		md: 'h-9 px-4 text-sm',
		icon: 'h-8 w-8'
	};
</script>

<button
	{type}
	class="{base} {variants[variant]} {sizes[size]} {klass}"
	disabled={disabled || loading}
	aria-busy={loading}
	{...rest}
>
	{#if loading}
		<span
			class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
			aria-hidden="true"
		></span>
	{/if}
	{@render children()}
</button>
