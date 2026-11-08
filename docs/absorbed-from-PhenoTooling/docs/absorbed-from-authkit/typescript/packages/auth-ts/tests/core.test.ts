import { describe, expect, it } from 'vitest';
import {
  AuthError,
  AuthErrors,
  MemoryTokenStore,
  PlaceholderJwtVerifier,
  TokenError,
  asToken,
} from '../src';

describe('TokenError', () => {
  it('creates typed invalid request errors', () => {
    const error = TokenError.invalidRequest('bad request', { field: 'grantType' });

    expect(error).toBeInstanceOf(TokenError);
    expect(error.message).toBe('bad request');
    expect(error.code).toBe('invalid_request');
    expect(error.statusCode).toBe(400);
    expect(error.context).toEqual({ field: 'grantType' });
  });

  it('creates typed invalid client errors', () => {
    const error = TokenError.invalidClient('bad client');

    expect(error.code).toBe('invalid_client');
    expect(error.statusCode).toBe(401);
  });

  it('creates the remaining OAuth error variants', () => {
    expect(TokenError.invalidGrant('bad grant').code).toBe('invalid_grant');
    expect(TokenError.unauthorizedClient('no access').statusCode).toBe(403);
    expect(TokenError.unsupportedGrantType('unsupported').code).toBe(
      'unsupported_grant_type'
    );
  });
});

describe('AuthErrors', () => {
  it('creates descriptive auth errors', () => {
    const error = AuthErrors.MISSING_CLAIM('sub');

    expect(error).toBeInstanceOf(AuthError);
    expect(error.code).toBe('MISSING_CLAIM');
    expect(error.statusCode).toBe(401);
    expect(error.message).toContain('sub');
  });

  it('formats insufficient scope errors', () => {
    const error = AuthErrors.INSUFFICIENT_SCOPE(['read', 'write'], ['read']);

    expect(error.code).toBe('INSUFFICIENT_SCOPE');
    expect(error.statusCode).toBe(403);
    expect(error.message).toContain('Required: read, write');
    expect(error.message).toContain('Actual: read');
  });

  it('creates the remaining standard auth errors', () => {
    expect(AuthErrors.INVALID_TOKEN().code).toBe('INVALID_TOKEN');
    expect(AuthErrors.TOKEN_EXPIRED().code).toBe('TOKEN_EXPIRED');
    expect(AuthErrors.TOKEN_NOT_YET_VALID().code).toBe('TOKEN_NOT_YET_VALID');
    expect(AuthErrors.INVALID_SIGNATURE().code).toBe('INVALID_SIGNATURE');
    expect(AuthErrors.PROVIDER_ERROR('boom').statusCode).toBe(502);
  });
});

describe('MemoryTokenStore', () => {
  it('stores, retrieves, and deletes tokens', async () => {
    const store = new MemoryTokenStore();
    const token = { accessToken: 'abc', tokenType: 'Bearer', expiresAt: Date.now() + 60_000 };

    await store.save('session-1', token, 60);

    expect(await store.get('session-1')).toEqual(token);

    await store.delete('session-1');

    expect(await store.get('session-1')).toBeNull();
  });

  it('expires tokens after ttl', async () => {
    const store = new MemoryTokenStore();

    await store.save('session-2', { accessToken: 'expired', tokenType: 'Bearer' }, -1);

    expect(await store.get('session-2')).toBeNull();
  });
});

describe('asToken', () => {
  it('narrows valid token shapes', () => {
    const token = { accessToken: 'abc', tokenType: 'Bearer', expiresAt: 123 };

    expect(asToken(token)).toEqual(token);
  });

  it('rejects invalid token shapes', () => {
    expect(asToken({ accessToken: 'abc' })).toBeNull();
    expect(asToken(null)).toBeNull();
  });
});

describe('PlaceholderJwtVerifier', () => {
  it('always rejects verification', async () => {
    const verifier = new PlaceholderJwtVerifier();

    await expect(verifier.verify('token')).rejects.toMatchObject({
      code: 'INVALID_TOKEN',
      statusCode: 401,
    });
  });

  it('validates required claims, issuer, and audience', async () => {
    const verifier = new PlaceholderJwtVerifier();

    await expect(
      verifier.validateClaims(
        {
          sub: 'user-1',
          iss: 'https://issuer.example.com',
          aud: ['client-a', 'client-b'],
        },
        {
          requiredClaims: ['sub', 'iss', 'aud'],
          expectedIssuer: 'https://issuer.example.com',
          expectedAudience: 'client-b',
        }
      )
    ).resolves.toBe(true);
  });

  it('accepts expected audience arrays', async () => {
    const verifier = new PlaceholderJwtVerifier();

    await expect(
      verifier.validateClaims(
        {
          sub: 'user-1',
          iss: 'https://issuer.example.com',
          aud: 'client-b',
        },
        {
          expectedAudience: ['client-a', 'client-b'],
        }
      )
    ).resolves.toBe(true);
  });

  it('rejects missing and mismatched claims', async () => {
    const verifier = new PlaceholderJwtVerifier();

    await expect(
      verifier.validateClaims(
        { iss: 'https://issuer.example.com', aud: 'client-a' },
        { requiredClaims: ['sub'] }
      )
    ).rejects.toMatchObject({
      code: 'MISSING_CLAIM',
    });

    await expect(
      verifier.validateClaims(
        { sub: 'user-1', iss: 'https://issuer.example.com', aud: 'client-a' },
        { expectedIssuer: 'https://other.example.com' }
      )
    ).rejects.toMatchObject({
      code: 'INVALID_CLAIM',
    });
  });
});
