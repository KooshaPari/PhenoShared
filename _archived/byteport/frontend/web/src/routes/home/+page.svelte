<script lang="ts">
	import Icon from '@iconify/svelte';
	import type { Project, Instance } from '$lib/utils.ts';

	import { onMount } from 'svelte';
	import type { User } from '../../stores/user';
	import { user, initializeUser } from '../../stores/user';

	import { goto } from '$app/navigation';
	import { platform } from '@tauri-apps/plugin-os';
	import Dialog from '../../components/addProjectDialog.svelte';
	import ProjectCard from '../../components/projectPopup.svelte';
	import { populateLists } from '$lib/utils';
	const getBaseUrl = async () => {
		if ((window as any).__TAURI_INTERNALS__) {
			const currentPlatform: string = platform();
			console.log(currentPlatform);
			switch (currentPlatform) {
				case 'android':
					return 'http://10.0.2.2:8081';
				case 'windows':
					return 'http://localhost:8081';
				default:
					return 'http://localhost:8081';
			}
		} else {
			return 'http://localhost:8081';
		}
	};

	let client: User | null = null;
	// convert to map name, '/name'
	const menuItemsMap = new Map<string, string>([
		['Projects', '/home/projects'],
		['Instances', '/home/instances'],
		['Monitor', '/home/monitor'],
		['Settings', '/home/settings/integrations']
	]);
	let projects: Project[];

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
			populateLists().then((p) => {
				projects = p;
			}); // Populate user-specific lists or data
		}
	});

	onMount(() => {
		getBaseUrl().then((baseUrl) => {
			console.log('Base URL:', baseUrl);
			// Ensure the user initialization is complete
			initializeUser(baseUrl);
		});
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
						on:click={() => goto('/settings')}
						icon="ic:baseline-account-circle"
					/>
				</div>
			</div>
			<div id="headerContent" class="h-2/5 text-4xl text-white">Hello.</div>
		</div>
		<div id="mainBody">
			<div id="instanceSec" class="h-2/5 w-5/5 overflow-x-scroll">
				<h1 class="text-dark-secondary p-2">Instances</h1>
				<div id="instances" class="flex w-max overflow-y-visible p-2">
					<div
						class="hover:bg-dark-surfaceContainerHighest active:bg-dark-surfaceContainer bg-dark-surfaceContainerHigh text-dark-onSurface m-0.5 mx-1.5 flex h-64 w-48 items-center justify-center rounded-lg transition-all"
					>
						<Icon
							on:click={() => {
								console.log('LO');
							}}
							class="active:text-dark-surfaceVariant hover:bg-dark-onPrimaryContainer active:bg-dark-onPrimary bg-dark-primary text-dark-onPrimary h-max w-max rounded-full p-5 text-4xl transition-all hover:-translate-y-2 hover:scale-105 active:translate-y-1 active:scale-100"
							icon="ic:baseline-add"
						/>
					</div>
					<!--{#each instances as instance}-->
					<!-- <div
							class="bg-dark-surfaceContainerHigh text-dark-onSurface m-0.5 mx-1.5 h-64 w-48 rounded-lg transition-all hover:-translate-y-2 hover:scale-105 active:translate-y-1 active:scale-100"
						>
							<img
								src="/src/assets/img/byteport copy.png"
								alt="BytePort"
								class="h-5/5 bg-dark-surfaceContainerHighest p-2"
							/>
							<div
								class=" bg-dark-surfaceContainerHigh grid-flow-col grid-cols-2 px-2 pb-3 pt-1 text-sm"
							></div>
					{/each}-->
				</div>
			</div>
			<div id="projectsSec" class="h-2/5 w-5/5 overflow-x-scroll">
				<h1 class="text-dark-secondary p-2">Projects</h1>
				<div id="projects" class="flex w-max overflow-y-visible p-2">
					<div
						class="hover:bg-dark-surfaceContainerHighest active:bg-dark-surfaceContainer bg-dark-surfaceContainerHigh text-dark-onSurface m-0.5 mx-1.5 flex h-64 w-48 items-center justify-center rounded-lg transition-all"
					>
						<Dialog></Dialog>
					</div>
					{#each projects as project}
						<div
							class="hover:bg-dark-surfaceContainerHighest active:bg-dark-surfaceContainer bg-dark-surfaceContainerHigh text-dark-onSurface align-center m-0.5 mx-1.5 flex h-64 w-48 flex-col items-center justify-center rounded-lg transition-all"
						>
							<div
								class=" active:text-dark-surfaceVariant hover:bg-dark-onSecondaryContainer active:bg-dark-onPrimary bg-dark-primaryContainer text-dark-onPrimary m-5 h-max w-5/5 rounded-lg p-5 text-4xl transition-all hover:-translate-y-2 hover:scale-105 active:translate-y-1 active:scale-100"
							>
								<a href={project.access_url} target="_blank">
									<div class="accessBlocImg h-3/5">
										<img src={'src/assets/img/Byte.png'} alt="project" />
									</div>
								</a>
							</div>
							<div
								class="bg-dark-surfaceContainerHigh hpmax w-4/5 grid-flow-col grid-cols-2 px-2 pt-1 pb-3 text-sm"
							>
								<ProjectCard {project}></ProjectCard>
							</div>
							<!-- <img
								src="/src/assets/img/byteport copy.png"
								alt="BytePort"
								class="h-5/5 bg-dark-surfaceContainerHighest p-2"
							/>
							<div class="h-5/5 bg-dark-surfaceContainerHigh flex-col px-2 pb-3 pt-3 text-sm"></div>-->
						</div>
					{/each}
				</div>
			</div>
		</div>
		<div id="footer"></div>
	</div>
</div>

<style>
</style>
