import type { Actions } from './$types.js';
import { user } from '$lib/../stores/user';
import { get } from 'svelte/store';

import { fail } from '@sveltejs/kit';
import { formSchema } from './schema';
import type { PageServerLoad } from './$types.js';
import { zod4 as zod4Adapter } from 'sveltekit-superforms/adapters';
import type { User } from '$lib/../stores/user';
import { superValidate, message } from 'sveltekit-superforms';

const getBaseUrl = async () => {
	return 'http://localhost:8081';
};

let client: User | null = null;
let baseUrl: string;

export const load: PageServerLoad = async () => {
	console.log('Loading settings page');
	try {
		baseUrl = await getBaseUrl();
		console.log('Base URL:', baseUrl);
		client = get(user).data;
		console.log('Client:', client);
		if (client) {
			console.log('Client:', client);
		}
	} catch (error) {
		console.error('Error in onMount:', error);
	}

	return {
		form: await superValidate(
			{
				name: client?.name || '',
				email: client?.email || '',
				password: { password: '', confirmPassword: '' }
			},
			zod4Adapter(formSchema)
		)
	};
};

const unsubscribe = user.subscribe((value) => {
	// Handle pending state
	if (value.status === 'pending') {
		console.log('Outer User state pending...');
		client = value.data;
		return; // Wait for initialization to complete
	}

	// Redirect if unauthenticated
	if (value.status !== 'authenticated') {
		console.log('User unauthenticated, redirecting...');
	} else {
		console.log('Authenticated user:', value.data);
		// Perform actions for authenticated user
		client = value.data; // Assign the authenticated user to `client`
	}
});

// Cleanup subscription when done
unsubscribe();

export const actions = {
	default: async ({ request }) => {
		const form = await superValidate(request, zod4Adapter(formSchema));

		console.log('POST', form);

		if (!form.valid) return fail(400, { form });

		return message(form, 'Updated Information');
	}
} satisfies Actions;
