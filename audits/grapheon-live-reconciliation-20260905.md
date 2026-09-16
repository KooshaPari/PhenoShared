# Grapheon -> Tracera live reconciliation

**Captured:** 2026-09-05T05:28Z (custody and successor refresh)
**Scope:** archived Grapheon source, Tracera current main, and registry boundary records.
**Disposition:** NO-GO for absorption/retirement completion.

## Verified source custody

- `KooshaPari/zz-archive-grapheon` is private and archived; `main` is
  `8b57aa380dd6d288f451be5ef0e4e766f606c7fb`.
- Local Grapheon `git fsck --full --no-reflogs` passes. The preservation bundle
  `/tmp/grapheon-preservation-all-20260904-0757.bundle` is 431,515,603 bytes with
  SHA-256 `828023ca7f034b796a9e4867ae008fa0c1f5443162c78e256746402a082185f0`.
- `git bundle verify` lists 47 refs. An isolated local restore has exact sorted
  ref/object parity and `git fsck --full --no-dangling` exits 0.
- On 2026-09-05, the existing bundle hash and bundle verification passed
  again; the existing restore passed `git fsck --full --no-dangling`.
  Sorted named refs match exactly (46 refs; the bundle's 47th advertised
  entry is `HEAD`), and restored `HEAD` matches the source commit. The
  Grapheon checkout has zero porcelain status entries and one worktree.
- This remains GitHub/local evidence, not immutable dual-cloud proof.
  Live `wrangler r2 bucket list` succeeds and finds `phenotype-preservation`;
  the earlier blanket credentials-absent description is superseded.
  `wrangler r2 bucket lock list phenotype-preservation` reports **no lock
  rules**. Installed Wrangler 4.120.1 enforces a 314,572,800-byte object-put
  limit, below the 431,515,603-byte bundle. `aws`, `rclone`, `b2`, and
  `restic` are absent from PATH; no AWS/R2/Cloudflare credential environment
  variables were present (values were never printed). This does not exclude
  credentials in another owner-managed store. No upload was attempted.
- Next custody action requires the cloud owner to designate immutable
  retention and a supported multipart upload route, with any storage spending
  authorized. Then upload the hash-addressed bundle, independently download
  it, verify SHA-256, restore, compare all named refs and HEAD, and run fsck.
  GitHub archival alone does not establish first-cloud immutability or full
  dirty/untracked/artifact coverage; those program gates remain open.

## Destination state

- Tracera has no open pull requests. Current remote `main` is
  `b23469678da42d0d0ec8c303a7a97e5b1b19d293` and hosted Rust/build/coverage
  checks fail; dependency policy reports yanked `chacha20 0.10.1` and `spin 0.9.8`.
- Vercel and Cloudflare Worker deployments succeeded for that commit, but the
  full-stack/Render build failed. These successes do not prove backend
  readiness or end-to-end consumption.
- `pheno-harness` still documents Grapheon as source-of-truth, defaults to
  `127.0.0.1:8080`, and has an unfinished Tracera adapter. No authenticated
  append/query/health dogfood, telemetry delivery, or AgilePlus compliance run
  is evidenced.
- A focused local compatibility patch is present in the existing dirty
  `pheno-harness` owner checkout (`pheno/runtime_config.py`,
  `pheno/trace_store/config.py`, and `pheno/trace_store/tracera.py`): canonical
  `GRAPHEON_*` variables now take precedence while `TRACERA_*` aliases remain
  supported. The black-box tests `tests/test_runtime_config.py`,
  `tests/trace_store/test_config.py`, and `tests/trace_store/test_tracera.py`
  pass 45/45 via `python3 -m pytest -q -c /dev/null ...`. It is uncommitted
  and not production/dogfood proof.
- A protected Tracera successor branch based on current remote `main` now has
  commits `ec47038ad181d2772e83e14419a96955f642612c` and
  `79436a75e25d7d4db9be95a8873f7a596a114070`: Rust docs/dependencies were
  repaired, the yanked `chacha20`/`spin` entries were updated, the four
  WorkOS compile blockers were resolved, and the contradictory raw-`&` URL
  test now asserts the intended rejection. `cargo check -p tracera-workos
  --locked`, `cargo test -p tracera-workos --locked` (47/47), and
  `cargo deny check advisories` pass. Workspace-wide formatting still reports
  unrelated pre-existing drift. The commits are unpushed and not hosted-CI
  proof.
- Successor owner refreshed the same remote-main SHA and clean successor
  worktree on 2026-09-05; `cargo test -p tracera-workos --locked` again
  passed 47 tests. Repository Actions remains enabled and push/PR workflows
  select `ubuntu-latest`; publication remains gated on zero-billable-runner
  enforcement. The prior full successor SHA was corrected above.
- Before any push, those two successor commits were preserved in
  `/tmp/tracera-workos-successor-20260905-0416.bundle`; `git bundle verify`
  passes and SHA-256 is
  `9a27c9eceeeef81c8f74da61fa3682e5520d0754a03e12221efca1b3c3da70d0`.
- AgilePlus MCP `health_check` is healthy (`grpc_core=ok`), but the direct
  `get_feature("grapheon-tracera-absorption")` call returns gRPC `NOT_FOUND`.
  No lifecycle feature, work-package chain, or audit record exists for this
  program; the owner-scoped spec is now committed in AgilePlus as
  `bc36bec6` (`kitty-specs/grapheon-tracera-absorption/spec.md`) and the live
  `agileplus_specify` call accepted it as queued. A subsequent `get_feature`
  still returns `NOT_FOUND`, so lifecycle creation remains pending engine
  processing/owner action.
- A source-controlled workflow scan of archived Grapheon found 17 workflow
  files, 25 `ubuntu-latest` jobs, 10 Blacksmith jobs, and 2 matrix-OS jobs.
  Three workflows are scheduled (`nightly` cron `17 6 * * *`, `trunk-check`
  cron `0 3 * * 1`, and `scorecard` cron `25 4 * * 1`); 11 expose
  `workflow_dispatch`. This is an exposure inventory, not proof of billing or
  zero-cost execution. Owner-controlled suspension or an approved free/self-
  hosted runner attestation is still required.

## Gate decision

The GitHub archive rename preceded the required dual-cloud restore gate. Do not
rename, delete, reset, clean, prune, or force-push any source-bearing state.
Completion requires: current-main Tracera fixes and accepted successor slices;
consumer repoint plus authenticated dogfood/observability/compliance proof;
zero-billable-runner evidence; and immutable second-cloud upload with an
independent restore, ref parity, and git-fsck report. Sponsor re-acknowledgement
must follow those proofs.
