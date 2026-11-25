import { describe, expect, it } from 'vitest';
import { entryForPath, isActiveHref, NAV_ENTRIES, SIDEBAR_ENTRIES } from './nav';

describe('NAV_ENTRIES', () => {
	it('gives every top-level row an icon and a subtitle', () => {
		for (const entry of SIDEBAR_ENTRIES) {
			expect(entry.icon, `${entry.href} must have an icon`).toBeTruthy();
			expect(entry.subtitle.length).toBeGreaterThan(0);
		}
	});

	it('keeps nested settings routes out of the sidebar', () => {
		const hrefs = SIDEBAR_ENTRIES.map((e) => e.href);
		expect(hrefs).toContain('/home/settings');
		expect(hrefs).not.toContain('/home/settings/profile');
		expect(hrefs).not.toContain('/home/settings/integrations');
	});

	it('declares exactly the four shell destinations', () => {
		expect(SIDEBAR_ENTRIES.map((e) => e.href)).toEqual([
			'/home/projects',
			'/home/instances',
			'/home/monitor',
			'/home/settings'
		]);
	});
});

describe('isActiveHref', () => {
	it('matches the exact route', () => {
		expect(isActiveHref('/home/projects', '/home/projects')).toBe(true);
	});

	it('keeps a parent row active for its sub-routes', () => {
		expect(isActiveHref('/home/settings/profile', '/home/settings')).toBe(true);
	});

	it('does not match a sibling that merely shares a prefix', () => {
		expect(isActiveHref('/home/projects-archive', '/home/projects')).toBe(false);
	});

	it('does not match unrelated paths', () => {
		expect(isActiveHref('/login', '/home/projects')).toBe(false);
	});
});

describe('entryForPath', () => {
	it('resolves a known route to its entry', () => {
		expect(entryForPath('/home/instances').label).toBe('Instances');
	});

	it('resolves a deep route to its own entry over the parent', () => {
		expect(entryForPath('/home/settings/profile').label).toBe('Profile');
	});

	it('falls back to the parent entry for unlisted sub-routes', () => {
		expect(entryForPath('/home/settings/unknown').label).toBe('Settings');
	});

	it('prefers the longest matching href', () => {
		// '/home' is a prefix of every other entry; specificity must win.
		expect(entryForPath('/home/projects').label).toBe('Projects');
		expect(entryForPath('/home').label).toBe('Overview');
	});

	it('falls back to the neutral shell title for unknown paths', () => {
		const entry = entryForPath('/somewhere/else');
		expect(entry.label).toBe('BytePort');
		expect(entry.subtitle).toBe('');
		expect(entry.href).toBe('/somewhere/else');
	});

	it('covers every declared entry at least once', () => {
		const seen = new Set(NAV_ENTRIES.map((e) => entryForPath(e.href).href));
		expect(seen.size).toBe(NAV_ENTRIES.length);
	});
});
