import { z } from 'zod';

export const formSchema = z.object({
	name: z.string({ error: 'Required.' }),
	email: z.string({ error: 'Required.' }),
	password: z
		.object({
			password: z.string({ error: 'Required.' }),
			confirmPassword: z.string({ error: 'Required.' })
		})
		.superRefine(({ confirmPassword, password }, ctx) => {
			if (confirmPassword !== password) {
				ctx.addIssue({
					code: 'custom',
					message: 'The passwords did not match',
					path: ['confirmPassword']
				});
			}
		})
});

export type FormSchema = typeof formSchema;
