/**
 * Provider and model vocabulary for the integrations form.
 *
 * Kept as data in its own module: these values travel to the backend in the
 * POST /link payload and must match what the rest of the app expects, so they
 * should be reviewable without reading any markup.
 */
export interface SelectOption {
	label: string;
	value: string;
}

export interface ModelOption extends SelectOption {
	provider: string;
}

const MODEL_TABLE: Record<string, [label: string, value: string][]> = {
	local: [
		['Llama3.2', 'llama3.2'],
		['Llama3.1', 'llama3.1'],
		['Llama3.3(70B)', 'llama3.3'],
		['Mixtral 8x7B', 'mixtral'],
		['QWQ', 'qwq'],
		['Phi 4', 'phi-4'],
		['Command R +', 'cmdR']
	],
	openai: [
		['GPT-4o', 'gpt-4o'],
		['GPT-4o-mini', 'gpt-4o-mini'],
		['GPT-o1', 'gpt-o1'],
		['GPT-o1-mini', 'gpt-o1-mini']
	],
	gemini: [
		['Gemini 2.0 Flash', 'gemini-2.0-flash'],
		['Gemini 1.5 Flash', 'gemini-1.5-flash'],
		['Gemini 1.5 Pro', 'gemini-1.5-pro']
	],
	anthropic: [
		['Claude 3.5 Sonnet', '3.5-sonnet'],
		['Claude 3.5 Haiku', '3.5-haiku'],
		['Claude 3 Opus', '3-opus']
	],
	deepseek: [['DeepSeek V3', 'deepseek-v3']]
};

export const modals: ModelOption[] = Object.entries(MODEL_TABLE).flatMap(([provider, entries]) =>
	entries.map(([label, value]) => ({ provider, label, value }))
);

export const providers: SelectOption[] = [
	{ label: 'OpenAI', value: 'openai' },
	{ label: 'ByteLlama', value: 'local' },
	{ label: 'Anthropic', value: 'anthropic' },
	{ label: 'Gemini', value: 'gemini' },
	{ label: 'DeepSeek', value: 'deepseek' }
];
