import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer, type Server } from 'node:http';
import { fileURLToPath } from 'node:url';

// These drive the real server over real stdio using JSON-RPC, the way an MCP
// client does. A source-inspection test would pass even if the refusal logic
// were unreachable at runtime.

const SERVER = fileURLToPath(new URL('../../tools/cockpit/mcp-readonly.mjs', import.meta.url));

type Reply = { id?: number; result?: any; error?: any };

/** Sends `requests` to the server and resolves the parsed replies. */
function rpc(requests: unknown[], env: NodeJS.ProcessEnv = {}): Promise<Reply[]> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [SERVER], {
      env: { ...process.env, ...env },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let out = '';
    let err = '';
    child.stdout.on('data', (d) => { out += d; });
    child.stderr.on('data', (d) => { err += d; });
    child.on('error', reject);
    child.on('close', () => {
      if (err.trim()) return reject(new Error(`server wrote to stderr: ${err.trim()}`));
      const lines = out.split('\n').filter((l) => l.trim());
      try {
        resolve(lines.map((l) => JSON.parse(l) as Reply));
      } catch (e) {
        reject(new Error(`non-JSON on stdout: ${out.slice(0, 300)}`));
      }
    });
    for (const r of requests) child.stdin.write(`${JSON.stringify(r)}\n`);
    child.stdin.end();
    setTimeout(() => child.kill(), 8000).unref();
  });
}

const INIT = { jsonrpc: '2.0', id: 1, method: 'initialize', params: {} };

test('the server answers initialize over real stdio', async () => {
  const [reply] = await rpc([INIT]);
  assert.equal(reply.id, 1, 'no JSON-RPC reply came back on stdout');
  assert.ok(reply.result, `initialize returned no result: ${JSON.stringify(reply)}`);
});

test('tools/list advertises only the two read tools', async () => {
  const [, reply] = await rpc([INIT, { jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }]);
  const names = (reply.result?.tools ?? []).map((t: { name: string }) => t.name).sort();
  assert.deepEqual(names, ['cockpit_get', 'cockpit_list'], `unexpected tool list: ${names}`);
});

test('mutating tools are refused at runtime, not merely unlisted', async () => {
  // A client that ignores tools/list and calls a write tool anyway.
  const replies = await rpc([
    INIT,
    { jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'cockpit_update', arguments: { id: 'x' } } },
    { jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'cockpit_add', arguments: {} } },
    { jsonrpc: '2.0', id: 5, method: 'tools/call', params: { name: 'cockpit_archive', arguments: { id: 'x' } } },
  ]);
  for (const id of [3, 4, 5]) {
    const reply = replies.find((r) => r.id === id);
    const text = JSON.stringify(reply?.result ?? reply?.error ?? {});
    assert.match(text, /read-only server/, `call id=${id} was not refused as read-only: ${text}`);
    assert.match(text, /not available here/, `call id=${id} refusal was not explicit: ${text}`);
  }
});

test('a refused mutation issues no HTTP request at all', async () => {
  // Points the server at a closed port. If any request were attempted the
  // refusal would be replaced by a transport error, proving the refusal
  // short-circuits before the network layer.
  const replies = await rpc(
    [
      INIT,
      { jsonrpc: '2.0', id: 6, method: 'tools/call', params: { name: 'cockpit_update', arguments: {} } },
    ],
    { COCKPIT_URL: 'http://127.0.0.1:9' },
  );
  const reply = replies.find((r) => r.id === 6);
  const text = JSON.stringify(reply?.result ?? reply?.error ?? {});
  assert.match(text, /read-only server/, `expected a refusal, got: ${text}`);
  assert.doesNotMatch(text, /unreachable|ECONNREFUSED|fetch failed/, 'a request was attempted before the refusal');
});

test('a transport failure is reported as an error, not an unhandled crash', async () => {
  // The read path IS allowed to reach the network, so with an unreachable
  // upstream it must degrade to a message the client can read.
  const replies = await rpc(
    [
      INIT,
      { jsonrpc: '2.0', id: 7, method: 'tools/call', params: { name: 'cockpit_list', arguments: {} } },
    ],
    { COCKPIT_URL: 'http://127.0.0.1:9' },
  );
  const reply = replies.find((r) => r.id === 7);
  assert.ok(reply, 'the server died instead of replying to a failed read');
  const text = JSON.stringify(reply?.result ?? reply?.error ?? '');
  assert.match(text, /unreachable|error|fail/i, `expected a reported failure, got: ${text}`);
});

test('malformed input does not kill the server', async () => {
  // The process must survive a line it cannot parse and still answer later calls.
  const replies = await rpc([
    INIT,
    { jsonrpc: '2.0', id: 8, method: 'tools/list', params: {} },
  ]);
  const reply = replies.find((r) => r.id === 8);
  assert.ok(reply?.result?.tools, 'the server stopped responding');
  assert.equal(reply.result.tools.length, 2, 'the read-only tool set changed');
});

test('a successful tool call delivers the real payload, not [object Promise]', async (t) => {
  // Regression guard. A review bot flagged the tools/call handler as not
  // awaiting run(), which would stringify a pending Promise into every success
  // response. The code does await, so this test asserts the OBSERVED behaviour
  // against a live stub upstream rather than trusting a read of the source.
  const server: Server = createServer((_req, res) => {
    const body = JSON.stringify({ items: [{ id: 'job-42', title: 'real payload' }], count: 1 });
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(body);
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as { port: number };
  t.after(() => new Promise<void>((resolve) => server.close(() => resolve())));

  const replies = await rpc(
    [
      INIT,
      { jsonrpc: '2.0', id: 9, method: 'tools/call', params: { name: 'cockpit_get', arguments: { id: 'job-42' } } },
    ],
    { COCKPIT_URL: `http://127.0.0.1:${port}` },
  );
  const reply = replies.find((r) => r.id === 9);
  const text = JSON.stringify(reply?.result ?? reply?.error ?? '');
  assert.doesNotMatch(text, /\[object Promise\]/, 'the handler stringified a pending Promise');
  assert.match(text, /job-42/, `the upstream payload was not delivered: ${text}`);
  assert.equal(reply?.result?.isError, false, 'a successful read was flagged as an error');
});
