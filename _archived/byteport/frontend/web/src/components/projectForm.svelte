<script lang="ts">
	import { Input } from '$lib/components/ui/input';

	import Check from 'lucide-svelte/icons/check';
	import ChevronsUpDown from 'lucide-svelte/icons/chevrons-up-down';
	import { tick } from 'svelte';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Button from '$lib/components/ui/button';
	import { cn } from '$lib/utils.js';
	import Combo from './combo.svelte';
	let typeValue = $state('');
	let platformValue = $state('');
	const platformArray = [
		{ value: 'web', label: 'Web' },
		{ value: 'mobile', label: 'Mobile' },
		{ value: 'desktop', label: 'Desktop' }
	];

	const typeArray = [
		{ value: 'single-page', label: 'Single Page' },
		{ value: 'multi-page', label: 'Multi Page' },
		{ value: 'plugin', label: 'Plugin' },
		{ value: 'service', label: 'Service' }
	];
</script>

<form id="form-stage-2">
	<Input placeholder="Project Name" name="name" />
	<Input placeholder="Description" name="description" />
	<Input placeholder="NVMS Path" name="nvms" />
	<Input type="hidden" name="type" bind:value={typeValue} />
	<Input type="hidden" name="platform" bind:value={platformValue} />
	<Combo
		items={platformArray}
		onselect={(e: CustomEvent<string>) => (platformValue = e.detail)}
		placeholder="Platform"
	/>
	<Combo
		items={typeArray}
		onselect={(e: CustomEvent<string>) => (typeValue = e.detail)}
		placeholder="Type"
	/>
</form>
