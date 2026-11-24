# Publish Risk Assessment - 2026-11-19

Generated: 2026-11-18T16:50:12-08:00
Scope: 27 private KooshaPari repositories, default-branch trees inspected for disclosure risk prior to any publish-to-PhenoShared decision.

## Summary ranking (highest risk first)

| Rank | Repository | Highest severity | Findings | Verdict |
|---:|---|---|---:|---|
| 1 | audit-snapshot-OmniRoute | high | 41 | do not publish |
| 2 | audit-snapshot-pheno | medium | 44 | scrub first |
| 3 | audit-snapshot-tooling | medium | 44 | scrub first |
| 4 | audit-snapshot-agentapi | medium | 43 | scrub first |
| 5 | cliproxyapi-plusplus | medium | 43 | scrub first |
| 6 | audit-snapshot-HexaKit | medium | 29 | scrub first |
| 7 | audit-snapshot-AgilePlus | medium | 20 | scrub first |
| 8 | argis-extensions-preserved-20261114 | medium | 16 | scrub first |
| 9 | audit-snapshot-argis | medium | 16 | scrub first |
| 10 | Personal | medium | 7 | scrub first |
| 11 | BytePort | medium | 6 | scrub first |
| 12 | harness-ops | medium | 6 | scrub first |
| 13 | phenotype-landing | medium | 6 | scrub first |
| 14 | chatta | medium | 4 | scrub first |
| 15 | zz-argis-extensions | medium | 4 | scrub first |
| 16 | zz-HexaKit | medium | 3 | scrub first |
| 17 | HarnessDesk | medium | 1 | scrub first |
| 18 | PhenoVCS | medium | 1 | scrub first |
| 19 | audit-snapshot-PhenoVCS | medium | 1 | scrub first |
| 20 | phenoDesign-visual-production-v2 | medium | 1 | scrub first |
| 21 | StealthStartup | none | 0 | safe to publish |
| 22 | audit-snapshot-hwLedger | none | 0 | safe to publish |
| 23 | audit-system | none | 0 | safe to publish |
| 24 | cvp-fixture | none | 0 | safe to publish |
| 25 | dagrun | none | 0 | safe to publish |
| 26 | phenoreg-browser-audit | none | 0 | safe to publish |
| 27 | zz-aa-dep-AirLock | none | 0 | safe to publish |

## Per-repository details

### audit-snapshot-OmniRoute

