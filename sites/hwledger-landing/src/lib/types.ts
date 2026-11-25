/**
 * Shared TypeScript interfaces for landing pages
 */

export interface CoverageReport {
  pct?: number;
  lines_total?: number;
  lines_covered?: number;
  generated_at?: string;
}

export interface LintReport {
  clippy?: { errors: number; warnings: number };
  ruff?: { errors: number; warnings: number };
  vale?: { errors: number; warnings: number; suggestions?: number };
  generated_at?: string;
}

export interface FrTraceReport {
  total_frs?: number;
  covered_frs?: number;
  uncovered?: string[];
  generated_at?: string;
}

export interface GhContentEntry {
  name: string;
  path: string;
  sha: string;
  size: number;
  url: string;
  html_url: string;
  git_url: string;
  download_url: string | null;
  type: 'file' | 'dir' | 'symlink';
}

export interface GhRepoMeta {
  description: string;
  stargazers_count: number;
  pushed_at: string;
  language: string | null;
  homepage: string;
  full_name: string;
  html_url: string;
}

export interface GhRelease {
  id: number;
  tag_name: string;
  name: string | null;
  html_url: string;
  published_at: string;
  body?: string;
}

export interface PrInfo {
  number: number;
  title: string;
  branch: string;
  sha: string;
  html_url: string;
  previewUrl: string;
  previewSource: 'vercel-check-run' | 'deployment-api' | 'branch-alias-fallback';
}

export interface PanelResult<T> {
  data: T | null;
  reason: string | null;
}
