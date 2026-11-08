/**
 * JWT / OIDC-style claims (domain).
 */

export interface JwtClaims {
  readonly sub?: string;
  readonly iss?: string;
  readonly aud?: string | string[];
  readonly exp?: number;
  readonly iat?: number;
  readonly [claim: string]: unknown;
}