- Default branch: `main`
- Files scanned (tree blobs): 13989
- Content files fetched (sampled): 40
- Tree truncated: no
- Categories hit: filename:credentials-named, filename:docker-compose, filename:env-file, filename:npmrc, filename:secrets-named, filename:token-named, openai-key
- Highest severity: **high**
- Verdict: **do not publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `@omniroute/opencode-plugin/tests/management-read-token.test.ts` | openai-key | high | sk-m… | content |
| `@omniroute/opencode-plugin/tests/management-read-token.test.ts` | filename:token-named | medium | n/a | filename |
| `bin/cli/commands/tokens.mjs` | filename:token-named | medium | n/a | filename |
| `bin/cli/utils/cliToken.mjs` | filename:token-named | medium | n/a | filename |
| `docs/i18n/pl/docs/security/CLI_TOKEN.md` | filename:token-named | medium | n/a | filename |
| `docs/security/CLI_TOKEN.md` | filename:token-named | medium | n/a | filename |
| `docs/sessions/20260715-apple-oci-caddy/artifacts/runtime.env` | filename:env-file | medium | n/a | filename |
| `docs/sessions/20260715-apple-oci-caddy/artifacts/static.env` | filename:env-file | medium | n/a | filename |
| `extensions/argis/config/secrets.go` | filename:secrets-named | medium | n/a | filename |
| `extensions/argis/config/secrets_test.go` | filename:secrets-named | medium | n/a | filename |
| `extensions/argis/findings/2026-06-18-T9-2-secret-block-resolution.md` | filename:secrets-named | medium | n/a | filename |
| `extensions/argis/findings/2026-06-19-T21-1-secret-scan-rescan.md` | filename:secrets-named | medium | n/a | filename |
| `extensions/argis/pheno-secret-scan/.github/workflows/secret-scan.yml` | filename:secrets-named | medium | n/a | filename |
| `open-sse/config/credentialLoader.ts` | filename:credentials-named | medium | n/a | filename |
| `open-sse/handlers/chatCore/cliproxyapiCredentials.ts` | filename:credentials-named | medium | n/a | filename |
| `open-sse/handlers/chatCore/executionCredentials.ts` | filename:credentials-named | medium | n/a | filename |
| `open-sse/handlers/chatCore/outputTokenBudget.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/rpc/edges/tokenBucketEdges.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/rpc/edges/tokenBucketFfi.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/services/credentialGate.ts` | filename:credentials-named | medium | n/a | filename |
| `open-sse/services/reasoningTokenBuffer.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/services/tokenBucket.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/services/tokenExtractionConfig.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/services/tokenLimitCounter.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/services/tokenRefresh.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/translator/helpers/__tests__/maxTokensHelper.test.ts` | filename:token-named | medium | n/a | filename |
| `open-sse/translator/helpers/maxTokensHelper.ts` | filename:token-named | medium | n/a | filename |
| `scripts/check/check-secrets.mjs` | filename:secrets-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/combos/ReasoningTokenBufferToggle.tsx` | filename:token-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/endpoint/VscodeTokenAliasCard.tsx` | filename:token-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/playground/components/TokenCostCounter.tsx` | filename:token-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/providers/[id]/components/WebSessionCredentialGuide.tsx` | filename:credentials-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/providers/[id]/providerCredentialText.ts` | filename:credentials-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/providers/[id]/webSessionCredentials.ts` | filename:credentials-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/settings/components/AccessTokensTab.tsx` | filename:token-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/settings/components/CompressionTokenSaverCard.tsx` | filename:token-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/settings/components/UsageTokenBufferTab.tsx` | filename:token-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/tools/traffic-inspector/components/shared/SecretMaskToggle.tsx` | filename:secrets-named | medium | n/a | filename |
| `src/app/(dashboard)/dashboard/tools/traffic-inspector/components/shared/TokenBadge.tsx` | filename:token-named | medium | n/a | filename |
| `src/app/api/v1/vscode/[token]/tokenizedRequest.ts` | filename:token-named | medium | n/a | filename |
| `src/app/api/v1/vscode/raw/[token]/tokenizedRequest.ts` | filename:token-named | medium | n/a | filename |

### audit-snapshot-pheno

- Default branch: `main`
- Files scanned (tree blobs): 8876
- Content files fetched (sampled): 40
- Tree truncated: no
- Categories hit: email-address, filename:credentials-named, filename:docker-compose, filename:env-file, filename:npmrc, filename:secrets-named, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `TOKEN_ACQUISITION_CHECKLIST.md` | filename:token-named | medium | n/a | filename |
| `agileplus-agents/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `agileplus-mcp/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `agileplus/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `agileplus/crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `agileplus/docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `agileplus/docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `crates/agile-plus/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `crates/agile-plus/crates/agileplus-api/src/middleware/token_verifier.rs` | filename:token-named | medium | n/a | filename |
| `crates/agile-plus/crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `crates/agile-plus/crates/agileplus-triage/src/ast_tokenize.rs` | filename:token-named | medium | n/a | filename |
| `crates/agile-plus/docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `crates/agile-plus/docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `crates/agile-plus/findings/secrets_precommit_audit_2026-05-05.md` | filename:secrets-named | medium | n/a | filename |
| `crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `crates/hexa-kit/TOKEN_ACQUISITION_CHECKLIST.md` | filename:token-named | medium | n/a | filename |
| `crates/hexa-kit/agileplus-agents/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `crates/hexa-kit/agileplus-mcp/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `crates/hexa-kit/agileplus/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `crates/hexa-kit/agileplus/crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `crates/hexa-kit/agileplus/docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `crates/hexa-kit/agileplus/docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `crates/hexa-kit/crates/phenotype-port-traits/src/outbound/secret.rs` | filename:secrets-named | medium | n/a | filename |
| `crates/hexa-kit/docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | filename:secrets-named | medium | n/a | filename |
| `crates/hexa-kit/docs/guides/SNYK_TOKEN_ACQUISITION_GUIDE.md` | filename:token-named | medium | n/a | filename |
| `crates/hexa-kit/docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `crates/hexa-kit/docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `crates/hexa-kit/forgecode-fork/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `crates/pheno-config/src/secret.rs` | filename:secrets-named | medium | n/a | filename |
| `crates/phenotype-port-traits/src/outbound/secret.rs` | filename:secrets-named | medium | n/a | filename |
| `docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | filename:secrets-named | medium | n/a | filename |
| `docs/guides/SNYK_TOKEN_ACQUISITION_GUIDE.md` | filename:token-named | medium | n/a | filename |
| `docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `forgecode-fork/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `pheno-cli/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `phenotype-governance/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `phenotype-infrakit/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `phenotype-infrakit/crates/phenotype-rate-limiter/src/adapters/token_bucket.rs` | filename:token-named | medium | n/a | filename |
| `phenotype-router-monitor/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `TOKEN_ACQUISITION_CHECKLIST.md` | email-address | low | your… | content |
| `crates/hexa-kit/TOKEN_ACQUISITION_CHECKLIST.md` | email-address | low | your… | content |
| `crates/hexa-kit/docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | email-address | low | your… | content |
| `docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | email-address | low | your… | content |

