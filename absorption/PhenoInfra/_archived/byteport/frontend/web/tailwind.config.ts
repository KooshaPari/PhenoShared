import aspectRatio from '@tailwindcss/aspect-ratio';
import containerQueries from '@tailwindcss/container-queries';
import forms from '@tailwindcss/forms';
import tailwindScrollbar from 'tailwind-scrollbar';
import { fontFamily } from 'tailwindcss/defaultTheme';
import type { Config } from 'tailwindcss';

// Existing material scheme mapped into Tailwind for both shadcn and bg-dark-X references
const materialTheme = {
	primary: '#80d5cf',
	onPrimary: '#003734',
	primaryContainer: '#00504c',
	onPrimaryContainer: '#9df1eb',
	secondary: '#83d2e3',
	onSecondary: '#00363e',
	secondaryContainer: '#004e5a',
	onSecondaryContainer: '#a2eeff',
	tertiary: '#9bcbfb',
	onTertiary: '#003353',
	tertiaryContainer: '#0e4a73',
	onTertiaryContainer: '#cee5ff',
	error: '#ffb4ab',
	onError: '#690005',
	background: '#0e1514',
	onBackground: '#dde4e2',
	surface: '#101418',
	onSurface: '#e1e2e8',
	surfaceVariant: '#3f4948',
	onSurfaceVariant: '#bec9c7',
	outline: '#889391',
	outlineVariant: '#3f4948',
	surfaceDim: '#101418',
	surfaceBright: '#36393e',
	surfaceContainerLowest: '#0b0e13',
	surfaceContainerLow: '#191c20',
	surfaceContainer: '#1d2024',
	surfaceContainerHigh: '#272a2f',
	surfaceContainerHighest: '#32353a'
};

const config: Config = {
	darkMode: ['class'], // Enable dark mode support
	content: ['./src/**/*.{html,js,svelte,ts}'], // Ensure all files are scanned for Tailwind classes
	safelist: ['dark'], // Ensure dark mode classes are preserved
	theme: {
		extend: {
			colors: {
				// Map shadcn variables to your material scheme
				border: 'hsl(var(--border) / <alpha-value>)',
				input: 'hsl(var(--input) / <alpha-value>)',
				ring: 'hsl(var(--ring) / <alpha-value>)',
				background: materialTheme.background,
				foreground: materialTheme.onBackground,
				primary: {
					DEFAULT: materialTheme.primary,
					foreground: materialTheme.onPrimary
				},
				secondary: {
					DEFAULT: materialTheme.secondary,
					foreground: materialTheme.onSecondary
				},
				destructive: {
					DEFAULT: materialTheme.error,
					foreground: materialTheme.onError
				},
				muted: {
					DEFAULT: materialTheme.surfaceVariant,
					foreground: materialTheme.onSurfaceVariant
				},
				accent: {
					DEFAULT: materialTheme.secondary,
					foreground: materialTheme.onSecondary
				},
				popover: {
					DEFAULT: materialTheme.surface,
					foreground: materialTheme.onSurface
				},
				card: {
					DEFAULT: materialTheme.surface,
					foreground: materialTheme.onSurface
				},
				// Retain darkTheme for existing references (e.g., bg-dark-X)
				dark: materialTheme
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)'
			},
			fontFamily: {
				sans: [...fontFamily.sans]
			}
		},
		container: {
			center: true,
			padding: '2rem',
			screens: {
				'2xl': '1400px'
			}
		}
	},
	plugins: [forms, containerQueries, aspectRatio, tailwindScrollbar]
};

export default config;
