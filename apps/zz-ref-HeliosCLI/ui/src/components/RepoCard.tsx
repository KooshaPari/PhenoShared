import type { RepoStatus } from "../types";

interface RepoCardProps {
  repo: RepoStatus;
  onClick: (fullName: string) => void;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "never";
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function RepoCard({ repo, onClick }: RepoCardProps) {
  return (
    <div className="repo-card" onClick={() => onClick(repo.full_name)}>
      <div className="repo-card-header">
        <span className="repo-card-name">{repo.name}</span>
        <span className={`ci-dot ${repo.ci_status}`} title={repo.ci_status} />
      </div>

      {repo.description && (
        <p className="repo-card-description">{repo.description}</p>
      )}

      <div className="repo-card-stats">
        <span className="repo-stat">
          <span>&#9733;</span>
          <span className="count">{repo.stars}</span>
        </span>
        <span className="repo-stat">
          <span>&#9741;</span>
          <span className="count">{repo.forks}</span>
        </span>
        <span className="repo-stat">
          <span>&#9679;</span>
          <span className="count">{repo.open_issues}</span>
          issues
        </span>
        <span className="repo-stat">
          <span>&#9654;</span>
          <span className="count">{repo.open_prs}</span>
          PRs
        </span>
      </div>

      <div className="repo-card-meta">
        <span>{repo.default_branch}</span>
        <span>pushed {timeAgo(repo.last_push)}</span>
      </div>
    </div>
  );
}
