<script lang="ts">
	import { goto } from '$app/navigation';
	import tempUser from '../+layout.svelte';
	import { initializeUser, setUser, user } from '../../stores/user';
	import { Button } from '$lib/components/ui/button';
	import type { User } from '../../stores/user';
	import { platform } from '@tauri-apps/plugin-os';

	let newUser: User;
	let Error: string = '';
	const getBaseUrl = async () => {
		if (window.__TAURI_INTERNALS__) {
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

	const getClientUrl = () => {
		if (window.__TAURI_INTERNALS__) {
			const currentPlatform: string | null = platform();
			if (currentPlatform == null) {
				return 'http://localhost:5173';
			}

			switch (currentPlatform) {
				case 'android':
					return 'http:///10.0.2.2:5173';
				case 'windows':
					return 'http://localhost:5173';
				default:
					return 'http://localhost:5173';
			}
		} else {
			return 'http://localhost:5173';
		}
	};

	async function login() {
		const baseUrl = await getBaseUrl();
		console.log('Base URL:', baseUrl);
		const regUserForm = document.forms.namedItem('regUser');
		if (!regUserForm) {
			Error = 'Login form was not found.';
			return;
		}
		const formData = new FormData(regUserForm);
		let newUser = {
			Email: String(formData.get('email') ?? ''),
			Password: String(formData.get('password') ?? '')
		};
		const { Email, Password } = newUser;
		try {
			console.log(`${baseUrl}/login`);
			const response = await fetch(`${baseUrl}/login`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ Email, Password }),
				credentials: 'include'
			});

			console.log('Response Status:', response.status);
			console.log('Response OK:', response.ok);
			console.log('Resp Credentials: ', response.headers.get('Authorization'));
			console.log('Resp Cookies: ', response.headers.get('authToken'));
			console.log('All Response Headers:');
			for (const [key, value] of response.headers.entries()) {
				console.log(`${key}: ${value}`);
			}
			console.log('Response: ', response);

			const data = await response.json();

			if (response.ok) {
				console.log('Login successful:', data);
				console.log('Initializing User: ', baseUrl);
				await initializeUser(baseUrl);
				if (window.__TAURI_INTERNALS__) {
					//const { getCookies } =   await import('@tauri-apps/plugin-http');
					//const cookies = await getCookies();
					//console.log('Tauri Stored Cookies:', cookies);
				}
				//setUser(true, data as User);
				goto(`/home`);
			} else {
				Error = data.message || data.error || 'An unknown error occurred';
				console.log('Login failed:', Error);
			}
		} catch (err) {
			console.error('Error during Login:', err);
			Error = 'An error occurred during login.';
		}
	}
</script>

<div class="bg-dark-surface h-screen w-screen overflow-x-hidden">
	<div
		id="header"
		class=" bg-dark-surfaceContainerLow h-1/5 w-5/5 flex-col justify-between ps-2.5"
	>
		<div id="headerNav" class="h-3/5 pt-2.5"></div>
		<div id="headerContent" class="h-2/5 text-4xl text-white">Hello.</div>
	</div>
	<div id="body" class="px-2.5 pt-5">
		<h1 class="text-2xl text-white">Please Register Below...</h1>
		<div id="logCont">
			<form class="flex-row" name="regUser" on:submit|preventDefault={login}>
				<div>
					<label for="email">Email</label>
					<input name="email" placeholder="Email" required type="email" />
				</div>
				<div>
					<label for="password">Password</label>
					<input
						name="password"
						pattern="(?=.*\d)(?=.*[a-z])(?=.*[A-Z])+"
						type="password"
						required
						placeholder="Password"
					/>
				</div>
				<div>
					<input
						type="submit"
						value="Log In"
						class="bg-dark-surfaceContainerHigh text-dark-onSurface hover:bg-dark-surfaceContainerHighest active:bg-dark-surfaceContainer rounded-full p-2"
					/>
					<button
						on:click={() => goto(`${getClientUrl()}/signup`)}
						class="bg-dark-surfaceContainerHigh text-dark-onSurface hover:bg-dark-surfaceContainerHighest active:bg-dark-surfaceContainer my-3 rounded-full p-2"
					>
						Sign up
					</button>
				</div>
			</form>
		</div>
	</div>
</div>

<style>
	@reference '../../app.css';

	#logCont form > div > input {
		@apply bg-dark-surfaceContainerHigh text-dark-onSurface placeholder-dark-onSurfaceVariant selection:bg-dark-surfaceContainer hover:bg-dark-surfaceContainerHighest my-2 rounded-full;
		border: none;
	}
	#logCont form > div > label {
		@apply text-dark-onSurface;
	}
	#logCont form > div {
		@apply h-1/5 w-screen flex-row items-center justify-center;
	}
</style>
