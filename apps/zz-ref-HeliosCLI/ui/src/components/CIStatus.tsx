import { useCIRuns } from "../hooks/useHelios";
import { useConfig } from "../hooks/useHelios";

interface CIStatusPanelProps {
  fullName: string | null;
  onBack: () => void;
}

function parseRepo(fullName: string): { owner: string; name: string } {
  const [owner, ...rest] = fullName.split("/");
  return { owner, name: rest.join("/") };
}

function statusIcon(conclusion: string | null, status: string): string {
  if (conclusion === "success") return "\u2705";
  if (conclusion === "failure") return "\u274C";
  if (conclusion === "cancelled") return "\u26D4";
  if (conclusion === "skipped") return "\u23ED";
  if (status === "in_progress") return "\u23F3";
  if (status === "queued") return "\u23F3";
  return "\u2753";
}

function formatDuration(secs: number | null): string {
  if (secs === null) return "--";
  const minutes = Math.floor(secs / 60);
  const seconds = secs % 60;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function runDuration(run: { run_started_at: string | null; updated_at: string }): string {
  if (!run.run_started_at) return "--";
  const start = new Date(run.run_started_at).getTime();
  const end = new Date(run.updated_at).getTime();
  const secs = Math.floor((end - start) / 1000);
  return formatDuration(secs > 0 ? secs : null);
}

function shortSha(sha: string): string {
  return sha.substring(0, 7);
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function CIStatusPanel({ fullName, onBack }: CIStatusPanelProps) {
  const { config } = useConfig();

  const owner = fullName ? parseRepo(fullName).owner : null;
  const name = fullName ? parseRepo(fullName).name : null;
  const { runs, loading } = useCIRuns(owner, name);

  return (
    <div className="ci-panel">
      <div className="page-header-row">
        <div className="page-header">
          <h2>CI Status</h2>
          <p>
            {fullName
              ? `Recent workflow runs for ${fullName}`
              : "Select a repo from the sidebar or dashboard"}
          </p>
        </div>
        <button className="back-button" onClick={onBack}>
          &larr; Dashboard
        </button>
      </div>

      {config && config.repos.length > 0 && (
        <div className="ci-repo-selector">
          {config.repos.map((repo) => {
            const rf = `${repo.owner}/${repo.name}`;
            return (
              <button
                key={rf}
                className={`ci-repo-btn ${rf === fullName ? "active" : ""}`}
                onClick={() => {}}
              >
                {repo.name}
              </button>
            );
          })}
        </div>
      )}

      {loading && <div className="loading">Loading workflow runs...</div>}

      {!loading && runs.length === 0 && fullName && (
        <div className="empty-state">
          <div className="icon">&#9881;</div>
          <h3>No workflow runs found</h3>
          <p>This repository may not have GitHub Actions configured.</p>
        </div>
      )}

      {!fullName && (
        <div className="empty-state">
          <div className="icon">&#9881;</div>
          <h3>Select a repository</h3>
          <p>Click a repo card on the Dashboard or select from the sidebar.</p>
        </div>
      )}

      {runs.length > 0 && (
        <div className="run-list">
          {runs.map((run) => (
            <div className="run-item" key={run.id}>
              <span className="run-icon">
                {statusIcon(run.conclusion, run.status)}
              </span>
              <span className="run-name">{run.name}</span>
              <span className="run-branch">{run.branch}</span>
              <span className="run-duration">
                {runDuration(run)}
              </span>
              <span className="run-time" title={run.created_at}>
                {timeAgo(run.created_at)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
