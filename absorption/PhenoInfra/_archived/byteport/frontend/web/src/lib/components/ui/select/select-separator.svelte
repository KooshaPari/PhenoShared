<script lang="ts">
	// @ts-nocheck
	import { cn } from '$lib/utils.js';

	type $$Props = { class?: string | null | undefined };

	let className: $$Props['class'] = undefined;
	export { className as class };
</script>

<div role="separator" class={cn('bg-muted -mx-1 my-1 h-px', className)} {...$$restProps}></div>
