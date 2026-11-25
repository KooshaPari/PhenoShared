/**
 * View RPC bridge. The renderer calls `getRepoState` on boot to load
 * specs, ADRs, and traces from the selected local repo.
 */

import { BrowserView, type RPCSchema } from "electrobun/bun";
import type { RepoBridge } from "../repo-bridge";
import type { CLI } from "../cli";
import type { AppPaths } from "../paths";

export type RepoRPC = {
  bun: RPCSchema<{
    requests: {
      getRepoState: {
        params: Record<string, never>;
        response: {
          repoRoot: string;
          specs: Awaited<ReturnType<RepoBridge["listSpecs"]>>;
          adrs: Awaited<ReturnType<RepoBridge["listAdrs"]>>;
          traces: Awaited<ReturnType<RepoBridge["listTraces"]>>;
        };
      };
    };
    messages: Record<string, never>;
  }>;
  webview: RPCSchema<{
    requests: Record<string, never>;
    messages: Record<string, never>;
  }>;
};

export function createRepoRpc(deps: {
  repo: RepoBridge;
  cli: CLI;
  paths: AppPaths;
}) {
  void deps.cli;
  return BrowserView.defineRPC<RepoRPC>({
    maxRequestTime: 5000,
    handlers: {
      requests: {
        getRepoState: async () => {
          const [specs, adrs, traces] = await Promise.all([
            deps.repo.listSpecs(),
            deps.repo.listAdrs(),
            deps.repo.listTraces(),
          ]);
          return {
            repoRoot: deps.paths.repoRoot,
            specs,
            adrs,
            traces,
          };
        },
      },
      messages: {},
    },
  });
}
