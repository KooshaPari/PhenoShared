// Serves collector output from KV under /dispensary/data/*; falls through to static files on a miss.
export async function onRequest(ctx) {
  const key = [].concat(ctx.params.path).join('/');
  if (ctx.env.DISP) {
    const v = await ctx.env.DISP.get(key);
    if (v !== null) return new Response(v, { headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
  }
  return ctx.next();
}
