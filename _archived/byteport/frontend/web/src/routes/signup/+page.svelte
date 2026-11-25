<script lang="ts">
	import { goto } from '$app/navigation';
	import tempUser from '../+layout.svelte';
	import { initializeUser, setUser, user } from '../../stores/user';
	import type { User } from '../../stores/user';

	let newUser: User;
	let Error: string = '';

	// Get base URL with correct port
	const getBaseUrl = () => {
		const url = new URL(window.location.href);
		url.hostname = url.hostname.split('.').slice(-2).join('.');
		url.port = '8081';
		return url.origin;
	};

	async function signUpUser() {
		const regUserForm = document.forms.namedItem('regUser');
		if (!regUserForm) {
			Error = 'Signup form was not found.';
			return;
		}
		const formData = new FormData(regUserForm);
		let newUser = {
			Name: String(formData.get('name') ?? ''),
			Email: String(formData.get('email') ?? ''),
			Password: String(formData.get('password') ?? '')
		};

		const { Name, Email, Password } = newUser;
		try {
			const baseUrl = getBaseUrl();
			const response = await fetch(`${baseUrl}/signup`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ Name, Email, Password }),
				credentials: 'include'
			});

			console.log('Response Status:', response.status);
			console.log('Response OK:', response.ok);

			const data = await response.json();

			if (response.ok) {
				console.log('Signup successful:', data);
				await initializeUser(baseUrl);
				goto('/fts');
			} else {
				Error = data.message || data.error || 'An unknown error occurred';
				console.log('Signup failed:', Error);
			}
		} catch (err) {
			console.error('Error during signup:', err);
			Error = 'An error occurred during signup.';
		}
	}
</script>
