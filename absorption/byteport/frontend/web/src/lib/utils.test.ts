import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from './api';
import { cn, flyAndScale, populateLists } from './utils';

vi.mock('./api', () => ({
	apiFetch: vi.fn()
}));

const fetchMock = vi.mocked(apiFetch);

describe('flyAndScale', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	const stubStyle = (transform: string) => {
		vi.stubGlobal('getComputedStyle', () => ({ transform }));
	};

	it('returns the default timing configuration', () => {
		stubStyle('none');
		const config = flyAndScale({} as Element);
		expect(config.duration).toBe(150);
		expect(config.delay).toBe(0);
		expect(config.easing).toBeTypeOf('function');
	});

	it('emits translate3d and opacity for the animation end state', () => {
		stubStyle('none');
		const config = flyAndScale({} as Element);
		const css = config.css!(1, 0);
		expect(css).toContain('translate3d(0px, 0px, 0)');
		// Scale at t=1 is 1 within floating-point tolerance.
		expect(css).toMatch(/scale\(1(\.0+)?\)/);
		expect(css).toContain('opacity:1');
	});

	it('emits the offset start state at t=0', () => {
		stubStyle('none');
		const config = flyAndScale({} as Element);
		const css = config.css!(0, 0);
		// Defaults: y=-8, start=0.95. The z axis is emitted as a bare 0.
		expect(css).toContain('translate3d(0px, -8px, 0)');
		expect(css).toContain('scale(0.95)');
		expect(css).toContain('opacity:0');
	});

	it('honors custom parameters', () => {
		stubStyle('none');
		const config = flyAndScale({} as Element, {
			y: -4,
			x: 10,
			start: 0.5,
			duration: 50
		});
		expect(config.duration).toBe(50);
		const css = config.css!(0, 0);
		expect(css).toContain('translate3d(10px, -4px, 0)');
		expect(css).toContain('scale(0.5)');
	});

	it('preserves the element existing transform as a prefix', () => {
		stubStyle('matrix(1, 0, 0, 1, 5, 6)');
		const config = flyAndScale({} as Element);
		const css = config.css!(1, 0);
		expect(css).toContain('matrix(1, 0, 0, 1, 5, 6) translate3d');
	});
});

describe('cn', () => {
	it('joins truthy class names', () => {
		expect(cn('a', 'b')).toBe('a b');
	});

	it('skips falsy inputs', () => {
		expect(cn('a', false, undefined, null, '', 'b')).toBe('a b');
	});

	it('lets later Tailwind utilities win', () => {
		expect(cn('p-2', 'p-4')).toBe('p-4');
	});

	it('merges conditional objects', () => {
		expect(cn({ 'text-red-500': true, 'text-blue-500': false })).toBe('text-red-500');
	});

	it('returns an empty string for no inputs', () => {
		expect(cn()).toBe('');
	});
});

describe('populateLists', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.spyOn(console, 'log').mockImplementation(() => {});
	});

	it('fetches and returns the projects list', async () => {
		const projects = [{ UUID: 'p1', name: 'demo' }];
		fetchMock.mockResolvedValueOnce(projects as never);

		await expect(populateLists()).resolves.toEqual(projects);
		expect(fetchMock).toHaveBeenCalledWith('/projects');
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});

	it('propagates a failed fetch', async () => {
		fetchMock.mockRejectedValueOnce(new Error('backend down'));
		await expect(populateLists()).rejects.toThrow('backend down');
	});
});
