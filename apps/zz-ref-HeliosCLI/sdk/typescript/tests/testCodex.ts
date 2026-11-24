import path from "node:path";

import { Codex } from "../src/codex";
import type { CodexConfigObject } from "../src/codexOptions";

/**
 * Resolve the `codex` binary the integration tests drive.
 *
 * Two things this has to get right:
 *
 *  1. Cargo honors `CARGO_TARGET_DIR`, which relocates the entire target tree.
 *     Hardcoding `codex-rs/target/debug/codex` silently points at a path that
 *     may not exist, which is the case in this repo's own CI/dev setup where
 *     CARGO_TARGET_DIR is set. A relative value is resolved against the
 *     codex-rs workspace, since that is where cargo is invoked from.
 *  2. `spawn` with an absolute path does not do PATHEXT resolution, so the
 *     Windows binary needs its `.exe` suffix spelled out.
 */
function resolveCodexExecPath(): string {
  const explicit = process.env.CODEX_EXEC_PATH;
  if (explicit) {
    return explicit;
  }

  const workspaceDir = path.join(process.cwd(), "..", "..", "codex-rs");
  const cargoTargetDir = process.env.CARGO_TARGET_DIR;
  const targetDir = cargoTargetDir
    ? path.resolve(workspaceDir, cargoTargetDir)
    : path.join(workspaceDir, "target");

  const binaryName = process.platform === "win32" ? "codex.exe" : "codex";
  return path.join(targetDir, "debug", binaryName);
}

export const codexExecPath = resolveCodexExecPath();

type CreateTestClientOptions = {
  apiKey?: string;
  baseUrl?: string;
  config?: CodexConfigObject;
  env?: Record<string, string>;
  inheritEnv?: boolean;
};

export type TestClient = {
  cleanup: () => void;
  client: Codex;
};

export function createMockClient(url: string): TestClient {
  return createTestClient({
    config: {
      model_provider: "mock",
      model_providers: {
        mock: {
          name: "Mock provider for test",
          base_url: url,
          wire_api: "responses",
          supports_websockets: false,
        },
      },
    },
  });
}

export function createTestClient(options: CreateTestClientOptions = {}): TestClient {
  const env =
    options.inheritEnv === false ? { ...options.env } : { ...getCurrentEnv(), ...options.env };

  return {
    cleanup: () => {},
    client: new Codex({
      codexPathOverride: codexExecPath,
      baseUrl: options.baseUrl,
      apiKey: options.apiKey,
      config: mergeTestConfig(options.baseUrl, options.config),
      env,
    }),
  };
}

function mergeTestConfig(
  baseUrl: string | undefined,
  config: CodexConfigObject | undefined,
): CodexConfigObject | undefined {
  const mergedConfig: CodexConfigObject | undefined =
    !baseUrl || hasExplicitProviderConfig(config)
      ? config
      : {
          ...config,
          // Built-in providers are merged before user config, so tests need a
          // custom provider entry to force SSE against the local mock server.
          model_provider: "mock",
          model_providers: {
            mock: {
              name: "Mock provider for test",
              base_url: baseUrl,
              wire_api: "responses",
              supports_websockets: false,
            },
          },
        };
  const featureOverrides = mergedConfig?.features;

  return {
    ...mergedConfig,
    // Disable plugins in SDK integration tests so background curated-plugin
    // sync does not race temp CODEX_HOME cleanup.
    features:
      featureOverrides && typeof featureOverrides === "object" && !Array.isArray(featureOverrides)
        ? { ...featureOverrides, plugins: false }
        : { plugins: false },
  };
}

function hasExplicitProviderConfig(config: CodexConfigObject | undefined): boolean {
  return config?.model_provider !== undefined || config?.model_providers !== undefined;
}

function getCurrentEnv(): Record<string, string> {
  const env: Record<string, string> = {};

  for (const [key, value] of Object.entries(process.env)) {
    if (key === "CODEX_INTERNAL_ORIGINATOR_OVERRIDE") {
      continue;
    }
    if (value !== undefined) {
      env[key] = value;
    }
  }

  return env;
}
