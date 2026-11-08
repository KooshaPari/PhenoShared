/**
 * Placeholder JWT verification adapter — swap for jose/jwks in production.
 */

import type { JwtClaims } from '../domain/claims';
import type { ClaimsValidationOptions, TokenVerifier } from '../ports';
import { AuthErrors } from '../domain/errors';

export class PlaceholderJwtVerifier implements TokenVerifier {
  async verify(_token: string): Promise<JwtClaims> {
    throw AuthErrors.INVALID_TOKEN();
  }

  async validateClaims(
    claims: JwtClaims,
    options: ClaimsValidationOptions
  ): Promise<boolean> {
    const required = options.requiredClaims ?? [];
    for (const key of required) {
      if (claims[key] === undefined && claims[key as keyof JwtClaims] === undefined) {
        throw AuthErrors.MISSING_CLAIM(key);
      }
    }
    if (options.expectedIssuer && claims.iss !== options.expectedIssuer) {
      throw AuthErrors.INVALID_CLAIM('iss', options.expectedIssuer);
    }
    const aud = claims.aud;
    if (options.expectedAudience !== undefined) {
      const expected = options.expectedAudience;
      const ok = Array.isArray(aud)
        ? aud.some((a) =>
            Array.isArray(expected) ? expected.includes(a) : a === expected
          )
        : aud === expected || (Array.isArray(expected) && expected.includes(aud as string));
      if (!ok) {
        throw AuthErrors.INVALID_CLAIM('aud', String(expected));
      }
    }
    return true;
  }
}