### audit-snapshot-tooling

- Default branch: `main`
- Files scanned (tree blobs): 22552
- Content files fetched (sampled): 40
- Tree truncated: no
- Categories hit: email-address, filename:credentials-named, filename:docker-compose, filename:env-file, filename:npmrc, filename:secrets-named, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `absorption/phenotype-router-monitor-root/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `absorption/phenotype-router-monitor-root/phenotype-router-monitor/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `absorption/phenotype-router-monitor/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `crates/phinbox/tests/fixtures/secret.json` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-HeliosCLI/.archive/absorb-readiness-2026-03-03/repo-heads.env` | filename:env-file | medium | n/a | filename |
| `docs/absorbed-from-Paginary/apps/specs/src/content/research/SECRETS_MANAGERS_SOTA.md` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-Paginary/apps/specs/src/content/research/SECRET_DISTRIBUTION_SOTA.md` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-Paginary/apps/specs/src/content/specs/crypto/secrets/docs/journeys/secret-rotation.md` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-Paginary/apps/specs/src/content/specs/crypto/secrets/docs/journeys/team-secrets-sharing.md` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-Paginary/apps/specs/src/content/specs/platform/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/TOKEN_ACQUISITION_CHECKLIST.md` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/agileplus-agents/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/agileplus-mcp/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/agileplus/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/agileplus/crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/agileplus/docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/agileplus/docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/crates/phenotype-port-traits/src/outbound/secret.rs` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/docs/guides/SNYK_TOKEN_ACQUISITION_GUIDE.md` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/pheno-cli/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/phenotype-governance/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoDevOps/phenotype-infrakit/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoFastMCP/fastmcp_slim/fastmcp/utilities/token_cache.py` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoFastMCP/tests/server/auth/oauth_proxy/test_tokens.py` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoFastMCP/tests/server/auth/test_oidc_proxy_token.py` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoFastMCP/tests/server/auth/test_static_token_verifier.py` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoFastMCP/tests/server/http/test_stale_access_token.py` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoFastMCP/tests/utilities/test_token_cache.py` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/apps/pheno-cli/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/crates/phenotype-router-monitor/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/phenotype-router-monitor/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/phenotype-router-monitor/phenotype-router-monitor/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/python/pheno-deployment/src/pheno_deployment/cloud/types/credentials.py` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/python/pheno-mcp/src/pheno_mcp/qa/oauth/credential_broker.py` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/python/pheno-observability/src/pheno_observability/metrics/metrics_token.py` | filename:token-named | medium | n/a | filename |
| `docs/absorbed-from-PhenoProc/python/pheno-testing/src/pheno_testing/mcp_qa/auth/credential_manager.py` | filename:credentials-named | medium | n/a | filename |
| `docs/absorbed-from-Paginary/apps/specs/src/content/specs/crypto/secrets/docs/journeys/team-secrets-sharing.md` | email-address | low | alic… | content |
| `docs/absorbed-from-PhenoDevOps/TOKEN_ACQUISITION_CHECKLIST.md` | email-address | low | your… | content |
| `docs/absorbed-from-PhenoDevOps/docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | email-address | low | your… | content |
| `docs/absorbed-from-PhenoProc/python/pheno-testing/src/pheno_testing/mcp_qa/auth/credential_manager.py` | email-address | low | user… | content |

### audit-snapshot-agentapi

