/// A monitored repository's status.
export interface RepoStatus {
  name: string;
  full_name: string;
  description: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  open_prs: number;
  default_branch: string;
  last_push: string | null;
  ci_status: CIStatus;
  url: string;
}

/// Aggregated CI status.
export type CIStatus = "passing" | "pending" | "failing" | "unknown";

/// A GitHub Actions workflow run.
export interface WorkflowRun {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  branch: string;
  commit_sha: string;
  commit_message: string | null;
  created_at: string;
  updated_at: string;
  run_started_at: string | null;
  html_url: string;
}

/// An open GitHub issue.
export interface Issue {
  number: number;
  title: string;
  state: string;
  labels: string[];
  assignee: string | null;
  created_at: string;
  updated_at: string;
  html_url: string;
  author: string;
}

/// An open GitHub pull request.
export interface PR {
  number: number;
  title: string;
  author: string;
  state: string;
  draft: boolean;
  mergeable: boolean | null;
  labels: string[];
  created_at: string;
  updated_at: string;
  html_url: string;
  head_sha: string;
  ci_status: CIStatus;
  review_status: string;
}

/// A repository the user wants to monitor.
export interface MonitoredRepo {
  owner: string;
  name: string;
}

/// Full app configuration.
export interface AppConfig {
  repos: MonitoredRepo[];
  github_token: string | null;
  refresh_interval_secs: number;
}

/// Navigation page type.
export type Page = "dashboard" | "ci" | "issues" | "prs" | "settings";
