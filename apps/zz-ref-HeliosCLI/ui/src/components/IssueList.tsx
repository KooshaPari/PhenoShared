import { useIssues } from "../hooks/useHelios";

interface IssueListProps {
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

export function IssueList({ fullName, onBack }: IssueListProps) {
  const owner = fullName ? parseRepo(fullName).owner : null;
  const name = fullName ? parseRepo(fullName).name : null;
  const { issues, loading } = useIssues(owner, name);

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header">
          <h2>Open Issues</h2>
          <p>{fullName ? `Issues in ${fullName}` : "Select a repo first"}</p>
        </div>
        <button className="back-button" onClick={onBack}>
          &larr; Dashboard
        </button>
      </div>

      {loading && <div className="loading">Loading issues...</div>}

      {!loading && issues.length === 0 && fullName && (
        <div className="empty-state">
          <div className="icon">&#10003;</div>
          <h3>No open issues</h3>
          <p>This repository has no open issues. All clear!</p>
        </div>
      )}

      {!fullName && (
        <div className="empty-state">
          <div className="icon">&#9679;</div>
          <h3>Select a repository</h3>
          <p>Click a repo card on the Dashboard to view its issues.</p>
        </div>
      )}

      {issues.length > 0 && (
        <div className="list-container">
          {issues.map((issue) => (
            <div className="list-item" key={issue.number}>
              <span className="list-item-number">#{issue.number}</span>
              <div className="list-item-content">
                <div className="list-item-title">{issue.title}</div>
                <div className="list-item-meta">
                  <span className="author">{issue.author}</span>
                  <span>{timeAgo(issue.created_at)}</span>
                  {issue.labels.map((label) => (
                    <span key={label} className="label-tag">
                      {label}
                    </span>
                  ))}
                  {issue.assignee && <span>assignee: {issue.assignee}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
