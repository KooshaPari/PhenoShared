# Commit log (rich view)

Sample **git-style** history for the documentation hub. Data is loaded from `.vitepress/data/commit-log.json` (replace in CI with output from `git log` across federated repos).

<CommitLog />

## Producing data locally

```bash
# Example: last 20 commits as JSON (shape must match commit-log.json)
git log -20 --pretty=format:'{"sha":"%h","date":"%cs","author":"%an","subject":"%s","repo":"phenodocs"},' \
  | sed '1s/^/[/; $s/,$/]/' > .vitepress/data/commit-log.json
```

(Adjust quoting for strict JSON; use `jq` in production.)
