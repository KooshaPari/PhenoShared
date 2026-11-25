import { useRepoStatuses, useConfig } from "../hooks/useHelios";
import type { Page } from "../types";

interface SidebarProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  selectedRepo: string | null;
}

export function Sidebar({ currentPage, onNavigate, selectedRepo }: SidebarProps) {
  const { repos } = useRepoStatuses();
  const { config } = useConfig();
  const repoCount = config?.repos.length ?? 0;

  const navItems: { page: Page; icon: string; label: string }[] = [
    { page: "dashboard", icon: "\u25A3", label: "Dashboard" },
    { page: "ci", icon: "\u2699", label: "CI Status" },
    { page: "issues", icon: "\u25CB", label: "Issues" },
    { page: "prs", icon: "\u25B6", label: "Pull Requests" },
    { page: "settings", icon: "\u2692", label: "Settings" },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <h1>&#9788; HELIOS</h1>
        <p>Command Center</p>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <div
            key={item.page}
            className={`sidebar-item ${currentPage === item.page ? "active" : ""}`}
            onClick={() => onNavigate(item.page)}
          >
            <span className="icon">{item.icon}</span>
            <span>{item.label}</span>
            {item.page === "dashboard" && repoCount > 0 && (
              <span className="sidebar-badge">{repoCount}</span>
            )}
          </div>
        ))}
      </nav>

      {config && config.repos.length > 0 && (
        <div className="sidebar-repo-section">
          <h3>Monitored</h3>
          {config.repos.map((repo) => {
            const rf = `${repo.owner}/${repo.name}`;
            const status = repos.find((r) => r.full_name === rf);
            return (
              <div
                key={rf}
                className={`sidebar-repo-item ${selectedRepo === rf ? "selected" : ""}`}
                onClick={() => onNavigate("ci")}
              >
                {status && (
                  <span className={`ci-dot ${status.ci_status}`} />
                )}
                {!status && (
                  <span className="ci-dot unknown" />
                )}
                <span>{repo.name}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
