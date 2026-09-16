<script lang="ts">
	// @ts-nocheck
	import { Dialog as DialogPrimitive } from 'bits-ui';
	type $$Props = DialogPrimitive.PortalProps;
</script>

<DialogPrimitive.Portal {...$$restProps}>
	<slot />
</DialogPrimitive.Portal>
