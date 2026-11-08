/**
 * Tests for the Secret wrapper.
 *
 * Covers the redaction guarantees called out in L18 of the v37 audit:
 * - JSON.stringify, toString, template literals, util.inspect, Symbol.toPrimitive
 *   must all return the redacted form.
 * - reveal() returns the original value.
 * - peek() returns a fingerprint without revealing the value.
 */

import { describe, expect, it } from 'vitest';
import { inspect } from 'util';
import { asSecret, isSecret, Secret } from './secret';

describe('Secret wrapper', () => {
  it('reveals the underlying value only via reveal()', () => {
    const secret = new Secret('hunter2');
    expect(secret.reveal()).toBe('hunter2');
  });

  it('redacts on JSON.stringify', () => {
    const secret = new Secret('hunter2');
    expect(JSON.stringify({ token: secret })).toBe('{"token":"[REDACTED]"}');
  });

  it('redacts on toString()', () => {
    const secret = new Secret('hunter2');
    expect(secret.toString()).toBe('[REDACTED]');
  });

  it('redacts on template-literal interpolation', () => {
    const secret = new Secret('hunter2');
    expect(`token=${secret}`).toBe('token=[REDACTED]');
  });

  it('redacts on Symbol.toPrimitive coercion', () => {
    const secret = new Secret('hunter2');
    expect(`${secret}`).toBe('[REDACTED]');
    expect(String(secret)).toBe('[REDACTED]');
    // Concatenation coerces via Symbol.toPrimitive (hint=string).
    expect('value: ' + secret).toBe('value: [REDACTED]');
  });

  it('redacts in Node.js util.inspect output', () => {
    const secret = new Secret('hunter2');
    // Node.js inspect renders the string returned from the custom symbol
    // without quoting (since it's already a literal); we assert the
    // redaction marker is present and the raw value is not.
    const rendered = inspect(secret);
    expect(rendered).toContain('[REDACTED]');
    expect(rendered).not.toContain('hunter2');
    expect(rendered).toMatch(/^Secret /);
  });

  it('redacts when nested inside an array', () => {
    const arr = [new Secret('a'), new Secret('b')];
    expect(JSON.stringify(arr)).toBe('["[REDACTED]","[REDACTED]"]');
  });

  it('peek() returns a non-revealing fingerprint', () => {
    const secret = new Secret('hunter2');
    expect(secret.peek()).toEqual({ present: true, length: 7, kind: 'string' });
  });

  it('peek() classifies non-string kinds', () => {
    expect(new Secret(42).peek().kind).toBe('number');
    expect(new Secret(true).peek().kind).toBe('boolean');
    expect(new Secret(['x']).peek().kind).toBe('array');
    expect(new Secret({ a: 1 }).peek().kind).toBe('object');
  });

  it('peek() reports not-present for null/undefined', () => {
    expect(new Secret(null).peek().present).toBe(false);
    expect(new Secret(null).peek().kind).toBe('null');
  });

  it('isSecret detects the wrapper', () => {
    expect(isSecret(new Secret('x'))).toBe(true);
    expect(isSecret('x')).toBe(false);
    expect(isSecret(null)).toBe(false);
  });

  it('asSecret wraps only non-secret values', () => {
    const inner = new Secret('inner');
    const wrapped = asSecret(inner);
    expect(wrapped).toBe(inner); // identity for already-wrapped values
    const fresh = asSecret('outer');
    expect(isSecret(fresh)).toBe(true);
    expect(fresh.reveal()).toBe('outer');
  });

  it('rejects undefined values at construction time', () => {
    // The constructor accepts a generic <T>; passing `undefined` is a
    // type-system error AND a runtime guard. We intentionally bypass
    // the type system here to verify the runtime guard fires.
    expect(() => new Secret<undefined>(undefined)).toThrow(/cannot be undefined/);
  });
});