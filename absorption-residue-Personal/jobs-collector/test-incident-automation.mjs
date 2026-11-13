import test from 'node:test';
import assert from 'node:assert/strict';
import {INCIDENT_TITLE, previousArtifact, updateIncident} from '../collector/incident-automation.mjs';

const context = {repo: {owner: 'offline', repo: 'collector'}, runId: 300, serverUrl: 'https://github.com'};
const issue = (state = 'open', number = 42) => ({title: INCIDENT_TITLE, state, number, assignees: ['existing-owner']});
const report = (opens, status = 'degraded') => ({checked_at: '2026-10-14T18:00:00Z', status,
  problems: ['one board failed'], incident: {should_open_or_reopen: opens, reasons: ['two distinct runs'],
    latest_run_id: 'la-day-v1:2026-10-14', boards_failed: 1, boards_checked: 25, finalized_age_hours: 2}});

function client(issues = []) {
  const writes = [], reads = [];
  const github = {
    rest: {issues: {
      listForRepo: async () => {},
      update: async args => { writes.push(['update', args]); },
      create: async args => { writes.push(['create', args]); },
      createComment: async args => { writes.push(['comment', args]); },
    }},
    paginate: async (method, args) => { reads.push(args); return issues; },
  };
  return {github, writes, reads};
}

for (const status of ['healthy', 'degraded', 'unknown']) {
  for (const state of ['open', 'closed']) {
    test(`no opening condition leaves ${state} incident unchanged for ${status} health`, async () => {
      const c = client([issue(state)]);
      await updateIncident({github: c.github, context, report: report(false, status)});
      assert.deepEqual(c.writes, []);
      assert.deepEqual(c.reads, []);
    });
  }
}
test('missing opening decision does not write an incident', async () => {
  const c = client([issue()]);
  await updateIncident({github: c.github, context, report: {status: 'degraded'}});
  assert.deepEqual(c.writes, []);
});
test('qualified closed incident reopens once without changing owners or adding comments', async () => {
  const c = client([issue('closed')]);
  assert.equal(await updateIncident({github: c.github, context, report: report(true)}), 'reopened');
  assert.deepEqual(c.writes, [['update', {owner: 'offline', repo: 'collector', issue_number: 42, state: 'open'}]]);
});
test('qualified already-open incident produces no writes', async () => {
  const c = client([issue('closed', 70), issue('open')]);
  assert.equal(await updateIncident({github: c.github, context, report: report(true)}), 'already open');
  assert.deepEqual(c.writes, []);
});
test('qualified absent incident creates one issue with exact failed/checked counts', async () => {
  const c = client([{...issue(), pull_request: {}}]);
  await updateIncident({github: c.github, context, report: report(true)});
  assert.equal(c.writes.length, 1);
  assert.equal(c.writes[0][0], 'create');
  assert.equal(c.writes[0][1].title, INCIDENT_TITLE);
  assert.match(c.writes[0][1].body, /1 \/ 25/);
  assert.match(c.writes[0][1].body, /owner review/);
});

function artifactsClient(pages, artifacts = {}) {
  const calls = [];
  const listWorkflowRunArtifacts = async () => {};
  return {calls, github: {
    rest: {actions: {listWorkflowRunArtifacts,
      listWorkflowRuns: async args => {calls.push(args); return {data: {workflow_runs: pages[args.page - 1] || []}};}}},
    paginate: async (method, args) => artifacts[args.run_id] || [],
  }};
}
const artifact = id => ({name: 'collector-health-' + id, expired: false});
const workflowRun = (id, head_branch = 'main') => ({id, head_branch});

test('checkpoint selection excludes current and non-main runs, retaining failed-run evidence', async () => {
  const c = artifactsClient([[workflowRun(300), workflowRun(299, 'candidate'), workflowRun(298), workflowRun(297)]],
    {300: [artifact(300)], 299: [artifact(299)], 297: [artifact(297)]});
  assert.deepEqual(await previousArtifact({github: c.github, context}), {runId: 297, name: 'collector-health-297'});
  assert.equal(c.calls[0].branch, 'main');
  assert.equal(c.calls[0].status, 'completed');
  assert.equal(c.calls[0].workflow_id, 'job-health-monitor.yml');
});
test('first observation with no artifact is explicit', async () => {
  const c = artifactsClient([[]]);
  assert.equal(await previousArtifact({github: c.github, context}), null);
});
test('deleted/missing prior checkpoint cannot silently bootstrap a new clock', async () => {
  const c = artifactsClient([[workflowRun(298)]], {298: [{name: 'unrelated', expired: false}]});
  await assert.rejects(previousArtifact({github: c.github, context}), /lack a checkpoint/);
});
test('expired checkpoint and GitHub API failure cannot reset state', async () => {
  const c = artifactsClient([[workflowRun(298)]], {298: [{...artifact(298), expired: true}]});
  await assert.rejects(previousArtifact({github: c.github, context}), /expired/);
  c.github.rest.actions.listWorkflowRuns = async () => {throw new Error('unavailable');};
  await assert.rejects(previousArtifact({github: c.github, context}), /unavailable/);
});
test('bounded exhausted search cannot bootstrap a fresh completion clock', async () => {
  const full = Array.from({length: 100}, (_, i) => workflowRun(200 - i));
  const c = artifactsClient(Array(10).fill(full));
  await assert.rejects(previousArtifact({github: c.github, context}), /exhausted/);
  assert.equal(c.calls.length, 10);
});
