<script lang="ts">
	/**
	 * Signed-in identity for the sidebar footer.
	 *
	 * Reads the existing session store; renders nothing while the session is
	 * still resolving or when the user is not authenticated (the pages already
	 * redirect to /login in that case, so a "signed out" chip would only flash).
	 */
	import { user } from '../../../stores/user';

	const identity = $derived.by(() => {
		if ($user.status !== 'authenticated' || !$user.data) return null;

		const name = $user.data.name?.trim() ?? '';
		const email = $user.data.email?.trim() ?? '';
		const source = name || email;
		const initials =
			source
				.split(/\s+/)
				.filter(Boolean)
				.slice(0, 2)
				.map((part) => part[0]?.toUpperCase() ?? '')
				.join('') || '?';

		return { name: name || email, email, initials };
	});
</script>

{#if identity}
	<div class="flex items-center gap-2.5 rounded-md px-2 py-1.5">
		<span
			class="bg-dark-surfaceContainerHighest text-dark-onSurfaceVariant flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold uppercase"
			aria-hidden="true"
		>
			{identity.initials}
		</span>
		<span class="flex min-w-0 flex-col">
			<span class="text-dark-onSurface truncate text-[12px] font-medium">{identity.name}</span
			>
			{#if identity.email && identity.email !== identity.name}
				<span class="text-dark-onSurfaceVariant truncate text-[11px]">{identity.email}</span
				>
			{/if}
		</span>
	</div>
{/if}
