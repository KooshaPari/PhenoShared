import { defineMiddleware } from 'astro:middleware';

const PUBLIC_PATHS = ['/', '/auth/callback', '/favicon.ico'];

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith('/assets'))) return next();
  const session = context.cookies.get('wos-session');
  if (!session) {
    const authUrl = `https://api.workos.com/user_management/authorize?response_type=code&client_id=${import.meta.env.WORKOS_CLIENT_ID}&redirect_uri=${encodeURIComponent(context.url.origin + '/auth/callback')}&provider=authkit`;
    return context.redirect(authUrl);
  }
  return next();
});
