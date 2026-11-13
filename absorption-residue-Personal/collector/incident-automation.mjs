// Purely injected GitHub client: tests never contact GitHub or the live Worker.
export const INCIDENT_TITLE = 'Job collector: live health incident';

export async function updateIncident({github, context, report}) {
  if (report.incident?.should_open_or_reopen !== true) return 'no opening condition';
  const {owner, repo} = context.repo;
  const issues = await github.paginate(github.rest.issues.listForRepo, {owner, repo, state: 'all', per_page: 100});
  const matches = issues.filter(issue => issue.title === INCIDENT_TITLE && !issue.pull_request);
  const prior = matches.find(issue => issue.state === 'open') || matches.sort((a, b) => b.number - a.number)[0];
  if (prior?.state === 'open') return 'already open';
  if (prior) {
    await github.rest.issues.update({owner, repo, issue_number: prior.number, state: 'open'});
    return 'reopened';
  }
  const body = [
    'Read-only monitoring met the collector incident opening policy.', '',
    '**Detected:** ' + report.checked_at,
    '**Opening conditions:** ' + report.incident.reasons.join('; '),
    '**Problems:** ' + report.problems.join('; '),
    '**Finalized run:** ' + report.incident.latest_run_id,
    '**Failed / checked boards:** ' + report.incident.boards_failed + ' / ' + report.incident.boards_checked,
    '**Last finalized-run age (hours):** ' + report.incident.finalized_age_hours, '',
    'Collection health remains strict. The discovery queue is not a verified application shortlist.',
    'Recovery resets the failure streak. Closing this incident requires owner review.',
    'Run: ' + context.serverUrl + '/' + owner + '/' + repo + '/actions/runs/' + context.runId,
  ].join('\n');
  await github.rest.issues.create({owner, repo, title: INCIDENT_TITLE, body});
  return 'created';
}

export async function previousArtifact({github, context}) {
  const {owner, repo} = context.repo;
  let sawPriorRun = false;
  // Search completed main runs, including failed health checks. A broken latest
  // run with no report must not wipe the previous completion/absence clock.
  for (let page = 1; page <= 10; page++) {
    const {data} = await github.rest.actions.listWorkflowRuns({owner, repo,
      workflow_id: 'job-health-monitor.yml', branch: 'main', status: 'completed', per_page: 100, page});
    for (const run of data.workflow_runs) {
      if (String(run.id) === String(context.runId) || run.head_branch !== 'main') continue;
      sawPriorRun = true;
      const artifacts = await github.paginate(github.rest.actions.listWorkflowRunArtifacts,
        {owner, repo, run_id: run.id, per_page: 100});
      const matching = artifacts.find(a => a.name === 'collector-health-' + run.id);
      if (matching?.expired) throw new Error('Previous health checkpoint expired; restore evidence before incident writes');
      if (matching) return {runId: run.id, name: matching.name};
    }
    if (data.workflow_runs.length < 100) {
      if (sawPriorRun) throw new Error('Previous monitor runs lack a checkpoint; restore evidence before incident writes');
      return null;
    }
  }
  throw new Error('Checkpoint search exhausted; refusing to reset monitor state');
}