- Default branch: `main`
- Files scanned (tree blobs): 2605
- Content files fetched (sampled): 40
- Tree truncated: no
- Categories hit: email-address, filename:credentials-named, filename:docker-compose, filename:env-file, filename:secrets-named, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.github/scripts/check-docs-secret-samples.sh` | filename:secrets-named | medium | n/a | filename |
| `.github/scripts/check-phase-doc-placeholder-tokens.sh` | filename:token-named | medium | n/a | filename |
| `.github/scripts/check-workflow-token-permissions.sh` | filename:token-named | medium | n/a | filename |
| `.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `examples/systemd/cliproxyapi-plusplus.env` | filename:env-file | medium | n/a | filename |
| `pkg/llmproxy/api/handlers/management/oauth_token_antigravity.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/api/handlers/management/oauth_token_gemini.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/api/handlers/management/token_resolution.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/api/modules/amp/secret.go` | filename:secrets-named | medium | n/a | filename |
| `pkg/llmproxy/api/modules/amp/secret_test.go` | filename:secrets-named | medium | n/a | filename |
| `pkg/llmproxy/auth/base/token_storage.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/claude/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/claude/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/codex/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/codex/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/copilot/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/copilot/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/empty/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/gemini/gemini_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/gemini/gemini_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/iflow/iflow_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/iflow/iflow_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kilo/kilo_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kilo/kilo_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kimi/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kimi/token_path_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kimi/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/aws_load_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token_extra_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token_repository.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token_repository_camelcase_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/oauth_token_manager.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/oauth_token_manager_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/qwen/qwen_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/qwen/qwen_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/vertex/vertex_credentials.go` | filename:credentials-named | medium | n/a | filename |
| `pkg/llmproxy/auth/xai/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/executor/helps/token_helpers.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/executor/token_helpers.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/codex/token_test.go` | email-address | low | test… | content |
| `pkg/llmproxy/auth/kiro/token_extra_test.go` | email-address | low | test… | content |
| `pkg/llmproxy/auth/qwen/qwen_token_test.go` | email-address | low | test… | content |

### cliproxyapi-plusplus

- Default branch: `main`
- Files scanned (tree blobs): 3129
- Content files fetched (sampled): 40
- Tree truncated: no
- Categories hit: email-address, filename:credentials-named, filename:docker-compose, filename:env-file, filename:secrets-named, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.github/scripts/check-docs-secret-samples.sh` | filename:secrets-named | medium | n/a | filename |
| `.github/scripts/check-phase-doc-placeholder-tokens.sh` | filename:token-named | medium | n/a | filename |
| `.github/scripts/check-workflow-token-permissions.sh` | filename:token-named | medium | n/a | filename |
| `.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `examples/systemd/cliproxyapi-plusplus.env` | filename:env-file | medium | n/a | filename |
| `pkg/llmproxy/api/handlers/management/oauth_token_antigravity.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/api/handlers/management/oauth_token_gemini.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/api/handlers/management/token_resolution.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/api/modules/amp/secret.go` | filename:secrets-named | medium | n/a | filename |
| `pkg/llmproxy/api/modules/amp/secret_test.go` | filename:secrets-named | medium | n/a | filename |
| `pkg/llmproxy/auth/base/token_storage.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/claude/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/claude/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/codex/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/codex/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/copilot/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/copilot/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/empty/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/gemini/gemini_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/gemini/gemini_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/iflow/iflow_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/iflow/iflow_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kilo/kilo_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kilo/kilo_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kimi/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kimi/token_path_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kimi/token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/aws_load_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token_extra_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token_repository.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/kiro/token_repository_camelcase_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/oauth_token_manager.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/oauth_token_manager_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/qwen/qwen_token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/qwen/qwen_token_test.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/vertex/vertex_credentials.go` | filename:credentials-named | medium | n/a | filename |
| `pkg/llmproxy/auth/xai/token.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/executor/helps/token_helpers.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/executor/token_helpers.go` | filename:token-named | medium | n/a | filename |
| `pkg/llmproxy/auth/codex/token_test.go` | email-address | low | test… | content |
| `pkg/llmproxy/auth/kiro/token_extra_test.go` | email-address | low | test… | content |
| `pkg/llmproxy/auth/qwen/qwen_token_test.go` | email-address | low | test… | content |

### audit-snapshot-HexaKit

