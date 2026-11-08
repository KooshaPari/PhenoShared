/**
 * Token domain models.
 *
 * Following hexagonal architecture principles.
 */

export interface Token {
  readonly accessToken: string;
  readonly tokenType: string;
  readonly expiresAt: number;
  readonly refreshToken?: string;
  readonly scope?: string;
}

export interface TokenRequest {
  readonly grantType: 'client_credentials' | 'password' | 'refresh_token' | 'authorization_code';
  readonly clientId: string;
  readonly clientSecret?: string;
  readonly username?: string;
  readonly password?: string;
  readonly code?: string;
  readonly redirectUri?: string;
  readonly refreshToken?: string;
}

export interface TokenResponse {
  readonly accessToken: string;
  readonly tokenType: string;
  readonly expiresIn: number;
  readonly refreshToken?: string;
  readonly scope?: string;
  readonly idToken?: string;
}

export class TokenError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number,
    public readonly context?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'TokenError';
  }

  static invalidRequest(message: string, context?: Record<string, unknown>) {
    return new TokenError(message, 'invalid_request', 400, context);
  }

  static invalidClient(message: string, context?: Record<string, unknown>) {
    return new TokenError(message, 'invalid_client', 401, context);
  }

  static invalidGrant(message: string, context?: Record<string, unknown>) {
    return new TokenError(message, 'invalid_grant', 400, context);
  }

  static unauthorizedClient(message: string, context?: Record<string, unknown>) {
    return new TokenError(message, 'unauthorized_client', 403, context);
  }

  static unsupportedGrantType(message: string, context?: Record<string, unknown>) {
    return new TokenError(message, 'unsupported_grant_type', 400, context);
  }
}
