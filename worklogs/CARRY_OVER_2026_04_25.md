# Carry-Over — 2026-04-25 (evening refresh)

Cross-repo open items at end of session. Replaces earlier-day snapshot.

## User actions required (cannot be agent-completed)

- **helios-cli alerts** — disable at repo level via admin toggle (Dependabot +
  CodeQL + secret-scanning). Repo is archive-pending.
- **Vercel deploy hook** — needs creation for `projects-landing` so the nightly
  cron can actually trigger redeploys (cron is wired but hook URL is null).

## User decisions pending

Four candidates flagged for splitting out as standalone repos:

1. `phenotype-shared` — currently inside `phenotype-infra`
2. `bifrost-extensions`
3. `HexaKit`
4. `Tracera`

Decision needed on which to split and the rollout order. Default proposal:
extract Tracera first (cleanest boundary), then HexaKit.

## Deferred technical work

- **PhenoRuntime** — 3 MED `rustls-webpki` advisories deferred. Real fix needs
  `aws-smithy-http-client` default-feature change; non-trivial cascade.
- **BytePort gtk3-rs migration** — Linux-only big rewrite; tracked, not
  scheduled.
- **Dependabot Rust scans materializing** — for the 8 just-committed-lockfile
  repos: BytePort, hwLedger, PhenoKits, phenoShared, AuthKit,
  PhenoObservability, phenotype-infra, PhenoRuntime. Re-audit in 24h.

## Scheduled

- **Cloud routine** `trig_01DAEAKGCw6KtYLRYBxVMzGN` fires
  **2026-04-26T18:00Z** for branch cleanup R5.

## Active investigation

- **thegent platform-sync** — 4 test conflicts still flagged. `test_openrouter_p2`
  was fixed via #966; remaining 3 unresolved.

## Local-only commits (not pushed)

- `repos/Cargo.toml` workspace fix — parent `repos/` git remote is
  misconfigured (points at PhenoKits). Push deferred until remote is corrected.

## Status snapshot

- ~40 HIGH+MED CVEs closed real this session
- 5 of 5 Tier-1 project landings 200ing
- `projects.<REDACTED>.com` LIVE
- Tier-3 path microfrontends pattern proven on agileplus-landing
- MEMORY.md compaction: 490 → 33 lines + 12 topic files

## Update — Evening Close (2026-04-25)

### Cloud routines now scheduled (3)
- `trig_01WyavEsSwm8ouHmtNTD7E7k` — Sunday observability triad
- `trig_01DAEAKGCw6KtYLRYBxVMzGN` — Sunday branch cleanup
- `trig_01W7Zjoker6d88VMupekB3Kh` — Monday Dependabot harvest

### Resolved during session
- 7 manifest blockers cleared
- 7 lockfile commits landed
- 30+ HIGH CVEs closed

### Remaining blockers (user-required only)
- Vercel deploy hook
- OCI lottery hit
- helios-cli alerts admin toggle

### Residual H/C
- 6 H/C remaining on agentapi-plusplus (transitive; auto-closes on rescan)