- Default branch: `main`
- Files scanned (tree blobs): 3308
- Content files fetched (sampled): 26
- Content fetch/scan errors: 4
- Tree truncated: no
- Categories hit: email-address, filename:credentials-named, filename:docker-compose, filename:env-file, filename:npmrc, filename:secrets-named, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.env.development.example` | filename:env-file | medium | n/a | filename |
| `.env.example` | filename:env-file | medium | n/a | filename |
| `.npmrc` | filename:npmrc | medium | n/a | filename |
| `TOKEN_ACQUISITION_CHECKLIST.md` | filename:token-named | medium | n/a | filename |
| `agileplus-agents/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `agileplus-mcp/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `agileplus/.env.example` | filename:env-file | medium | n/a | filename |
| `agileplus/.npmrc` | filename:npmrc | medium | n/a | filename |
| `agileplus/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `agileplus/crates/agileplus-dashboard/web/.env.development` | filename:env-file | medium | n/a | filename |
| `agileplus/crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `agileplus/docker-compose.plane.yml` | filename:docker-compose | medium | n/a | filename |
| `agileplus/docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `agileplus/docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `agileplus/docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `agileplus/tests/integration/docker-compose.test.yml` | filename:docker-compose | medium | n/a | filename |
| `crates/phenotype-port-traits/src/outbound/secret.rs` | filename:secrets-named | medium | n/a | filename |
| `docker-compose.plane.yml` | filename:docker-compose | medium | n/a | filename |
| `docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | filename:secrets-named | medium | n/a | filename |
| `docs/guides/SNYK_TOKEN_ACQUISITION_GUIDE.md` | filename:token-named | medium | n/a | filename |
| `docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `forgecode-fork/.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `templates/appgen/desktop-electrobun/.env.example` | filename:env-file | medium | n/a | filename |
| `tests/integration/docker-compose.test.yml` | filename:docker-compose | medium | n/a | filename |
| `TOKEN_ACQUISITION_CHECKLIST.md` | email-address | low | your… | content |
| `agileplus/.env.example` | email-address | low | your… | content |
| `docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | email-address | low | your… | content |

### audit-snapshot-AgilePlus

