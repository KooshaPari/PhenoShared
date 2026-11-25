<script lang="ts">
	// @ts-nocheck
	import { Input } from '$lib/components/ui/input';
	import Check from 'lucide-svelte/icons/check';
	import ChevronsUpDown from 'lucide-svelte/icons/chevrons-up-down';
	import { tick } from 'svelte';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { cn } from '$lib/utils.js';

	type ComboItem = {
		value: string;
		label: string;
	};

	type Props = {
		items: ComboItem[];
		placeholder: string;
		onselect?: (event: CustomEvent<string>) => void;
	};

	let { items, placeholder, onselect }: Props = $props();

	let open = $state(false);
	let value = $state('');
	let selectedValue = $state('');

	$effect(() => {
		selectedValue = items.find((f) => f.value === value)?.label ?? `Select a ${placeholder}...`;
	});

	// We want to refocus the trigger button when the user selects
	// an item from the list so users can continue navigating the
	// rest of the form with the keyboard.
	async function closeAndFocusTrigger(triggerId: string) {
		open = false;
		console.log('ID: ', triggerId);
		tick().then(() => {
			console.log('CL');
			document.getElementById(triggerId)?.focus();
		});
	}
</script>

<Popover.Root bind:open let:ids>
	<Popover.Trigger asChild let:builder>
		<Button
			builders={[builder]}
			variant="outline"
			role="combobox"
			aria-expanded={open}
			class="w-[200px] justify-between"
		>
			{selectedValue}
			<ChevronsUpDown class="ml-2 h-4 w-4 shrink-0 opacity-50" />
		</Button>
	</Popover.Trigger>
	<Popover.Content class="w-[200px] p-0">
		<Command.Root>
			<Command.Group>
				{#each items as item}
					<Command.Item
						class="cursor-pointer"
						value={item.value}
						onSelect={(currentValue) => {
							value = currentValue;
							onselect?.(new CustomEvent('select', { detail: currentValue }));
							closeAndFocusTrigger(ids.trigger);
						}}
					>
						<Check
							class={cn('mr-2 h-4 w-4', value !== item.value && 'text-transparent')}
						/>
						{item.label}
					</Command.Item>
				{/each}
			</Command.Group>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
