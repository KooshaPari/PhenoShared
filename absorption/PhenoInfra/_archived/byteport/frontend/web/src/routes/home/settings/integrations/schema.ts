import { z } from 'zod';

const modals = [
	{ label: 'ByteLLama', value: 'local' },
	{ label: 'OpenAI-4o', value: 'openai' }
] as const;

type Modal = (typeof modals)[number]['value'];
const aiProviderSchema = z.object({
	modal: z.string(),
	apiKey: z.string()
});

export const formSchema = z.object({
	github: z.string({ error: 'Required.' }),
	aws: z.object({
		accessKey: z.string({ error: 'Required.' }),
		secretKey: z.string({ error: 'Required.' })
	}),
	llm: z.object({
		provider: z.string({ error: 'Required.' }),
		providers: z.record(z.string(), aiProviderSchema)
	}),
	// Hack: https://github.com/colinhacks/zod/issues/2280
	demo: z.object({
		endpoint: z.string({ error: 'Required.' }),
		apiKey: z.string({ error: 'Required.' })
	})

	/*modal: z.enum(modals.map((modal) => modal.value) as [Modal, ...Modal[]], {
		invalid_type_error: 'Select a modal',
		required_error: 'Please modal a font.'
	})*/
});

export type FormSchema = typeof formSchema;