- Default branch: `main`
- Files scanned (tree blobs): 2979
- Content files fetched (sampled): 19
- Tree truncated: no
- Categories hit: email-address, filename:credentials-named, filename:docker-compose, filename:env-file, filename:npmrc, filename:secrets-named, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.archive/AgilePlus-recovery-20260714/PhenoLang-crates-2026-06-20/crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `.archive/kitty-specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `.env.example` | filename:env-file | medium | n/a | filename |
| `.npmrc` | filename:npmrc | medium | n/a | filename |
| `.semgrep-rules/secrets-detection.yml` | filename:secrets-named | medium | n/a | filename |
| `assets/tokens.css` | filename:token-named | medium | n/a | filename |
| `crates/agileplus-api/src/middleware/token_verifier.rs` | filename:token-named | medium | n/a | filename |
| `crates/agileplus-dashboard/desktop-electrobun/.env.example` | filename:env-file | medium | n/a | filename |
| `crates/agileplus-domain/src/config/credentials.rs` | filename:credentials-named | medium | n/a | filename |
| `crates/agileplus-triage/src/ast_tokenize.rs` | filename:token-named | medium | n/a | filename |
| `deploy/selfhost/docker-compose.selfhost.yml` | filename:docker-compose | medium | n/a | filename |
| `docker-compose.plane.yml` | filename:docker-compose | medium | n/a | filename |
| `docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `docs/pilot/tokenledger.md` | filename:token-named | medium | n/a | filename |
| `docs/specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `findings/secrets_precommit_audit_2026-05-05.md` | filename:secrets-named | medium | n/a | filename |
| `kitty-specs/001-spec-driven-development-engine/tasks/WP15-api-credentials.md` | filename:credentials-named | medium | n/a | filename |
| `scripts/wrangler-secrets-bootstrap.mjs` | filename:secrets-named | medium | n/a | filename |
| `tools/phench/.env.example` | filename:env-file | medium | n/a | filename |
| `.env.example` | email-address | low | your… | content |

### argis-extensions-preserved-20261114

- Default branch: `main`
- Files scanned (tree blobs): 1628
- Content files fetched (sampled): 14
- Tree truncated: no
- Categories hit: email-address, filename:docker-compose, filename:env-file, filename:secrets-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.env.example` | filename:env-file | medium | n/a | filename |
| `.secrets.baseline` | filename:secrets-named | medium | n/a | filename |
| `config/secrets.go` | filename:secrets-named | medium | n/a | filename |
| `config/secrets_test.go` | filename:secrets-named | medium | n/a | filename |
| `docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `findings/2026-06-18-T9-2-secret-block-resolution.md` | filename:secrets-named | medium | n/a | filename |
| `findings/2026-06-19-T21-1-secret-scan-rescan.md` | filename:secrets-named | medium | n/a | filename |
| `findings/2026-06-22-SIDE-22-secrets-scan.md` | filename:secrets-named | medium | n/a | filename |
| `findings/archived-repo-local-patches/2026-06-20/phenotype-ops/0001-feat-security-add-gitleaks-secret-scan-CI-workflow-L.patch` | filename:secrets-named | medium | n/a | filename |
| `pheno-config/src/secret_rotation.rs` | filename:secrets-named | medium | n/a | filename |
| `pheno-config/src/secrets.rs` | filename:secrets-named | medium | n/a | filename |
| `pheno-secret-scan/.github/workflows/secret-scan.yml` | filename:secrets-named | medium | n/a | filename |
| `services/promptadapter/docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `slm-server/docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `findings/2026-06-22-SIDE-22-secrets-scan.md` | email-address | low | user… | content |
| `findings/archived-repo-local-patches/2026-06-20/phenotype-ops/0001-feat-security-add-gitleaks-secret-scan-CI-workflow-L.patch` | email-address | low | koos… | content |

### audit-snapshot-argis

- Default branch: `main`
- Files scanned (tree blobs): 1613
- Content files fetched (sampled): 14
- Tree truncated: no
- Categories hit: email-address, filename:docker-compose, filename:env-file, filename:secrets-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.env.example` | filename:env-file | medium | n/a | filename |
| `.secrets.baseline` | filename:secrets-named | medium | n/a | filename |
| `config/secrets.go` | filename:secrets-named | medium | n/a | filename |
| `config/secrets_test.go` | filename:secrets-named | medium | n/a | filename |
| `docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `findings/2026-06-18-T9-2-secret-block-resolution.md` | filename:secrets-named | medium | n/a | filename |
| `findings/2026-06-19-T21-1-secret-scan-rescan.md` | filename:secrets-named | medium | n/a | filename |
| `findings/2026-06-22-SIDE-22-secrets-scan.md` | filename:secrets-named | medium | n/a | filename |
| `findings/archived-repo-local-patches/2026-06-20/phenotype-ops/0001-feat-security-add-gitleaks-secret-scan-CI-workflow-L.patch` | filename:secrets-named | medium | n/a | filename |
| `pheno-config/src/secret_rotation.rs` | filename:secrets-named | medium | n/a | filename |
| `pheno-config/src/secrets.rs` | filename:secrets-named | medium | n/a | filename |
| `pheno-secret-scan/.github/workflows/secret-scan.yml` | filename:secrets-named | medium | n/a | filename |
| `services/promptadapter/docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `slm-server/docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `findings/2026-06-22-SIDE-22-secrets-scan.md` | email-address | low | user… | content |
| `findings/archived-repo-local-patches/2026-06-20/phenotype-ops/0001-feat-security-add-gitleaks-secret-scan-CI-workflow-L.patch` | email-address | low | koos… | content |

### Personal

- Default branch: `main`
- Files scanned (tree blobs): 258
- Content files fetched (sampled): 6
- Tree truncated: no
- Categories hit: cloudflare-zone-id-like-32hex, filename:token-named, filename:wrangler.toml
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `jobs-collector/wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |
| `tools/agents-email/wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |
| `tools/kilo-bridge/wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |
| `web/src/styles/tokens.css` | filename:token-named | medium | n/a | filename |
| `worker/wrangler.toml` | cloudflare-zone-id-like-32hex | medium | 2a40… | content |
| `worker/wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |
| `wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |

### BytePort

