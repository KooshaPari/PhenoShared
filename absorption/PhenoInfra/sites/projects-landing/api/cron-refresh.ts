// Vercel Function — invoked by the cron defined in vercel.json.
//
// Vercel cron requires a function endpoint, but it cannot itself trigger a redeploy.
// Pattern: this handler pings the project's Deploy Hook URL (configured via the
// VERCEL_DEPLOY_HOOK env var in the Vercel dashboard). The redeploy re-runs
// `prebuild` (scripts/fetch-repos.mjs) which writes a fresh data/repos.json,
// then `astro build`, which bakes the new data into the static output.
//
// Configure once in Vercel dashboard:
//   1. Settings -> Git -> Deploy Hooks -> Create Hook (name: "cron-refresh", branch: main)
//   2. Settings -> Environment Variables -> add VERCEL_DEPLOY_HOOK = <hook url>
//
// The cron schedule lives in vercel.json. Hobby tier includes daily crons.

export const config = { runtime: "edge" };

export default async function handler(): Promise<Response> {
  const hook = process.env.VERCEL_DEPLOY_HOOK;
  if (!hook) {
    return new Response(
      JSON.stringify({
        ok: false,
        error: "VERCEL_DEPLOY_HOOK env var not configured",
      }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }

  const res = await fetch(hook, { method: "POST" });
  const body = await res.text();
  return new Response(
    JSON.stringify({
      ok: res.ok,
      status: res.status,
      triggeredAt: new Date().toISOString(),
      hookResponse: body.slice(0, 500),
    }),
    {
      status: res.ok ? 200 : 502,
      headers: { "content-type": "application/json" },
    },
  );
}
