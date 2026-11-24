<script lang="ts">
	/**
	 * BytePort product mark and wordmark.
	 *
	 * The old sidebar rendered `<img src="/src/assets/img/byte.png">`, a path that
	 * does not exist in the bundle (the real files are `Byte.png` /
	 * `BytePort.png`), so the brand slot showed a broken image. This is an inline
	 * SVG mark instead: it cannot 404 and it inherits the accent colour.
	 */
</script>

<a
	href="/home"
	class="group flex items-center gap-2.5 rounded-md px-1 py-1 text-left"
	aria-label="BytePort, go to overview"
>
	<span
		class="bg-dark-primaryContainer text-dark-primary flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
		aria-hidden="true"
	>
		<svg
			viewBox="0 0 16 16"
			class="h-3.5 w-3.5"
			fill="none"
			stroke="currentColor"
			stroke-width="1.25"
			stroke-linecap="round"
			stroke-linejoin="round"
		>
			<path d="M8 1.9 13.7 5v6L8 14.1 2.3 11V5z" />
			<path d="M2.3 5 8 8.1 13.7 5" />
			<path d="M8 8.1v6" />
		</svg>
	</span>
	<span class="flex min-w-0 flex-col">
		<span class="text-dark-onSurface truncate text-[13px] font-semibold tracking-tight">
			BytePort
		</span>
		<span
			class="text-dark-onSurfaceVariant/70 truncate text-[10.5px] font-medium tracking-wide uppercase"
		>
			Deployment console
		</span>
	</span>
</a>
