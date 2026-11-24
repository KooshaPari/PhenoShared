<script lang="ts">
	// @ts-nocheck
	import Icon from '@iconify/svelte';

	import { onMount } from 'svelte';
	import type { User } from '$lib/../stores/user';

	import { user, initializeUser } from '$lib/../stores/user';
	import { formSchema } from './schema';

	import { goto } from '$app/navigation';

	import SuperDebug, { type Infer, type SuperForm } from 'sveltekit-superforms';
	import { superForm } from 'sveltekit-superforms';
	import { zod4Client } from 'sveltekit-superforms/adapters';
	import * as Form from '$lib/components/ui/form/index.js';

	import { Input } from '$lib/components/ui/input/index.js';

	import { browser } from '$app/environment';

	export let data;
	type FormSchema = {
		name: string;
		email: string;
		password: {
			value: string;
			confirm: string;
		};
	};
	let initialized = false;

	const DEFAULT_CREDS: User = {
		uuid: '',
		name: '',
		email: ''
	};
	const mform = superForm(data.form, {
		validators: zod4Client(formSchema),
		dataType: 'json',
		onError: ({ result }) => {
			console.error('Form validation failed:', result);
		}
	});
	const { form, errors, enhance } = mform;

	let client: User | null = null;

	const menuItemsMap = new Map<string, string>([
		['Home', '/home '],
		['Profile', '/home/settings/profile'],
		['Integrations', '/home/settings/integrations'],
		['Settings', '/home/settings/profile']
	]);
	// edit personal info, delete acc
	// edit, add or delete API INFO
	const getBaseUrl = async () => {
		return 'http://localhost:8081';
	};

	// Handle user authentication and initialization
	const unsubscribe = user.subscribe(async (value) => {
		if (value.status === 'pending') {
			console.log('User state pending...');
			return;
		}

		if (value.status !== 'authenticated') {
			if (browser) {
				console.log('User unauthenticated, redirecting...');
				goto('/login');
			}
			return;
		}

		client = value.data;
		console.log('Authenticated user:', client);

		if (client) {
			const baseUrl = await getBaseUrl();
			console.log('SClient:', client);
			// Update form with fetched credentials
			form.set({
				name: client.name,
				email: client.email,
				password: {
					password: '',
					confirmPassword: ''
				}
			});
		}
	});
	async function updateUser() {
		console.log('Updating user...');
		const baseUrl = await getBaseUrl();
		const response = await fetch(`${baseUrl}/user/${client?.uuid}/creds`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				name: $form.name,
				email: $form.email,
				password: $form.password.password
			}),

			credentials: 'include'
		});
	}
	onMount(() => {
		const baseUrl = 'http://localhost:8081';
		initializeUser(baseUrl);
		return unsubscribe;
	});
</script>

<div class="bg-dark-surface flex h-screen w-screen overflow-x-hidden" id="mainDashPar">
	<div
		class="flex-ro bg-dark-surfaceContainer h-5/5 w-1/5 items-center justify-center"
		id="sideBar"
	>
		<button on:click={() => goto('/home')}>
			<img class="py-10" alt="BytePort" src="/src/assets/img/byte.png" />
		</button>``
		<div id="sideBarProfileCont"></div>
		<ul class="" id="menuList">
			{#each [...menuItemsMap] as [key, value]}
				<li class=" text-md w-5/5 py-2 text-center text-white">
					<button
						class="hover:bg-dark-surfaceContainerHigh active:bg-dark-surfaceContainer active:text-dark-surfaceBright w-4/5 py-2 text-center transition-all hover:-translate-y-1
						hover:rounded-full active:translate-y-0.5"
						on:click={() => {
							if (!value.includes('home')) {
								const mainBody = document.getElementById('bodyCont');
								if (mainBody) {
									mainBody.setAttribute('item', value);
								}
							}
							goto(value);
						}}
					>
						{key}
					</button>
				</li>
			{/each}
		</ul>
	</div>

	<div id="body" class="w-4/5">
		<div
			id="header"
			class=" bg-dark-surfaceContainerLow h-1/5 w-5/5 flex-col justify-between ps-2.5"
		>
			<div id="headerNav" class="h-3/5 pt-2.5">
				<div class="flex justify-end pe-2.5" id="navRight">
					<Icon
						class="hover:text-dark-primary active:text-dark-surfaceBright mx-1 h-6 w-6 cursor-pointer text-white"
						icon="ic:baseline-notifications"
					/>
					<Icon
						class="hover:text-dark-primary active:text-dark-surfaceBright mx-1 h-6 w-6 cursor-pointer text-white"
						on:click={() => goto('/home/settings')}
						icon="ic:baseline-account-circle"
					/>
				</div>
			</div>
			<div id="headerContent" class="h-2/5 text-4xl text-white">Settings</div>
		</div>
		<div id="mainBody">
			<form method="POST" class="space-y-8" use:enhance>
				<div class="openAICard align-center flex flex-row gap-3">
					<Form.Field class=" " name="name" form={mform}>
						<Form.Control let:attrs>
							<Form.Label>Username</Form.Label>
							<Input {...attrs} bind:value={$form.name as string} />
						</Form.Control>
						<Form.FieldErrors />
					</Form.Field>
					<Form.Field class=" " name="email" form={mform}>
						<Form.Control let:attrs>
							<Form.Label>Email</Form.Label>
							<Input {...attrs} type="email" bind:value={$form.email as string} />
						</Form.Control>
						<Form.FieldErrors />
					</Form.Field>
					<Form.Field class=" " name="password" form={mform}>
						<Form.Control let:attrs>
							<Form.Label>Password</Form.Label>
							<Input
								{...attrs}
								type="password"
								bind:value={$form.password.password as string}
							/>
							<Form.Label>Confirm Password</Form.Label>
							<Input
								{...attrs}
								type="password"
								bind:value={$form.password.confirmPassword as string}
							/>
						</Form.Control>
						<Form.FieldErrors />
					</Form.Field>
				</div>
				<Form.Button
					on:click={() => {
						updateUser();
					}}>Update Profile</Form.Button
				>
			</form>

			{#if browser}
				<SuperDebug data={$form} />
			{/if}
		</div>
		<div id="footer"></div>
	</div>
</div>

<style>
</style>
