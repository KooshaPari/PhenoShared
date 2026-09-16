<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Button from '$lib/components/ui/button';
	import Icon from '@iconify/svelte';
	import ProjectForm from './projectForm.svelte';
	import type { Project, Instance } from '$lib/utils';
	import { onMount } from 'svelte';
	import ReviewCard from './reviewCard.svelte';
	import GitSearch from './gitSearch.svelte';
	import { user, initializeUser } from '../stores/user';
	import type { User } from '../stores/user';
	import { getBaseUrl } from '$lib/utils';
	const SERVER_URL = 'http://localhost:8081';
	let projheadTxt: string = 'Welcome.';
	let stage = 1;
	let client: User | null = null;
	let projHeadDescr: string = "Let's Begin First Time Setup";
	let newProject: Project = {
		User: client,
		Repository: null,
		UUID: '',
		name: 'New Project',
		description: '',
		Type: '',
		Platform: '',
		Deployments: null,
		access_url: '',
		NVMS: null,
		ReadMe: '',
		DeploymentsJSON: ''
	};
	import { platform } from '@tauri-apps/plugin-os';

	const unsubscribe = user.subscribe((value) => {
		// Handle pending state
		if (value.status === 'pending') {
			console.log('User state pending...');
			return; // Wait for initialization to complete
		}

		// Redirect if unauthenticated
		if (value.status !== 'authenticated') {
			console.log('User unauthenticated, redirecting...');
			// destroy dialog
			return;
		} else {
			client = value.data; // Assign the authenticated user to `client`
		}
	});

	onMount(async () => {
		const baseUrl = await getBaseUrl();

		// Ensure the user initialization is complete
		await initializeUser(baseUrl);
	});
	async function deployProject() {
		newProject.User = client;

		console.log('Deploying Project:', newProject);
		// Send the project to the backend
		const response = await fetch(`${SERVER_URL}/deploy`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			credentials: 'include',
			body: JSON.stringify(newProject)
		});
	}

	function addNewProject() {
		// open dialog
		stage = 1;
		setStage();
		return;
	}
	async function setStage() {
		if (stage == 2) {
			const projForm = document.querySelector(`#form-stage-${stage}`) as HTMLFormElement;
			if (!projForm.checkValidity()) {
				projForm.reportValidity(); // Show validation errors
				return; // Stop progression
			}

			const formData = new FormData(projForm);
			const data = Object.fromEntries(formData.entries());

			switch (stage) {
				case 2:
					newProject.name = data.name as string;
					newProject.description = data.description as string;
					newProject.Type = data.type as string;
					newProject.Platform = data.platform as string;

					break;

				default:
					console.log('Odd Stage');
					break;
			}

			console.log(`Stage ${stage} data collected:`, newProject);
		}

		stage++;
		switch (stage) {
			case 1:
				projheadTxt = "Let's Start Off...";
				break;
			case 2:
				projheadTxt = "Let's Finish Up...";
				break;
			case 3:
				projheadTxt = 'Review Details';
				break;
			case 4:
				projheadTxt = 'Deploying...';
				stage = 0;
				await deployProject();

				break;
			case 5:
				projheadTxt = 'Deployment Complete!';
				break;
			default:
				projheadTxt = 'Setup ERR!';
				break;
		}
	}
</script>

<Dialog.Root>
	<Dialog.Trigger
		><Icon
			on:click={() => addNewProject()}
			class="active:text-dark-surfaceVariant hover:bg-dark-onPrimaryContainer active:bg-dark-onPrimary bg-dark-primary text-dark-onPrimary h-max w-max rounded-full p-5 text-4xl transition-all hover:-translate-y-2 hover:scale-105 active:translate-y-1 active:scale-100"
			icon="ic:baseline-add"
		/></Dialog.Trigger
	>

	<Dialog.Content class="flex flex-col items-center justify-center space-y-4"
		><Dialog.Header>
			<Dialog.Title>{newProject.name}</Dialog.Title>

			<Dialog.Description><h1>{projheadTxt}</h1></Dialog.Description>
		</Dialog.Header>
		{#if stage == 1}
			<GitSearch
				select={(e) => {
					const selectedRepo = e;
					console.log('TEST');
					newProject.Repository = selectedRepo;
					setStage();
				}}
			/>
		{:else if stage == 2}<ProjectForm />{:else if stage == 3}<ReviewCard
				project={newProject}
			/>{:else if stage == 4}{/if}
		<Dialog.Footer>
			{#if stage == 3}
				<Button.Root
					variant="ghost"
					on:click={() => {
						stage = stage - 2;
						setStage();
					}}>Back</Button.Root
				>
				<Button.Root
					variant="outline"
					on:click={() => {
						setStage();
					}}>Deploy</Button.Root
				>
			{:else if stage == 2}
				<Button.Root
					variant="ghost"
					on:click={() => {
						stage = stage - 2;
						setStage();
					}}>Back</Button.Root
				>
				<Button.Root
					variant="outline"
					on:click={() => {
						setStage();
					}}>Review</Button.Root
				>
			{/if}
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
