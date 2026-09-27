import { WorkOS } from '@workos-inc/node';

const workos = new WorkOS(process.env.WORKOS_API_KEY!);
const clientId = process.env.WORKOS_CLIENT_ID!;

export const PUBLIC_PATHS = ['/', '/about', '/pricing', '/docs', '/favicon.ico', '/auth/callback'];

export async function getSession(request: Request): Promise<{user: any} | null> {
  const cookie = request.headers.get('cookie') || '';
  const token = cookie.split(';').find((c: string) => c.trim().startsWith('wos-session='))?.split('=')[1];
  if (!token) return null;
  try {
    const { user } = await workos.userManagement.getJwksUrl(token as any);
    return { user };
  } catch { return null; }
}

export function getAuthUrl(redirectUri: string): string {
  return workos.userManagement.getAuthorizationUrl({ provider: 'authkit', redirectUri, clientId });
}

export async function handleCallback(code: string, redirectUri: string) {
  return workos.userManagement.authenticateWithCode({ code, clientId, session: { sealSession: true, cookiePassword: process.env.WORKOS_COOKIE_PASSWORD! } });
}
