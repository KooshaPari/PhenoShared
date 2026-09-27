<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Button from '$lib/components/ui/button';
	import { goto } from '$app/navigation';
	import { populateLists, getBaseUrl } from '$lib/utils';

	import * as Accordion from '$lib/components/ui/accordion';
	import Icon from '@iconify/svelte';
	import ProjectForm from './projectForm.svelte';
	import type { Project, Instance } from '$lib/utils';
	import { onMount, onDestroy } from 'svelte';
	import ReviewCard from './reviewCard.svelte';
	import GitSearch from './gitSearch.svelte';
	import { platform } from '@tauri-apps/plugin-os';
	import { Description } from 'formsnap';
	import { user, initializeUser } from '../stores/user';
	import type { User } from '../stores/user';
	import { json } from '@sveltejs/kit';
	const SERVER_URL = 'http://localhost:8081';
	let projheadTxt: string = 'Welcome.';
	let stage = 1;
	let client: User | null = null;
	let projHeadDescr: string = "Let's Begin First Time Setup";
	function terminateInstance(project: Project) {
		project.User = client;
		const resp = fetch(`${SERVER_URL}/terminate`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(project),
			credentials: 'include'
		});
	}
	const unsubscribe = user.subscribe((value) => {
		// Handle pending state
		if (value.status === 'pending') {
			console.log('User state pending...');
			return; // Wait for initialization to complete
		}

		// Redirect if unauthenticated
		if (value.status !== 'authenticated') {
			console.log('User unauthenticated, redirecting...');
			goto('/login');
		} else {
			console.log('Authenticated user:', value.data);
			// Perform actions for authenticated user
			client = value.data; // Assign the authenticated user to `client`
		}
	});
	let deployments = $state<Array<Instance>>([]);
	let props = $props();
	let project: Project = props.project;
	onMount(async () => {
		let project: Project = props.project;
		const baseUrl = await getBaseUrl();
		// parson json deployment json string to object
		project.Deployments = JSON.parse(project.DeploymentsJSON as string);

		deployments = project.Deployments
			? (Object.entries(project.Deployments).map(([key, value]) => value) as Instance[])
			: [];
		for (let i = 0; i < deployments.length; ++i) {
			for (let j = 0; j < deployments[i].Resources.length; ++j) {
				console.log('Res: ', deployments[i].Resources[j].status);
			}
		}

		console.log('ProjSSSSects: ', project);

		// Ensure the user initialization is complete
		await initializeUser(baseUrl);
	});
</script>

<section class="relative h-3/5 w-screen">
	<Dialog.Root>
		<Dialog.Trigger
			><!-- Block Representing Access IMG URL Bloc, Name, status, -->

			<h1 class=" text-2xl">{project.name}</h1>
		</Dialog.Trigger>

		<Dialog.Content class=" w-100  max-w-fit   items-center justify-center space-y-4"
			><Dialog.Header>
				<Dialog.Title>{project.name}</Dialog.Title>

				<Dialog.Description><h1>{project.description}</h1></Dialog.Description>
			</Dialog.Header>
			<!--Access Window, Details view, resource view, status -->
			<div class="vmView">
				<div class="cardLeft">
					<!--Access Window-->
				</div>
				<div class="cardRight">
					<!--Access URL, Status, Info, ProjectURL, Project Info, Resources Accordian-->
					<h1>Name: {project.name}</h1>
					<h2>Description: {project.description}</h2>

					<Button.Root on:click={() => window.open(project.access_url, '_blank')}
						>Access</Button.Root
					>
					<!--<Button.Root on:click={() => (window.location.href = project.access_url)}
						>{#if project.Deployments}Start{:else}Stop{/if}</Button.Root
					>
					<Button.Root on:click={() => (window.location.href = project.access_url)}
						>Restart</Button.Root
					>
						<Button.Root on:click={() => (window.location.href = project.access_url)}
						>Clone</Button.Root
					>-->

					<Button.Root on:click={() => terminateInstance(project)}
						>Terminate(X)</Button.Root
					>

					<div
						id="resources"
						class="max-h-[65vh] min-h-[45vh] max-w-[60vw] min-w-[50vw] overflow-y-scroll"
					>
						<Accordion.Root type="single">
							<Accordion.Item value="item-1">
								<Accordion.Trigger>Resources</Accordion.Trigger>
								<Accordion.Content>
									{#if project.Deployments}
										{#each deployments as instance}
											<div class="instance">
												<Accordion.Root type="single">
													<Accordion.Item value="item-1">
														<Accordion.Trigger
															>{instance.Name ??
																instance.name}</Accordion.Trigger
														>
														<Accordion.Content>
															<div
																style="display:grid"
																class="  w-1/1 grid-flow-row grid-cols-2 gap-1"
															>
																{#each instance.Resources as resource}
																	<div
																		class="bg-dark-surfaceContainerHigh mb-2 flex flex-col rounded-lg p-4"
																	>
																		<h1>
																			Name: {resource.name}
																		</h1>
																		// trim arn remove first 8 chars,
																		and trim to 25 chars
																		<h1>ARN: {resource.arn}</h1>
																		<h1>
																			Service: {resource.service}
																		</h1>

																		<h1>
																			Type: {resource.type}
																		</h1>
																		<h3
																			class="text-md
												{resource.status === 'Running' || resource.status === 'deployed'
																				? 'text-green-500'
																				: resource.status ===
																					  'Stopped'
																					? 'text-red-500'
																					: 'text-yellow-500'}"
																		>
																			Status: {resource.status}
																		</h3>
																	</div>
																{/each}
															</div>
														</Accordion.Content>
													</Accordion.Item>
												</Accordion.Root>
											</div>
										{/each}
									{:else}
										<p class="text-dark-onSurfaceVariant">
											No deployments found
										</p>
									{/if}
								</Accordion.Content>
							</Accordion.Item>
						</Accordion.Root>
					</div>
				</div>
			</div>
			<Dialog.Footer></Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>
</section>
