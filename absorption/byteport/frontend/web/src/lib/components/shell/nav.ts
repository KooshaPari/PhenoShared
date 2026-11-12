/**
 * Navigation model for the BytePort application shell.
 *
 * This is the single place that maps a route to (a) the sidebar row and (b) the
 * title/subtitle shown in the slim page header. Route files stay free of
 * navigation chrome, so a page never has to know it is rendered inside a shell.
 *
 * The entries are plain data with no Svelte imports: `Sidebar.svelte` binds an
 * icon component to each `icon` key, and `AppShell.svelte` resolves the header
 * copy from `entryForPath()`.
 */

/** Icon keys the sidebar knows how to render. */
export type NavIconName = 'projects' | 'instances' | 'monitor' | 'settings';

export interface NavEntry {
	/** Route this entry describes. */
	href: string;
	/** Sidebar label and page title. */
	label: string;
	/** Second header line. Short and factual; empty means "render nothing". */
	subtitle: string;
	/** Icon key. Absent on entries that are not top-level sidebar rows. */
	icon?: NavIconName;
}

/**
 * Every route the shell knows a title for.
 *
 * Ordering here is irrelevant: `MATCH_ORDER` below sorts by specificity so a
 * nested route such as `/home/settings/profile` is never shadowed by `/home`.
 */
export const NAV_ENTRIES: NavEntry[] = [
	{
		href: '/home/projects',
		label: 'Projects',
		subtitle: 'Repositories and the deployments they build',
		icon: 'projects'
	},
	{
		href: '/home/instances',
		label: 'Instances',
		subtitle: 'Running virtual machines and their resources',
		icon: 'instances'
	},
	{
		href: '/home/monitor',
		label: 'Monitor',
		subtitle: 'Status of projects and instances',
		icon: 'monitor'
	},
	{
		href: '/home/settings',
		label: 'Settings',
		subtitle: 'Account, profile and integrations',
		icon: 'settings'
	},
	{
		href: '/home/settings/profile',
		label: 'Profile',
		subtitle: 'Personal account details'
	},
	{
		href: '/home/settings/integrations',
		label: 'Integrations',
		subtitle: 'Provider credentials and connections'
	},
	{
		href: '/home',
		label: 'Overview',
		subtitle: 'Projects and instances at a glance'
	}
];

/** Top-level rows only, in the order they appear in the sidebar. The type
 * predicate is load-bearing: the explicit `NavEntry[]` annotation removed it and
 * widened `item.icon` back to `NavIconName | undefined`. */
export const SIDEBAR_ENTRIES = NAV_ENTRIES.filter(
	(entry): entry is NavEntry & { icon: NavIconName } => Boolean(entry.icon)
);

/** Longest href first, so nested routes win the prefix match. */
const MATCH_ORDER = [...NAV_ENTRIES].sort((a, b) => b.href.length - a.href.length);

/**
 * Whether `href` should be shown as the current destination for `pathname`.
 *
 * Sub-routes keep their parent row active (`/home/settings/profile` highlights
 * Settings) which is what a desktop sidebar is expected to do.
 */
export function isActiveHref(pathname: string, href: string): boolean {
	return pathname === href || pathname.startsWith(`${href}/`);
}

/** Header copy for the current route. Falls back to a neutral shell title. */
export function entryForPath(pathname: string): NavEntry {
	return (
		MATCH_ORDER.find((entry) => isActiveHref(pathname, entry.href)) ?? {
			href: pathname,
			label: 'BytePort',
			subtitle: ''
		}
	);
}
