import test from 'node:test';
import assert from 'node:assert/strict';
import { email, recipient, agents } from './worker.mjs';
const env = { CF_ACCESS_CLIENT_ID:'synthetic-id', CF_ACCESS_CLIENT_SECRET:'synthetic-secret',
  INTAKE_TOKEN:'synthetic-intake', RELAY_URL:'https://example.com/v1/intake' };
function message(to='dot@example.com', messageId=null) {
  const idHeader = messageId ? 'Message-ID: '+messageId+'\r\n' : '';
  return { to, from:'010001a1c9095d74-deadbeef-000000@example.com', rawSize:100,
    raw:new Blob(['From: user@example.com\r\nTo: '+to+'\r\n'+idHeader+'Subject: bridge test\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nHello bridge.']).stream(),
    setReject(reason) { this.rejected=reason; } };
}
for (const agent of agents) test('routes '+agent, () => assert.equal(recipient(agent+'@example.com'),agent));
test('rejects foreign, lookalike and unknown recipients', () => {
  for (const addr of ['user@example.com','dot@example.com.evil','unknown@example.com']) assert.equal(recipient(addr),null);
});
test('MIME parsed and authenticated POST acknowledged', async () => {
  let called=false;
  await email(message(),env,async(url,request) => {
    called=true; assert.equal(url,env.RELAY_URL); assert.equal(request.redirect,'manual');
    assert.equal(request.headers['CF-Access-Client-Secret'],env.CF_ACCESS_CLIENT_SECRET);
    assert.equal(request.headers.Authorization,'Bearer synthetic-intake');
    const body=JSON.parse(request.body);assert.deepEqual(body.to,['dot@example.com']);
    assert.equal(body.from,'user@example.com','header From, not the VERP envelope sender');
    assert.match(body.text,/Hello bridge/);assert.equal(body.subject,'bridge test');
    return Response.json({ids:['proof-id']});
  });assert.equal(called,true);
});
test('stable message identity is forwarded so a retry stores once', async () => {
  let seen=null;
  await email(message('instinct@example.com','<user@example.com>'),env,async(url,request)=>{
    seen={body:JSON.parse(request.body),headers:request.headers};
    return Response.json({ids:['proof-id']});
  });
  assert.equal(seen.body.message_id,'<user@example.com>');
  assert.equal(seen.headers['X-Message-Id'],'<user@example.com>');
});
test('no message identity means no identity field', async () => {
  let seen=null;
  await email(message('instinct@example.com'),env,async(url,request)=>{
    seen={body:JSON.parse(request.body),headers:request.headers};
    return Response.json({ids:['proof-id']});
  });
  assert.equal(seen.body.message_id,undefined);
  assert.equal(seen.headers['X-Message-Id'],undefined);
});
test('failure and missing secrets never acknowledged',async()=>{
  await assert.rejects(email(message(),env,async()=>new Response('',{status:530})),/HTTP 530/);
  await assert.rejects(email(message(),env,async()=>Response.json({ids:[]})),/acknowledge/);
  await assert.rejects(email(message(),{...env,INTAKE_TOKEN:''}),/Missing bridge secret/);
});
test('Cloudflare Access redirect is reported, not silently swallowed',async()=>{
  await assert.rejects(
    email(message(),env,async()=>({type:'opaqueredirect',status:0,ok:false})),
    /redirected/);
  await assert.rejects(
    email(message(),env,async()=>new Response('',{status:302})),
    /redirected/);
});
test('a transient relay failure is retried with the same identity',async()=>{
  const seen=[];
  await email(message('dot@example.com','<user@example.com>'),env,async(url,request)=>{
    seen.push(request.headers['X-Message-Id']);
    return seen.length===1?new Response('',{status:500}):Response.json({ids:['proof-id']});
  });
  assert.equal(seen.length,2,'one retry after a 5xx');
  assert.deepEqual(seen,['<user@example.com>','<user@example.com>'],'same identity, so the relay dedupes');
});
test('a permanent relay error is not retried',async()=>{
  let calls=0;
  await assert.rejects(email(message('dot@example.com','<user@example.com>'),env,async()=>{
    calls+=1;return new Response('',{status:403});
  }),/HTTP 403/);
  assert.equal(calls,1,'a 403 does not become true by waiting');
});
test('without a message identity a failure is not retried',async()=>{
  let calls=0;
  await assert.rejects(email(message('dot@example.com'),env,async()=>{
    calls+=1;return new Response('',{status:503});
  }),/HTTP 503/);
  assert.equal(calls,1,'no dedupe key, so a repeat could store twice');
});
test('an Access redirect is not retried',async()=>{
  let calls=0;
  await assert.rejects(email(message('dot@example.com','<user@example.com>'),env,async()=>{
    calls+=1;return new Response('',{status:302});
  }),/redirected/);
  assert.equal(calls,1,'an Access misconfiguration is not transient');
});
test('unknown and oversized messages rejected before fetch',async()=>{
  const unknown=message('unknown@example.com');await email(unknown,env);assert.ok(unknown.rejected);
  const big=message();big.rawSize=2097153;await email(big,env);assert.ok(big.rejected);
});
