/* AgilePlus PWA service worker
 * Same strategy as Tracera SW — see Tracera/workspace/sw.js for full doc.
 * Bump CACHE_VERSION on breaking schema or asset graph changes.
 */
const CACHE_VERSION = 'agileplus-pwa-v0.1.0-r4-consolidate';
const CORE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/agileplus-icon-192.png',
  '/icons/agileplus-icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_VERSION);
    try { await cache.addAll(CORE_ASSETS); } catch (_) { /* optional assets */ }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // AgilePlus exposes many sub-app routes; only the auth-gated ones stay network-only.
  if (url.pathname.startsWith('/v1/') || url.pathname.startsWith('/mcp/') || url.pathname.startsWith('/api/')) return;

  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const cache = await caches.open(CACHE_VERSION);
        cache.put(req, fresh.clone());
        return fresh;
      } catch (_) {
        const cache = await caches.open(CACHE_VERSION);
        return (await cache.match(req)) || (await cache.match('/index.html')) || Response.error();
      }
    })());
    return;
  }

  if (url.pathname.startsWith('/assets/') || /\.(js|mjs|css|woff2?|ttf|svg|png|jpg|webp|avif)$/.test(url.pathname)) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_VERSION);
      const cached = await cache.match(req);
      const network = fetch(req).then((res) => { cache.put(req, res.clone()); return res; }).catch(() => cached);
      return cached || network;
    })());
    return;
  }

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_VERSION);
    const cached = await cache.match(req);
    if (cached) return cached;
    try {
      const res = await fetch(req);
      if (res.ok) cache.put(req, res.clone());
      return res;
    } catch (_) { return Response.error(); }
  })());
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))));
  }
});
