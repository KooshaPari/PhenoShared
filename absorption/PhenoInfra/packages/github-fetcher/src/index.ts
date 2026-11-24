// Shared GitHub API client for Phenotype landing pages

const DEFAULT_HEADERS: Record<string, string> = {
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": "phenotype-landing",
};

export interface RepoInfo {
  name: string;
  description: string | null;
  url: string;
  homepage: string | null;
  language: string | null;
  stars: number;
  forks: number;
  pushedAt: string;
  archived: boolean;
  topics: string[];
}

export async function fetchRepoInfo(owner: string, repo: string, token?: string): Promise<RepoInfo | null> {
  const headers = { ...DEFAULT_HEADERS };
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(`https://api.github.com/repos/${owner}/${repo}`, { headers });
    if (!res.ok) return null;
    const json = await res.json();
    return {
      name: json.name,
      description: json.description,
      url: json.html_url,
      homepage: json.homepage,
      language: json.language,
      stars: json.stargazers_count ?? 0,
      forks: json.forks_count ?? 0,
      pushedAt: json.pushed_at,
      archived: !!json.archived,
      topics: json.topics ?? [],
    };
  } catch {
    return null;
  }
}

export async function fetchUserRepos(owner: string, token?: string, maxPages = 10): Promise<RepoInfo[]> {
  const headers = { ...DEFAULT_HEADERS };
  if (token) headers.Authorization = `Bearer ${token}`;

  const all: RepoInfo[] = [];
  const PER_PAGE = 100;

  for (let page = 1; page <= maxPages; page++) {
    const url = `https://api.github.com/users/${owner}/repos?per_page=${PER_PAGE}&page=${page}&sort=pushed`;
    const res = await fetch(url, { headers });
    if (!res.ok) break;
    const batch = await res.json();
    if (!Array.isArray(batch)) break;
    for (const r of batch) {
      all.push({
        name: r.name,
        description: r.description,
        url: r.html_url,
        homepage: r.homepage,
        language: r.language,
        stars: r.stargazers_count ?? 0,
        forks: r.forks_count ?? 0,
        pushedAt: r.pushed_at,
        archived: !!r.archived,
        topics: r.topics ?? [],
      });
    }
    if (batch.length < PER_PAGE) break;
  }

  return all;
}
