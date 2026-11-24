import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import type { RepoStatus, WorkflowRun, Issue, PR, AppConfig } from "../types";

/**
 * Generic Tauri invoke hook with loading/error state.
 */
function useTauriCommand<T>(command: string, args?: Record<string, unknown>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await invoke<T>(command, args);
      setData(result);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [command, args]);

  return { data, loading, error, execute, setData };
}

/**
 * Hook for fetching all repo statuses with auto-refresh.
 */
export function useRepoStatuses(refreshIntervalSecs: number = 60) {
  const { data, loading, error, execute } =
    useTauriCommand<RepoStatus[]>("get_repo_status");

  useEffect(() => {
    execute();
    const interval = setInterval(execute, refreshIntervalSecs * 1000);
    return () => clearInterval(interval);
  }, [execute, refreshIntervalSecs]);

  return { repos: data ?? [], loading, error, refresh: execute };
}

/**
 * Hook for fetching CI workflow runs for a specific repo.
 */
export function useCIRuns(owner: string | null, name: string | null) {
  const args = owner && name ? { owner, name } : undefined;
  const { data, loading, error, execute } = useTauriCommand<WorkflowRun[]>(
    "get_ci_runs",
    args
  );

  useEffect(() => {
    if (owner && name) {
      execute();
    }
  }, [owner, name, execute]);

  return { runs: data ?? [], loading, error, refresh: execute };
}

/**
 * Hook for fetching open issues for a repo.
 */
export function useIssues(owner: string | null, name: string | null) {
  const args = owner && name ? { owner, name } : undefined;
  const { data, loading, error, execute } = useTauriCommand<Issue[]>(
    "get_open_issues",
    args
  );

  useEffect(() => {
    if (owner && name) {
      execute();
    }
  }, [owner, name, execute]);

  return { issues: data ?? [], loading, error, refresh: execute };
}

/**
 * Hook for fetching open PRs for a repo.
 */
export function usePRs(owner: string | null, name: string | null) {
  const args = owner && name ? { owner, name } : undefined;
  const { data, loading, error, execute } = useTauriCommand<PR[]>(
    "get_open_prs",
    args
  );

  useEffect(() => {
    if (owner && name) {
      execute();
    }
  }, [owner, name, execute]);

  return { prs: data ?? [], loading, error, refresh: execute };
}

/**
 * Hook for managing app config.
 */
export function useConfig() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(false);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const result = await invoke<AppConfig>("list_repos");
      setConfig(result);
    } catch (err) {
      console.error("Failed to load config:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const addRepo = useCallback(
    async (owner: string, name: string) => {
      try {
        const result = await invoke<AppConfig>("add_repo", { owner, name });
        setConfig(result);
        return true;
      } catch (err) {
        console.error("Failed to add repo:", err);
        return false;
      }
    },
    []
  );

  const removeRepo = useCallback(
    async (fullName: string) => {
      try {
        const result = await invoke<AppConfig>("remove_repo", {
          fullName,
        });
        setConfig(result);
        return true;
      } catch (err) {
        console.error("Failed to remove repo:", err);
        return false;
      }
    },
    []
  );

  return { config, loading, addRepo, removeRepo, refresh: loadConfig };
}
