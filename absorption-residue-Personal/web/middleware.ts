// Vercel Routing Middleware: require a valid Cloudflare Access JWT on every request.
// The direct <project>.vercel.app production alias is publicly reachable even with
// Vercel Standard Protection (production is exempt), so the edge rejects any
// request that did not arrive through an Access-gated hostname with 401.
//
// Verifies Cf-Access-Jwt-Assertion against the Access team JWKS
// (https://floral-moon-c604.cloudflareaccess.com/cdn-cgi/access/certs),
// the team issuer, expiry, and a known Access application AUD.

const TEAM_DOMAIN = 'floral-moon-c604.cloudflareaccess.com';
const CERTS_URL = `https://${TEAM_DOMAIN}/cdn-cgi/access/certs`;
const ISSUER = `https://${TEAM_DOMAIN}`;

// Access application AUDs accepted by this deployment (all "Koosha only" policy):
//   pheno-studio-wildcard (*.pheno.studio), pheno-agileplus, pheno-tracera,
//   pheno-shop-wildcard (*.pheno.shop), pheno-agileplus-space (agileplus.phenotype.space)
const TRUSTED_AUDS = [
  'cd5a353030d8379b9322508233a0dbeaaa6896103c6237fa54cdb907e2b5852a',
  '019aa5a73cbde4c84fcac461f8ff1c7f0d0489e65df767d7a4f91759855f8a76',
  '1502c30a5519bf4a7dbd7ad0148e5d2b9d951aa8371d64ff4858bdc468396b27',
  'ac34527585f7e7c796b8fade8ea011f998ed019bc90bc227949324181224efc3',
  'a47099890d858f9ac98e4388b9c3ec007d78b6404c40348717f111018065e6a8',
];

let keysPromise: Promise<Map<string, CryptoKey>> | null = null;
let keysFetchedAt = 0;

async function getKeys(): Promise<Map<string, CryptoKey>> {
  if (!keysPromise || Date.now() - keysFetchedAt > 3600_000) {
    keysFetchedAt = Date.now();
    keysPromise = (async () => {
      const res = await fetch(CERTS_URL);
      if (!res.ok) throw new Error(`JWKS fetch failed: ${res.status}`);
      const { keys } = (await res.json()) as { keys: Array<JsonWebKey & { kid?: string }> };
      const map = new Map<string, CryptoKey>();
      for (const k of keys) {
        if (k.kty !== 'RSA' || !k.kid) continue;
        map.set(
          k.kid,
          await crypto.subtle.importKey(
            'jwk',
            k,
            { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
            false,
            ['verify'],
          ),
        );
      }
      return map;
    })();
    keysPromise.catch(() => {
      keysPromise = null;
    });
  }
  return keysPromise;
}

function b64url(segment: string): Uint8Array<ArrayBuffer> {
  const b64 = segment.replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(b64);
  const bytes = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

async function hasValidAccessJwt(jwt: string): Promise<boolean> {
  const parts = jwt.split('.');
  if (parts.length !== 3) return false;
  let header: { alg?: string; kid?: string };
  let payload: { iss?: string; aud?: string | string[]; exp?: number };
  try {
    header = JSON.parse(new TextDecoder().decode(b64url(parts[0])));
    payload = JSON.parse(new TextDecoder().decode(b64url(parts[1])));
  } catch {
    return false;
  }
  // JSON.parse can yield null or a scalar (e.g. a crafted "null" segment); without
  // this guard the property reads below would throw and surface a 500 instead of 401.
  if (!header || typeof header !== 'object' || !payload || typeof payload !== 'object') {
    return false;
  }
  if (header.alg !== 'RS256' || !header.kid) return false;
  if (payload.iss !== ISSUER) return false;
  const auds = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!auds.some((a) => a && TRUSTED_AUDS.includes(a))) return false;
  if (typeof payload.exp !== 'number' || payload.exp < Date.now() / 1000) return false;
  try {
    let keys = await getKeys();
    let key = keys.get(header.kid);
    if (!key && Date.now() - keysFetchedAt > 60_000) {
      // Unknown kid after a key rotation: drop the cached JWKS and refetch once
      // (guarded so a flood of junk kids cannot trigger a fetch storm).
      keysPromise = null;
      keys = await getKeys();
      key = keys.get(header.kid);
    }
    if (!key) return false;
    const signed = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
    return await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64url(parts[2]), signed);
  } catch {
    return false;
  }
}

export default async function middleware(request: Request): Promise<Response | undefined> {
  // Gate production deployments only. The public <project>.vercel.app production
  // alias is exempt from Vercel Authentication, while preview deployments already
  // require Vercel Authentication and cannot carry a Cloudflare Access JWT, so
  // gating previews would make every preview URL unusable.
  if (process.env.VERCEL_ENV !== 'production') return undefined;
  const jwt = request.headers.get('cf-access-jwt-assertion');
  if (jwt && (await hasValidAccessJwt(jwt))) return undefined; // continue to the app
  return new Response('Unauthorized', {
    status: 401,
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
}
