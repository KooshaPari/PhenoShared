<script lang="ts">
	/**
	 * Primary navigation rail.
	 *
	 * Replaces the 2023 sidebar that lived inside every page: a raw `<img>` bound
	 * to a path that does not exist, a `<ul>` of `<button>`s with `py-2` outer
	 * padding plus `py-2` inner padding, and no active state at all, so every page
	 * looked identical. Icons are lucide at 16px / stroke-width 1.75 to match the
	 * rest of the desktop chrome.
	 */
	import Activity from 'lucide-svelte/icons/activity';
	import Folder from 'lucide-svelte/icons/folder';
	import Server from 'lucide-svelte/icons/server';
	import Settings from 'lucide-svelte/icons/settings';
	import type { Component } from 'svelte';
	import { page } from '$app/state';
	import NavItem from './NavItem.svelte';
	import ProductMark from './ProductMark.svelte';
	import UserChip from './UserChip.svelte';
	import { SIDEBAR_ENTRIES, isActiveHref, type NavIconName } from './nav';

	// lucide ships Svelte 4 class components and Svelte 5's `Component` type does
	// not accept them structurally, so the map is cast once here instead of at
	// every render site.
	const icons = {
		projects: Folder,
		instances: Server,
		monitor: Activity,
		settings: Settings
	} as unknown as Record<NavIconName, Component>;

	const pathname = $derived(page.url.pathname);
</script>

<aside
	class="border-border bg-dark-surface flex h-full w-60 shrink-0 flex-col border-r"
	aria-label="Application"
>
	<div class="flex h-14 shrink-0 items-center px-3">
		<ProductMark />
	</div>

	<nav
		class="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 pb-2"
		aria-label="Primary"
	>
		{#each SIDEBAR_ENTRIES as item (item.href)}
			{@const Icon = icons[item.icon]}
			<NavItem
				href={item.href}
				label={item.label}
				active={isActiveHref(pathname, item.href)}
				icon={Icon}
			/>
		{/each}
	</nav>

	<div class="border-border shrink-0 border-t p-2">
		<UserChip />
	</div>
</aside>