- Default branch: `main`
- Files scanned (tree blobs): 680
- Content files fetched (sampled): 6
- Tree truncated: no
- Categories hit: filename:docker-compose, filename:env-file, filename:npmrc, filename:secrets-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.env.example` | filename:env-file | medium | n/a | filename |
| `.github/frontend/.npmrc` | filename:npmrc | medium | n/a | filename |
| `backend/byteport/models/secrets.go` | filename:secrets-named | medium | n/a | filename |
| `backend/byteport/routes/secrets.go` | filename:secrets-named | medium | n/a | filename |
| `docker-compose.yml` | filename:docker-compose | medium | n/a | filename |
| `frontend/web/.npmrc` | filename:npmrc | medium | n/a | filename |

### harness-ops

- Default branch: `main`
- Files scanned (tree blobs): 69
- Content files fetched (sampled): 4
- Tree truncated: no
- Categories hit: cloudflare-zone-id-like-32hex, filename:secrets-named, filename:wrangler.toml
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `agent-comms/docs/INFISICAL_SECRETS_PLAN.md` | filename:secrets-named | medium | n/a | filename |
| `agent-comms/workers/agentcom-discord/wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |
| `agent-comms/workers/agentcom-inbox/wrangler.toml` | cloudflare-zone-id-like-32hex | medium | 6c9e… | content |
| `agent-comms/workers/agentcom-inbox/wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |
| `agent-comms/workers/relay-forwarder/wrangler.toml` | cloudflare-zone-id-like-32hex | medium | a8c5… | content |
| `agent-comms/workers/relay-forwarder/wrangler.toml` | filename:wrangler.toml | medium | n/a | filename |

### phenotype-landing

- Default branch: `main`
- Files scanned (tree blobs): 550
- Content files fetched (sampled): 6
- Tree truncated: no
- Categories hit: filename:env-file, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `packages/auth/.env.example` | filename:env-file | medium | n/a | filename |
| `sites/agileplus-landing/src/styles/tokens.css` | filename:token-named | medium | n/a | filename |
| `sites/hwledger-landing/.env.example` | filename:env-file | medium | n/a | filename |
| `sites/phenokits-landing/.env.example` | filename:env-file | medium | n/a | filename |
| `sites/projects-landing/.env.example` | filename:env-file | medium | n/a | filename |
| `sites/thegent-landing/.env.example` | filename:env-file | medium | n/a | filename |

### chatta

- Default branch: `main`
- Files scanned (tree blobs): 4521
- Content files fetched (sampled): 4
- Tree truncated: no
- Categories hit: filename:db-file, filename:env-file, filename:npmrc
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `frontend/.npmrc` | filename:npmrc | medium | n/a | filename |
| `frontend/desktop-electrobun/.env.example` | filename:env-file | medium | n/a | filename |
| `backend/stores.db` | filename:db-file | low | n/a | filename |
| `backend/stores2.db` | filename:db-file | low | n/a | filename |

### zz-argis-extensions

- Default branch: `audit/snapshot-20260916`
- Files scanned (tree blobs): 304
- Content files fetched (sampled): 3
- Tree truncated: no
- Categories hit: email-address, filename:secrets-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `findings/2026-06-18-T9-2-secret-block-resolution.md` | filename:secrets-named | medium | n/a | filename |
| `findings/2026-06-22-SIDE-22-secrets-scan.md` | filename:secrets-named | medium | n/a | filename |
| `findings/archived-repo-local-patches/2026-06-20/phenotype-ops/0001-feat-security-add-gitleaks-secret-scan-CI-workflow-L.patch` | filename:secrets-named | medium | n/a | filename |
| `findings/2026-06-22-SIDE-22-secrets-scan.md` | email-address | low | user… | content |

### zz-HexaKit

- Default branch: `audit/snapshot-20260916`
- Files scanned (tree blobs): 358
- Content files fetched (sampled): 2
- Tree truncated: no
- Categories hit: email-address, filename:secrets-named, filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | filename:secrets-named | medium | n/a | filename |
| `docs/guides/SNYK_TOKEN_ACQUISITION_GUIDE.md` | filename:token-named | medium | n/a | filename |
| `docs/guides/GITHUB_SECRETS_SETUP_GUIDE.md` | email-address | low | your… | content |

### HarnessDesk

- Default branch: `main`
- Files scanned (tree blobs): 249
- Content files fetched (sampled): 1
- Tree truncated: no
- Categories hit: filename:env-file
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `web/.env.example` | filename:env-file | medium | n/a | filename |

### PhenoVCS

- Default branch: `main`
- Files scanned (tree blobs): 133
- Content files fetched (sampled): 1
- Tree truncated: no
- Categories hit: filename:env-file
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.env.example` | filename:env-file | medium | n/a | filename |

### audit-snapshot-PhenoVCS

- Default branch: `main`
- Files scanned (tree blobs): 133
- Content files fetched (sampled): 1
- Tree truncated: no
- Categories hit: filename:env-file
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `.env.example` | filename:env-file | medium | n/a | filename |

### phenoDesign-visual-production-v2

