import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	optimizeDeps: {
		include: ['lucide-svelte']
	},
	server: {
		host: '0.0.0.0',
		port: 5173,
		strictPort: true,
		hmr: {
			host: 'localhost',
			port: 5173,
			protocol: 'ws'
		},
		headers: {
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
			'Access-Control-Allow-Headers': 'Content-Type',
			'Access-Control-Allow-Credentials': 'true'
		}
	},
	ssr: {
		noExternal: ['lucide-svelte'] // Prevents treating it as an external dependency
	}
});
