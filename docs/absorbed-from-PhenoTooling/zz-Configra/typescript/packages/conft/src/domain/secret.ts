/**
 * Secret wrapper for sensitive configuration values.
 *
 * Purpose:
 * - Prevent accidental leakage of secrets through logs, error messages,
 *   snapshots, JSON.stringify, util.inspect, or template literals.
 * - Provide a controlled, auditable `reveal()` boundary.
 *
 * Security notes:
 * - `toJSON()`, `toString()`, `Symbol.toPrimitive`, and the Node.js
 *   `util.inspect` custom symbol all return the redacted form.
 * - Equality (`===` / `==`) is intentionally NOT overridden — secrets
 *   should be compared by `reveal()` result inside a controlled scope.
 * - `peek()` returns a non-revealing fingerprint (length + type tag) so
 *   callers can assert "is this set?" without seeing the value.
 */

const REDACTED = '[REDACTED]';

/**
 * Fingerprint describing a secret without revealing it.
 */
export interface SecretFingerprint {
  /** True if a value was provided (false if null/undefined/empty). */
  present: boolean;
  /** Length of the underlying string representation (or 0 if not a string). */
  length: number;
  /** Structural kind of the underlying value. */
  kind: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'null' | 'undefined';
}

export class Secret<T = string> {
  readonly #value: T;

  constructor(value: T) {
    if (value === undefined) {
      throw new Error('Secret value cannot be undefined; use a wrapper or omit the key.');
    }
    this.#value = value;
  }

  /**
   * Reveal the underlying value. Callers should treat this as a privileged
   * boundary and avoid passing the result to log sinks, error messages, or
   * any user-visible rendering path.
   */
  reveal(): T {
    return this.#value;
  }

  /**
   * Return a non-revealing fingerprint describing the value.
   */
  peek(): SecretFingerprint {
    const v = this.#value;
    if (v === null) return { present: false, length: 0, kind: 'null' };
    const kind: SecretFingerprint['kind'] =
      typeof v === 'string'
        ? 'string'
        : typeof v === 'number'
          ? 'number'
          : typeof v === 'boolean'
            ? 'boolean'
            : Array.isArray(v)
              ? 'array'
              : typeof v === 'object'
                ? 'object'
                : 'undefined';
    const length = kind === 'string' ? (v as string).length : 0;
    return { present: true, length, kind };
  }

  /**
   * Force the redacted form for any serializer that uses `toJSON()`
   * (JSON.stringify, Express res.json, error serialization, etc.).
   */
  toJSON(): string {
    return REDACTED;
  }

  /**
   * Force the redacted form for template literals and string concatenation.
   */
  toString(): string {
    return REDACTED;
  }

  /**
   * Force the redacted form for any implicit coercion path
   * (e.g. `${secret}`, `+secret`, `secret == "..."`).
   */
  [Symbol.toPrimitive](): string {
    return REDACTED;
  }

  /**
   * Custom inspection for Node.js `util.inspect`, `console.log`, and the
   * Vitest pretty-reporter.
   */
  [Symbol.for('nodejs.util.inspect.custom')](): string {
    return `Secret ${REDACTED}`;
  }
}

/**
 * Wrap a value in a Secret iff it is not already one.
 *
 * This lets adapters treat secretness as data (a Set of keys, a config flag,
 * a naming convention) without coupling the Secret wrapper to the adapter.
 */
export function asSecret<T>(value: T): Secret<T> {
  return value instanceof Secret ? value : new Secret<T>(value);
}

/**
 * Test whether a value is a Secret wrapper.
 */
export function isSecret(value: unknown): value is Secret<unknown> {
  return value instanceof Secret;
}