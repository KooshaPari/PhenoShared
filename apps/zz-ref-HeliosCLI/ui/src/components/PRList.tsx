import { usePRs } from "../hooks/useHelios";

interface PRListProps {
  fullName: string | null;
  onBack: () => void;
}

function parseRepo(fullName: string): { owner: string; name: string } {
  const [owner, ...rest] = fullName.split("/");
  return { owner, name: rest.join("/") };
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

export function PRList({ fullName, onBack }: PRListProps) {
  const owner = fullName ? parseRepo(fullName).owner : null;
  const name = fullName ? parseRepo(fullName).name : null;
  const { prs, loading } = usePRs(owner, name);

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header">
          <h2>Open Pull Requests</h2>
          <p>
            {fullName ? `Pull requests in ${fullName}` : "Select a repo first"}
          </p>
        </div>
        <button className="back-button" onClick={onBack}>
          &larr; Dashboard
        </button>
      </div>

      {loading && <div className="loading">Loading pull requests...</div>}

      {!loading && prs.length === 0 && fullName && (
        <div className="empty-state">
          <div className="icon">&#10003;</div>
          <h3>No open pull requests</h3>
          <p>This repository has no open pull requests.</p>
        </div>
      )}

      {!fullName && (
        <div className="empty-state">
          <div className="icon">&#9654;</div>
          <h3>Select a repository</h3>
          <p>Click a repo card on the Dashboard to view its pull requests.</p>
        </div>
      )}

      {prs.length > 0 && (
        <div className="list-container">
          {prs.map((pr) => (
            <div className="list-item" key={pr.number}>
              <span className="list-item-number">#{pr.number}</span>
              <div className="list-item-content">
                <div className="list-item-title">
                  {pr.draft && <span className="draft-tag">Draft </span>}
                  {pr.title}
                </div>
                <div className="list-item-meta">
                  <span className="author">{pr.author}</span>
                  <span>{timeAgo(pr.created_at)}</span>
                  {pr.labels.map((label) => (
                    <span key={label} className="label-tag">
                      {label}
                    </span>
                  ))}
                  <span
                    className={`ci-dot ${pr.ci_status}`}
                    style={{ width: 8, height: 8 }}
                    title={`CI: ${pr.ci_status}`}
                  />
                </div>
              </div>
              <div className="list-item-right">
                {pr.draft ? (
                  <span className="review-badge draft">Draft</span>
                ) : (
                  <span className="review-badge pending">
                    {pr.review_status}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
