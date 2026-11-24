<script lang="ts" context="module">
	// @ts-nocheck
	import type { FormPath, SuperForm } from 'sveltekit-superforms';
	type T = Record<string, unknown>;
	type U = FormPath<T>;
</script>

<script lang="ts" generics="T extends Record<string, unknown>, U extends FormPath<T>">
	import * as FormPrimitive from 'formsnap';
	import { cn } from '$lib/utils.js';

	type $$Props = { form: any; name: any; class?: string | null | undefined };
	const Field = FormPrimitive.Field as any;

	export let form: any;
	export let name: any;

	let className: $$Props['class'] = undefined;
	export { className as class };
</script>

<svelte:component this={Field} {form} {name} let:constraints let:errors let:tainted let:value>
	<div class={cn('space-y-2', className)}>
		<slot {constraints} {errors} {tainted} {value} />
	</div>
</svelte:component>