- Default branch: `main`
- Files scanned (tree blobs): 179
- Content files fetched (sampled): 1
- Tree truncated: no
- Categories hit: filename:token-named
- Highest severity: **medium**
- Verdict: **scrub first**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| `reference/frontend-3d-agent-kit/contracts/design-tokens.json` | filename:token-named | medium | n/a | filename |

### StealthStartup

- Default branch: `main`
- Files scanned (tree blobs): 34
- Content files fetched (sampled): 0
- Tree truncated: no
- Categories hit: none
- Highest severity: **none**
- Verdict: **safe to publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| _(none)_ | none | none | n/a | n/a |

### audit-snapshot-hwLedger

- Default branch: `main`
- Files scanned (tree blobs): 326
- Content files fetched (sampled): 0
- Tree truncated: no
- Categories hit: none
- Highest severity: **none**
- Verdict: **safe to publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| _(none)_ | none | none | n/a | n/a |

### audit-system

- Default branch: `main`
- Files scanned (tree blobs): 454
- Content files fetched (sampled): 0
- Tree truncated: no
- Categories hit: none
- Highest severity: **none**
- Verdict: **safe to publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| _(none)_ | none | none | n/a | n/a |

### cvp-fixture

- Default branch: `main`
- Files scanned (tree blobs): 17
- Content files fetched (sampled): 0
- Tree truncated: no
- Categories hit: none
- Highest severity: **none**
- Verdict: **safe to publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| _(none)_ | none | none | n/a | n/a |

### dagrun

- Default branch: `main`
- Files scanned (tree blobs): 192
- Content files fetched (sampled): 0
- Tree truncated: no
- Categories hit: none
- Highest severity: **none**
- Verdict: **safe to publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| _(none)_ | none | none | n/a | n/a |

### phenoreg-browser-audit

- Default branch: `main`
- Files scanned (tree blobs): 367
- Content files fetched (sampled): 0
- Tree truncated: no
- Categories hit: none
- Highest severity: **none**
- Verdict: **safe to publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| _(none)_ | none | none | n/a | n/a |

### zz-aa-dep-AirLock

- Default branch: `main`
- Files scanned (tree blobs): 775
- Content files fetched (sampled): 0
- Tree truncated: no
- Categories hit: none
- Highest severity: **none**
- Verdict: **safe to publish**

| Path | Category | Severity | Redacted indicator | Source |
|---|---|---|---|---|
| _(none)_ | none | none | n/a | n/a |

## Method and limits

- **Method:** For each repository, listed default-branch files via `gh api repos/KooshaPari/<repo>/git/trees/<branch>?recursive=1` and applied filename-first flagging (cheap, no content needed) for: `.env*`, `*.pem`, `*.key`, `id_rsa*`, `*.p12`, `secrets*`, `credentials*`, `*token*`, `*.tfstate`, `wrangler.toml`, `*.sqlite`, `*.db`, `docker-compose*.yml`, `.npmrc`, `.netrc`, `kubeconfig`, and files under `.ssh/` or `.aws/`. Then fetched content only for the highest-signal filename-flagged candidates (max 40 files per repo) and scanned for: OpenAI/Anthropic/HuggingFace/Google/Stripe key shapes, AWS AKIA/ASIA, GitHub ghp_/gho_/ghs_/ghu_/ghr_/github_pat_, Slack xox*, PEM private keys, Tailscale tskey/ts0, 100.64.0.0/10 CGNAT addresses, `*.ts.net` hostnames, 32-hex Cloudflare-zone-id-like strings, bcrypt hashes (`$2a$/$2b$/$2y$`), and email addresses.
- **Sampling limit:** Content inspection was limited to at most 40 filename-prioritized files per repository. Files not flagged by filename heuristics were not content-scanned.
- **Not a full content scan:** A clean result is **not** a guarantee of no disclosure risk. Secrets or sensitive identifiers may exist in unflagged filenames, in files beyond the 40-file sample, in binary/large files (content fetch capped/truncated), in commit history (not scanned), in issues/PRs/wiki/releases (not scanned), or in forms not matched by the regexes used.
- **Tree truncation:** If the Git Trees API reported truncation, file coverage for that repo is incomplete (noted per-repo).
- **Heuristic noise:** Some patterns (especially 32-hex strings and emails) can produce false positives; findings are risk indicators requiring human review, reported with redacted indicators only (no secret values recorded).
- **Verdict mapping:** `high` => do not publish; `medium` or `low` => scrub first; `none` observed in scanned scope => safe to publish (subject to limits above).

