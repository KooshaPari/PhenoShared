import { useRepoStatuses } from "../hooks/useHelios";
import { RepoCard } from "./RepoCard";

interface DashboardProps {
  onSelectRepo: (fullName: string) => void;
}

export function Dashboard({ onSelectRepo }: DashboardProps) {
  const { repos, loading, error } = useRepoStatuses();

  const passing = repos.filter((r) => r.ci_status === "passing").length;
  const failing = repos.filter((r) => r.ci_status === "failing").length;
  const pending = repos.filter((r) => r.ci_status === "pending").length;
  const totalStars = repos.reduce((sum, r) => sum + r.stars, 0);

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Health overview of all monitored repositories</p>
      </div>

      {repos.length > 0 && (
        <div className="dashboard-stats">
          <div className="stat-card">
            <div className="label">Repos</div>
            <div className="value">{repos.length}</div>
          </div>
          <div className="stat-card">
            <div className="label">Passing CI</div>
            <div className="value green">{passing}</div>
          </div>
          <div className="stat-card">
            <div className="label">Failing CI</div>
            <div className="value red">{failing}</div>
          </div>
          <div className="stat-card">
            <div className="label">Pending</div>
            <div className="value yellow">{pending}</div>
          </div>
          <div className="stat-card">
            <div className="label">Total Stars</div>
            <div className="value">{totalStars.toLocaleString()}</div>
          </div>
        </div>
      )}

      {loading && repos.length === 0 && (
        <div className="loading">Loading repository statuses...</div>
      )}

      {error && (
        <div className="empty-state">
          <h3>Error loading data</h3>
          <p>{error}</p>
        </div>
      )}

      {!loading && repos.length === 0 && !error && (
        <div className="empty-state">
          <div className="icon">&#9729;</div>
          <h3>No repositories configured</h3>
          <p>
            Go to Settings to add repositories you want to monitor. You can add
            any GitHub repo you have access to.
          </p>
        </div>
      )}

      {repos.length > 0 && (
        <div className="repo-grid">
          {repos.map((repo) => (
            <RepoCard
              key={repo.full_name}
              repo={repo}
              onClick={onSelectRepo}
            />
          ))}
        </div>
      )}
    </div>
  );
}
