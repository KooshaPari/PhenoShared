/**
 * Domain models for authentication.
 *
 * xDD Methodologies:
 * - DDD: Domain-driven design with bounded context
 * - PoLA: Descriptive error messages
 */

export class AuthError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 401
  ) {
    super(message);
    this.name = 'AuthError';
  }
}

// Domain errors following PoLA (Principle of Least Astonishment)
export const AuthErrors = {
  INVALID_TOKEN: () =>
    new AuthError('Token is invalid or malformed', 'INVALID_TOKEN', 401),

  TOKEN_EXPIRED: () =>
    new AuthError('Token has expired', 'TOKEN_EXPIRED', 401),

  TOKEN_NOT_YET_VALID: () =>
    new AuthError('Token is not yet valid', 'TOKEN_NOT_YET_VALID', 401),

  INVALID_SIGNATURE: () =>
    new AuthError('Token signature verification failed', 'INVALID_SIGNATURE', 401),

  MISSING_CLAIM: (claim: string) =>
    new AuthError(`Token missing required claim: ${claim}`, 'MISSING_CLAIM', 401),

  INVALID_CLAIM: (claim: string, expected: string) =>
    new AuthError(`Claim ${claim} must be ${expected}`, 'INVALID_CLAIM', 401),

  INSUFFICIENT_SCOPE: (required: string[], actual: string[]) =>
    new AuthError(
      `Insufficient scope. Required: ${required.join(', ')}, Actual: ${actual.join(', ')}`,
      'INSUFFICIENT_SCOPE',
      403
    ),

  PROVIDER_ERROR: (message: string) =>
    new AuthError(`Auth provider error: ${message}`, 'PROVIDER_ERROR', 502),
} as const;
