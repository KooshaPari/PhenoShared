/**
 * Outbound / inbound ports for auth (hexagonal).
 */

import type { TokenRequest, TokenResponse } from '../domain/token';
import type { JwtClaims } from '../domain/claims';

export type { TokenRequest, TokenResponse };

/** Issues and refreshes tokens (outbound to IdP). */
export interface TokenProvider {
  requestToken(req: TokenRequest): Promise<TokenResponse>;
  refreshToken?(refreshToken: string): Promise<TokenResponse>;
}

/** Persists tokens by key with TTL (outbound). */
export interface TokenStore {
  save(key: string, token: unknown, ttlSeconds: number): Promise<void>;
  get(key: string): Promise<unknown | null>;
  delete(key: string): Promise<void>;
}

/** Validates JWTs and claim shapes (outbound crypto / JWKS). */
export interface ClaimsValidationOptions {
  readonly requiredClaims?: string[];
  readonly expectedIssuer?: string;
  readonly expectedAudience?: string | string[];
}

export interface TokenVerifier {
  verify(token: string): Promise<JwtClaims>;
  validateClaims?(
    claims: JwtClaims,
    options: ClaimsValidationOptions
  ): Promise<boolean>;
}
